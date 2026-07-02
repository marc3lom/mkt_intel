"""
Word document export utilities for FOMC analysis.

This module provides functions for generating Word-optimized charts
and tables matching the styling of the reference Word documents.
"""

import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

# Fuso de exibição do grid intraday (horário de Brasília)
_TZ_BRT = ZoneInfo("America/Sao_Paulo")

# === Word Export Constants ===
WORD_PAGE_WIDTH_INCHES: float = 7.0
WORD_DPI: int = 150
WORD_FIGSIZE: tuple[float, float] = (7.0, 4.0)
WORD_FIGSIZE_TALL: tuple[float, float] = (7.0, 6.0)
WORD_FIGSIZE_DASHBOARD: tuple[float, float] = (7.0, 5.0)
WORD_FIGSIZE_DOT_PLOT: tuple[float, float] = (7.0, 4.5)

# === Word Table Styling Colors (matching reference docs) ===
HEADER_COLOR: str = "#2E4C59"  # Dark teal
HEADER_TEXT_COLOR: str = "#FFFFFF"  # White
ALT_ROW_COLOR: str = "#F5F0E8"  # Light tan/cream
ROW_COLOR: str = "#FFFFFF"  # White

# === COPOM Color Palette ===
COPOM_COLORS = [
    "#2E4C59",  # Dark teal (primary)
    "#F2B557",  # Yellow/gold (secondary)
    "#8B9F75",  # Olive green
    "#D4A88C",  # Tan
    "#C45C5C",  # Red
    "#5C7C8C",  # Blue-gray
    "#A67B5B",  # Brown
    "#6B8E6B",  # Forest green
    "#9B7BB0",  # Purple
    "#E8A87C",  # Peach
]

# === Font Sizes ===
WORD_TITLE_SIZE: int = 14
WORD_LABEL_SIZE: int = 11
WORD_TICK_SIZE: int = 10
WORD_LEGEND_SIZE: int = 10


def _get_project_root() -> Path:
    """Get the path to the project root (py-bcb)."""
    # Navigate from src/reports/fomc/core/ to project root
    return Path(__file__).parent.parent.parent.parent.parent


def get_word_export_path(filename: str) -> Path:
    """Get the output path for Word-optimized exports.

    Args:
        filename: Name of the output file.

    Returns:
        Full path in the output directory (output/reports/fomc/).
    """
    # Seguir convenção CLAUDE.md: outputs em output/ na raiz do projeto
    output_dir = _get_project_root() / "output" / "reports" / "fomc"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


def save_chart_for_word(
    fig: plt.Figure,
    output_path: Path | str,
    dpi: int = WORD_DPI,
) -> None:
    """Save a matplotlib figure with Word-optimized settings.

    Args:
        fig: Matplotlib figure to save.
        output_path: Path to save the file.
        dpi: Resolution in dots per inch. Default 150.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    logger.info(f"Saved chart to {output_path}")


def create_dot_plot_chart(
    dot_data: pd.DataFrame,
    output_path: Path | str | None = None,
    title: str = "Projecoes da Fed Funds (dots)",
) -> plt.Figure:
    """Create a dot plot chart for Fed Funds rate projections.

    Args:
        dot_data: DataFrame with columns: year, rate, count
        output_path: Optional path to save the chart.
        title: Chart title.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=WORD_FIGSIZE_DOT_PLOT, dpi=WORD_DPI)

    if dot_data.empty:
        ax.text(
            0.5,
            0.5,
            "Dados nao disponiveis",
            ha="center",
            va="center",
            fontsize=WORD_LABEL_SIZE,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    else:
        years = dot_data["year"].unique()
        year_positions = {year: i for i, year in enumerate(years)}

        # Plot dots
        for _, row in dot_data.iterrows():
            x = year_positions[row["year"]]
            y = row["rate"]

            ax.scatter(
                x,
                y,
                s=100,
                c=COPOM_COLORS[0],
                edgecolors="white",
                linewidth=1,
                zorder=3,
            )

        # Format axes
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels(years, fontsize=WORD_TICK_SIZE)

        ax.set_ylabel("Taxa (%)", fontsize=WORD_LABEL_SIZE)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.2f}"))
        ax.tick_params(axis="y", labelsize=WORD_TICK_SIZE)

        # Grid
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        # Add horizontal line at 2% (inflation target)
        ax.axhline(
            y=2.0,
            color=COPOM_COLORS[4],
            linestyle="--",
            linewidth=1,
            alpha=0.7,
            label="Meta Inflacao (2%)",
        )

    ax.set_title(title, fontsize=WORD_TITLE_SIZE, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_path:
        save_chart_for_word(fig, output_path)

    return fig


def create_sep_charts(
    medians_df: pd.DataFrame,
    prior_df: pd.DataFrame | None = None,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Create 4-panel dashboard with SEP projections.

    Creates charts for: GDP, Unemployment, PCE Inflation, Core PCE Inflation

    Args:
        medians_df: DataFrame with current projection medians.
        prior_df: DataFrame with prior meeting's medians (optional).
        output_path: Optional path to save the chart.

    Returns:
        Matplotlib Figure object.
    """
    fig, axes = plt.subplots(2, 2, figsize=WORD_FIGSIZE_DASHBOARD, dpi=WORD_DPI)

    indicators = [
        ("Change in real GDP", "PIB Real (%)", axes[0, 0]),
        ("Unemployment rate", "Taxa de Desemprego (%)", axes[0, 1]),
        ("PCE inflation", "Inflacao PCE (%)", axes[1, 0]),
        ("Core PCE inflation", "Core PCE (%)", axes[1, 1]),
    ]

    years = ["2025", "2026", "2027", "2028"]
    x_positions = range(len(years))

    for var_name, title, ax in indicators:
        # Get current values
        current_row = medians_df[medians_df["Variable"].str.contains(var_name, case=False)]

        if not current_row.empty:
            current_values = [
                current_row[year].values[0] for year in years if year in current_row.columns
            ]

            # Plot current
            ax.plot(
                x_positions[: len(current_values)],
                current_values,
                marker="o",
                markersize=8,
                color=COPOM_COLORS[0],
                linewidth=2,
                label="Atual",
            )

            # Plot prior if available
            if prior_df is not None and not prior_df.empty:
                prior_row = prior_df[prior_df["Variable"].str.contains(var_name, case=False)]
                if not prior_row.empty:
                    prior_values = [
                        prior_row[year].values[0] for year in years if year in prior_row.columns
                    ]
                    ax.plot(
                        x_positions[: len(prior_values)],
                        prior_values,
                        marker="s",
                        markersize=6,
                        color=COPOM_COLORS[5],
                        linewidth=1.5,
                        linestyle="--",
                        label="Anterior",
                    )

        # Format axes
        ax.set_title(title, fontsize=WORD_LABEL_SIZE, fontweight="bold")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(years, fontsize=WORD_TICK_SIZE)
        ax.tick_params(axis="y", labelsize=WORD_TICK_SIZE - 1)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if prior_df is not None:
            ax.legend(fontsize=WORD_TICK_SIZE - 2, loc="best")

    plt.tight_layout()

    if output_path:
        save_chart_for_word(fig, output_path)

    return fig


def create_market_reaction_charts(
    market_data: pd.DataFrame,
    statement_time: str = "14:00",
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Create 4-panel dashboard with market reaction charts.

    Creates intraday charts for: UST 2Y, UST 10Y, SPX, DXY

    Args:
        market_data: DataFrame with intraday market data.
        statement_time: Time of statement release (HH:MM).
        output_path: Optional path to save the chart.

    Returns:
        Matplotlib Figure object.
    """
    fig, axes = plt.subplots(2, 2, figsize=WORD_FIGSIZE_DASHBOARD, dpi=WORD_DPI)

    assets = [
        ("UST_2Y", "UST 2 Anos (%)", axes[0, 0], COPOM_COLORS[0]),
        ("UST_10Y", "UST 10 Anos (%)", axes[0, 1], COPOM_COLORS[2]),
        ("SPX", "S&P 500", axes[1, 0], COPOM_COLORS[1]),
        ("DXY", "Dolar Index", axes[1, 1], COPOM_COLORS[3]),
    ]

    for asset_key, title, ax, color in assets:
        if asset_key in market_data.columns:
            data = market_data[asset_key].dropna()

            if not data.empty:
                ax.plot(
                    data.index,
                    data.values,
                    color=color,
                    linewidth=1.5,
                )

                # Add vertical line at statement time
                if isinstance(data.index, pd.DatetimeIndex):
                    ax.axvline(
                        x=pd.Timestamp(data.index[0].date()) + pd.Timedelta(statement_time),
                        color=COPOM_COLORS[4],
                        linestyle="--",
                        linewidth=1,
                        alpha=0.7,
                    )

                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

        ax.set_title(title, fontsize=WORD_LABEL_SIZE, fontweight="bold")
        ax.tick_params(axis="both", labelsize=WORD_TICK_SIZE - 1)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_path:
        save_chart_for_word(fig, output_path)

    return fig


# === Grid de reação de mercado (3x3, estilo COPOM) ===

# Ordem dos 9 painéis (chave em market_data, título pt-BR, fmt do valor, cor COPOM).
# Evita o índice 4 (vermelho), reservado às linhas de evento.
MARKET_REACTION_PANELS: list[tuple[str, str, str, int]] = [
    ("NASDAQ", "Nasdaq 100", "{:,.0f}", 0),
    ("SPX", "S&P 500", "{:,.0f}", 5),
    ("RUSSELL", "Russell 2000", "{:,.0f}", 7),
    ("UST_2Y", "UST 2 Anos (%)", "{:.3f}", 0),
    ("UST_10Y", "UST 10 Anos (%)", "{:.3f}", 2),
    ("SPREAD_2S10S", "Inclinação 2s10s (bps)", "{:.1f}", 8),
    ("OIS_1Y1Y", "OIS Fwd 1Y1Y (%)", "{:.3f}", 6),
    ("DXY", "Dollar Index", "{:.2f}", 3),
    ("VIX", "VIX", "{:.2f}", 9),
]

# Eventos do FOMC a marcar com linha vertical: chave, rótulo, estilo de linha.
# Só a decisão é desenhada; para reativar as linhas da coletiva, basta re-adicionar
# ("presser_ini", "Início coletiva", "--") e ("presser_fim", "Fim coletiva", ":").
MARKET_REACTION_EVENTS: list[tuple[str, str, str]] = [
    ("decisao", "Decisão FOMC", "-"),
]


def _to_naive_brt(ts: pd.Timestamp) -> pd.Timestamp:
    """Normaliza um Timestamp para horário de Brasília *naive* (p/ plot sem
    ambiguidade de fuso do matplotlib). tz-aware → converte e remove tz."""
    ts = pd.Timestamp(ts)
    if ts.tz is not None:
        ts = ts.tz_convert(_TZ_BRT).tz_localize(None)
    return ts


def create_market_reaction_grid(
    market_data: pd.DataFrame,
    event_times: dict[str, pd.Timestamp] | None = None,
    meeting_date: str | None = None,
    output_path: Path | str | None = None,
    axis_end: pd.Timestamp | None = None,
    events: list[tuple[str, str, str]] | None = None,
) -> plt.Figure:
    """Cria o grid 3x3 de reação de mercado intraday (estilo COPOM).

    Reproduz o Chart Grid da Bloomberg com 9 painéis (Nasdaq 100, S&P 500,
    Russell 2000, UST 2Y, UST 10Y, 2s10s, OIS 1Y1Y, DXY, VIX) e marca as linhas
    verticais de evento passadas em event_times. Eixo X em horário de Brasília.

    Args:
        market_data: DataFrame intraday (uma coluna por painel, ver
            MARKET_REACTION_PANELS). Índice datetime (tz-aware BRT ou naive BRT).
        event_times: dict de eventos {chave → Timestamp} (tz-aware ou naive, em
            horário de Brasília); só as chaves presentes em events são
            desenhadas. Chaves ausentes/None são ignoradas.
        meeting_date: Data da reunião (YYYYMMDD). Atualmente não usado (o gráfico
            não tem título); mantido por compatibilidade. Opcional.
        output_path: Caminho para salvar o PNG. Opcional.
        axis_end: Limite direito do eixo X (Timestamp em BRT). Se dado, estende
            todos os painéis com dados até esse horário, ainda que não haja dados
            até lá (área em branco à direita). Opcional.
        events: Definições dos eventos a marcar, lista de tuplas
            (chave, rótulo, estilo de linha). Default: MARKET_REACTION_EVENTS
            (decisão FOMC). Permite reusar o grid p/ outros eventos (ex.: payroll).

    Returns:
        Figura matplotlib (3x3).
    """
    event_defs = MARKET_REACTION_EVENTS if events is None else events

    # Índice em BRT naive para o matplotlib formatar a hora literal correta
    data = market_data.copy()
    if isinstance(data.index, pd.DatetimeIndex) and data.index.tz is not None:
        data.index = data.index.tz_convert(_TZ_BRT).tz_localize(None)

    axis_end_naive = _to_naive_brt(axis_end) if axis_end is not None else None

    events_naive: dict[str, pd.Timestamp] = {}
    if event_times:
        for key, ts in event_times.items():
            if ts is not None:
                events_naive[key] = _to_naive_brt(ts)

    fig, axes = plt.subplots(3, 3, figsize=(WORD_PAGE_WIDTH_INCHES, 8.5), dpi=WORD_DPI)
    axes_flat = axes.flatten()
    event_color = COPOM_COLORS[4]

    for idx, (ax, (key, title, vfmt, color_idx)) in enumerate(
        zip(axes_flat, MARKET_REACTION_PANELS)
    ):
        color = COPOM_COLORS[color_idx % len(COPOM_COLORS)]
        series = data[key].dropna() if key in data.columns else pd.Series(dtype="float64")

        if not series.empty:
            ax.plot(series.index, series.values, color=color, linewidth=1.3)

            # Linha de referência no nível inicial da janela (estilo Bloomberg)
            ax.axhline(
                series.iloc[0],
                color="#AEAEAE",
                linestyle=":",
                linewidth=0.8,
                alpha=0.7,
            )

            # Rótulo do último valor
            last_val = series.iloc[-1]
            ax.annotate(
                vfmt.format(last_val),
                xy=(series.index[-1], last_val),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                ha="left",
                fontsize=WORD_TICK_SIZE - 1,
                fontweight="bold",
                color=color,
                clip_on=False,
            )

            # Estender o eixo X até axis_end (mesmo sem dados até lá)
            if axis_end_naive is not None:
                ax.set_xlim(right=axis_end_naive)

            # Locator adaptativo (a janela pode ir da Ásia ao fim da coletiva)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.tick_params(axis="both", labelsize=WORD_TICK_SIZE - 2)
        else:
            ax.text(
                0.5,
                0.5,
                "sem dados",
                ha="center",
                va="center",
                fontsize=WORD_TICK_SIZE,
                color="#999999",
                transform=ax.transAxes,
            )
            ax.set_xticks([])
            ax.set_yticks([])

        # Linhas verticais de evento (rótulo inline só no 1º painel = Nasdaq 100)
        for ekey, elabel, els in event_defs:
            ets = events_naive.get(ekey)
            if ets is None:
                continue
            ax.axvline(ets, color=event_color, linestyle=els, linewidth=1.2, alpha=0.85)
            if idx == 0:
                ax.annotate(
                    elabel,
                    xy=(ets, 1.0),
                    xycoords=("data", "axes fraction"),
                    xytext=(-4, -4),
                    textcoords="offset points",
                    rotation=90,
                    va="top",
                    ha="right",
                    fontsize=WORD_TICK_SIZE - 1,
                    fontweight="bold",
                    color=event_color,
                )

        ax.set_title(title, fontsize=WORD_LABEL_SIZE, fontweight="bold")
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    fig.tight_layout()

    if output_path:
        save_chart_for_word(fig, output_path)

    return fig


def create_summary_table_image(
    data: pd.DataFrame,
    output_path: Path | str,
    title: str = "FOMC",
    col_widths: list[float] | None = None,
) -> None:
    """Create a styled table image matching Word document styling.

    Args:
        data: DataFrame to render as table.
        output_path: Path to save the PNG image.
        title: Title label on left side.
        col_widths: Optional column widths in inches.
    """
    n_rows = len(data) + 1  # +1 for header
    n_cols = len(data.columns)

    # Calculate figure size
    row_height = 0.35
    fig_height = max(1.5, n_rows * row_height + 0.5)
    fig_width = WORD_PAGE_WIDTH_INCHES

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=WORD_DPI)
    ax.axis("off")

    # Default column widths
    if col_widths is None:
        col_widths = [fig_width / n_cols] * n_cols

    # Create table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc="center",
        loc="center",
    )

    # Style table
    table.auto_set_font_size(False)
    table.set_fontsize(WORD_TICK_SIZE)

    for i in range(n_cols):
        # Header row
        cell = table[0, i]
        cell.set_facecolor(HEADER_COLOR)
        cell.set_text_props(color=HEADER_TEXT_COLOR, fontweight="bold")
        cell.set_height(row_height / fig_height)

        # Data rows
        for j in range(1, n_rows):
            cell = table[j, i]
            cell.set_facecolor(ALT_ROW_COLOR if j % 2 == 0 else ROW_COLOR)
            cell.set_height(row_height / fig_height)

    # Set column widths
    for i, width in enumerate(col_widths[:n_cols]):
        for j in range(n_rows):
            table[j, i].set_width(width / fig_width)

    # Add title label on left
    ax.text(
        -0.02,
        0.5,
        title,
        transform=ax.transAxes,
        fontsize=WORD_LABEL_SIZE,
        fontweight="bold",
        color=HEADER_COLOR,
        rotation=90,
        va="center",
        ha="right",
    )

    plt.tight_layout()
    save_chart_for_word(fig, output_path)
    plt.close(fig)


def create_rate_path_chart(
    rate_path: pd.DataFrame,
    current_rate: float | None = None,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Create a chart showing the expected rate path.

    Args:
        rate_path: DataFrame with columns: year, rate
        current_rate: Current Fed Funds rate (optional).
        output_path: Optional path to save the chart.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=WORD_FIGSIZE, dpi=WORD_DPI)

    if rate_path.empty:
        ax.text(
            0.5,
            0.5,
            "Dados nao disponiveis",
            ha="center",
            va="center",
            fontsize=WORD_LABEL_SIZE,
        )
    else:
        years = rate_path["year"].values
        rates = rate_path["rate"].values
        x_positions = range(len(years))

        # Plot rate path
        ax.plot(
            x_positions,
            rates,
            marker="o",
            markersize=10,
            color=COPOM_COLORS[0],
            linewidth=2.5,
        )

        # Add current rate if provided
        if current_rate is not None:
            ax.axhline(
                y=current_rate,
                color=COPOM_COLORS[4],
                linestyle="--",
                linewidth=1.5,
                label=f"Taxa Atual ({current_rate:.2f}%)",
            )

        # Format axes
        ax.set_xticks(x_positions)
        ax.set_xticklabels(years, fontsize=WORD_TICK_SIZE)
        ax.set_ylabel("Fed Funds Rate (%)", fontsize=WORD_LABEL_SIZE)
        ax.tick_params(axis="y", labelsize=WORD_TICK_SIZE)

        # Grid
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)

        if current_rate is not None:
            ax.legend(fontsize=WORD_LEGEND_SIZE)

    ax.set_title(
        "Projecao da Taxa Fed Funds",
        fontsize=WORD_TITLE_SIZE,
        fontweight="bold",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_path:
        save_chart_for_word(fig, output_path)

    return fig
