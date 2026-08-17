"""Monitor panel rendering — sparklines + 4x4 grid."""

import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.estilo import (
    COLORS,
    FONT_SIZES,
    MONITOR_FIGSIZE,
    MONITOR_GRID,
    SPARKLINE_FILL_ALPHA,
    SPARKLINE_LINE_WIDTH,
    SPARKLINE_YLIM,
)
from comentario_matinal.render.calendars import is_market_holiday
from comentario_matinal.render.output import save_figure
from comentario_matinal.render.tickers import TickerInfo

logger = logging.getLogger("comentario_matinal")


# ---------------------------------------------------------------------------
# Asset formatters — return (is_positive, value_str, change_str)
# ---------------------------------------------------------------------------


def _format_rate(px_last: float, chg_net: float, chg_pct: float):
    return chg_net >= 0, f"{px_last:.3f}%", f"({chg_net * 100:+.1f} bps)"


def _format_vol(px_last: float, chg_net: float, chg_pct: float):
    return chg_net <= 0, f"{px_last:.2f}", f"({chg_net:+.2f} pts)"


def _format_commodity(px_last: float, chg_net: float, chg_pct: float):
    return chg_pct >= 0, f"${px_last:.2f}", f"({chg_pct:+.2f} %)"


def _format_default(px_last: float, chg_net: float, chg_pct: float):
    if px_last >= 1000:
        value_str = f"{px_last:,.0f}"
    else:
        value_str = f"{px_last:.3f}" if px_last < 100 else f"{px_last:.2f}"
    return chg_pct >= 0, value_str, f"({chg_pct:+.2f} %)"


FORMATTERS = {
    "rate": _format_rate,
    "vol": _format_vol,
    "commodity": _format_commodity,
    "equity": _format_default,
    "fx": _format_default,
}


# ---------------------------------------------------------------------------
# Sparkline helpers
# ---------------------------------------------------------------------------


def normalize_price_series(price_series: pd.Series) -> tuple[np.ndarray, float]:
    """Normalize intraday prices to 0-1 scale using min/max.

    Returns (normalized_values, midpoint) where midpoint is the
    normalized position of the opening price.
    """
    min_price = price_series.min()
    max_price = price_series.max()

    if max_price == min_price:
        return np.full(len(price_series), 0.5), 0.5

    normalized = (price_series.values - min_price) / (max_price - min_price)
    midpoint = (price_series.values[0] - min_price) / (max_price - min_price)
    return normalized, midpoint


def plot_sparkline_with_areas(
    ax: plt.Axes,
    price_series: pd.Series,
    positive_color: str = COLORS["positive"],
    negative_color: str = COLORS["negative"],
    line_width: float = SPARKLINE_LINE_WIDTH,
    fill_alpha: float = SPARKLINE_FILL_ALPHA,
) -> None:
    """Plot sparkline with green/red areas based on midpoint."""
    if price_series.empty or len(price_series) < 2:
        return

    normalized, midpoint = normalize_price_series(price_series)
    x = np.arange(len(normalized))

    # Positive area (above midpoint) — green
    ax.fill_between(
        x, normalized, midpoint,
        where=(normalized >= midpoint),
        facecolor=positive_color, alpha=fill_alpha, interpolate=True,
    )

    # Negative area (below midpoint) — red
    ax.fill_between(
        x, normalized, midpoint,
        where=(normalized < midpoint),
        facecolor=negative_color, alpha=fill_alpha, interpolate=True,
    )

    # Segmented line — color follows fill
    for i in range(len(x) - 1):
        color = positive_color if normalized[i] >= midpoint else negative_color
        ax.plot(x[i : i + 2], normalized[i : i + 2], color=color, linewidth=line_width)

    ax.set_ylim(*SPARKLINE_YLIM)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------


def build_monitor_panel(
    tickers_info: list[TickerInfo],
    ref_data: pd.DataFrame,
    price_data: dict[str, pd.Series],
    save_path: Path | None = None,
    figsize: tuple = MONITOR_FIGSIZE,
    grid: tuple[int, int] = MONITOR_GRID,
    allowed_root: Path | None = None,
    asof: datetime | None = None,
    column_headers: list[str] | None = None,
    market_closed_path: Path | None = None,
) -> tuple[Figure, dict[str, dict]]:
    """Build the monitor panel and report, per ticker, what each tile shows.

    Returns ``(figure, metrics)``. The metrics dict is keyed by ticker and holds
    exactly the numbers the tile rendered — including the change recomputed from
    the intraday series, which is NOT ``ref_data``'s ``chg_net_1d`` whenever bars
    came back. A caller that also narrates these moves in prose must read them
    from here; deriving them again from the reference fields would let the image
    and the text disagree about direction on the same morning.

    ``grid`` is (rows, cols) and must hold every ticker. Tiles beyond the ticker
    list are simply not drawn, so a grid larger than the list leaves blanks.

    ``column_headers`` labels each grid column — one string per column — for
    panels whose columns mean something (a category per column). Room is
    reserved at the top only when headers are given, so panels without them keep
    their current spacing exactly.

    Writes a PNG only when ``save_path`` is given, and only inside
    ``allowed_root``, which is required.
    """
    nrows, ncols = grid
    if len(tickers_info) > nrows * ncols:
        raise ValueError(
            f"Grid {nrows}x{ncols} comporta {nrows * ncols} tiles, "
            f"mas foram passados {len(tickers_info)} tickers."
        )
    if column_headers and len(column_headers) != ncols:
        raise ValueError(
            f"column_headers tem {len(column_headers)} entradas, "
            f"mas a grade tem {ncols} colunas."
        )

    metrics: dict[str, dict] = {}
    color_title = COLORS["title"]
    color_green = COLORS["positive"]
    color_red = COLORS["negative"]

    fig = plt.figure(figsize=figsize, facecolor="white")

    # O selo vem por parâmetro, não de uma raiz de projeto: esta camada
    # desenha, não sabe onde o repositório começa.
    market_closed_img = None
    if market_closed_path is not None and market_closed_path.exists():
        market_closed_img = plt.imread(str(market_closed_path))

    for idx, item in enumerate(tickers_info):
        ticker = item.ticker
        display_name = item.display
        asset_type = item.type

        ax = fig.add_subplot(nrows, ncols, idx + 1)

        # Reference data
        px_last = 0.0
        chg_net, chg_pct = 0.0, 0.0
        has_display_override = False
        if ticker in ref_data.index:
            row_data = ref_data.loc[ticker]
            px_last = row_data.get("px_last", 0)
            chg_net = row_data.get("chg_net_1d", 0)
            chg_pct = row_data.get("chg_pct_1d", 0)

            # Yield tickers store display overrides separately
            if "px_last_display" in row_data.index and pd.notna(row_data["px_last_display"]):
                px_last = row_data["px_last_display"]
                chg_net = row_data.get("chg_net_display", chg_net)
                has_display_override = True

        # Price series
        price_series = price_data.get(ticker, pd.Series())

        # The exchange calendar is authoritative: if the market is officially
        # closed for a holiday, force the "market closed" tile even when a few
        # stray bars come back (e.g. USGG10YR keeps ticking from overnight
        # London/Asia trading on a SIFMA holiday). Only draw the sparkline on
        # non-holiday days.
        holiday = is_market_holiday(ticker)
        has_chart = (
            not holiday
            and not price_series.empty
            and len(price_series) >= 2
        )

        # On a chart day, derive the change from the intraday series (unless
        # ref_data already provides a more accurate yield-based override).
        # On a holiday, keep ref_data's official 1-day change.
        if has_chart and not has_display_override:
            first_price = price_series.iloc[0]
            last_price = price_series.iloc[-1]
            chg_net = last_price - first_price
            chg_pct = (
                ((last_price - first_price) / first_price) * 100
                if first_price != 0
                else 0
            )

        # Format values via dispatch table
        formatter = FORMATTERS.get(asset_type, _format_default)
        is_positive, value_str, change_str = formatter(px_last, chg_net, chg_pct)
        text_color = color_green if is_positive else color_red

        # Record what this tile actually shows, so prose about the same move can
        # be generated from the rendered numbers rather than re-derived.
        metrics[ticker] = {
            "display": display_name,
            "type": asset_type,
            "px_last": px_last,
            "chg_net": chg_net,
            "chg_pct": chg_pct,
            "value_str": value_str,
            "change_str": change_str,
            "is_positive": is_positive,
            "has_chart": has_chart,
            "holiday": holiday,
        }

        # Sparkline on chart days; otherwise the "market closed" image — both
        # for a genuine data gap and for a holiday (where it wins over any
        # stray bars, since `has_chart` is False on holidays).
        if has_chart:
            plot_sparkline_with_areas(
                ax=ax,
                price_series=price_series,
                positive_color=color_green,
                negative_color=color_red,
                line_width=SPARKLINE_LINE_WIDTH,
                fill_alpha=SPARKLINE_FILL_ALPHA,
            )
        elif market_closed_img is not None:
            # O carimbo vai num eixo interno, e não no do tile. `imshow` com
            # aspect="equal" encolhe a caixa do eixo que recebe a imagem, para
            # preservar o formato do PNG — e as três linhas de texto abaixo são
            # posicionadas em coordenadas DESSE eixo (transAxes). Desenhando no
            # próprio tile, o eixo encolhia e arrastava a variação para o meio do
            # carimbo em vez do meio da coluna: na mesma grade, o tile fechado
            # saía com o texto desalinhado do tile aberto ao lado.
            #
            # Com o eixo interno o tile mantém a largura inteira, o texto fica
            # ancorado na coluna, e quem encolhe é o interno — que o matplotlib
            # centraliza por padrão, que é onde o carimbo deve ficar.
            selo = ax.inset_axes([0.0, 0.0, 1.0, 1.0])
            selo.imshow(market_closed_img, aspect="equal")
            # Ancoragem explícita: ao encolher para o formato do PNG, o eixo
            # interno precisa sobrar dos dois lados, e não só à direita.
            selo.set_anchor("C")
            selo.axis("off")

        ax.axis("off")

        # Asset name (top)
        ax.text(
            0, 1.15, display_name, transform=ax.transAxes,
            fontsize=FONT_SIZES["monitor_name"], fontweight="bold",
            color=color_title, va="bottom", ha="left",
        )

        # Value and change
        ax.text(
            0, 1.0, value_str, transform=ax.transAxes,
            fontsize=FONT_SIZES["monitor_value"], color=text_color,
            va="bottom", ha="left",
        )
        ax.text(
            0.5, 1.0, change_str, transform=ax.transAxes,
            fontsize=FONT_SIZES["monitor_change"], color=text_color,
            va="bottom", ha="left",
        )

    # Footer
    fig.text(
        0.02, 0.02, "OBS: Gráficos intraday.",
        fontsize=FONT_SIZES["monitor_obs"], color="black",
        ha="left", va="bottom",
    )
    # The stamp must be the reference moment the caller is working to, not the
    # wall clock: a caller that also writes prose headed "Referência: 07:35"
    # would otherwise ship an image stamped with whatever time it rendered.
    timestamp = (asof or datetime.now()).strftime("Atualizado em %d/%m/%y - %H:%M")
    fig.text(
        0.98, 0.02, timestamp,
        fontsize=FONT_SIZES["monitor_obs"], color=color_red,
        ha="right", va="bottom",
    )

    # Headers need vertical room above the first row's asset names, which
    # already sit above their axes. Reserve it only when there are headers, so
    # panels without them keep their existing spacing untouched.
    topo = 0.93 if column_headers else 0.97
    plt.tight_layout(rect=[0, 0.03, 1, topo])
    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    if column_headers:
        # Center each header over its column, taken from the laid-out position of
        # the first-row axes. Reading the geometry back beats hardcoding offsets,
        # which would drift with figure size and column count.
        for coluna, titulo in enumerate(column_headers):
            if coluna >= len(fig.axes):
                break
            caixa = fig.axes[coluna].get_position()
            fig.text(
                (caixa.x0 + caixa.x1) / 2, 0.965, titulo,
                fontsize=FONT_SIZES["monitor_column_header"], fontweight="bold",
                color=color_title, ha="center", va="center",
            )

    if save_path is not None:
        save_figure(fig, save_path, allowed_root=allowed_root)

    return fig, metrics


def create_monitor_panel(
    tickers_info: list[TickerInfo],
    ref_data: pd.DataFrame,
    price_data: dict[str, pd.Series],
    save_path: Path | None = None,
    figsize: tuple = MONITOR_FIGSIZE,
) -> Figure:
    """Create the monitor panel with sparklines, returning just the Figure.

    Thin wrapper over ``build_monitor_panel`` for callers that only render.
    """
    fig, _ = build_monitor_panel(
        tickers_info, ref_data, price_data, save_path=save_path, figsize=figsize,
    )
    return fig
