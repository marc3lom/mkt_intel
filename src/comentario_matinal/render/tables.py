"""Generic table rendering engine for calendar-style PNG tables."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.estilo import COLORS, FONT_SIZES
from comentario_matinal.render.output import save_figure

logger = logging.getLogger("comentario_matinal")


# ---------------------------------------------------------------------------
# Value formatting & highlight helpers
# ---------------------------------------------------------------------------


def format_value(val) -> str:
    """Format a value for display in the table."""
    if pd.isna(val):
        return "-"
    if isinstance(val, (int, float)):
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"
    return str(val)


def should_highlight_atual(row) -> bool:
    """Return True if ATUAL > ESTIMATIVA (highlight in green)."""
    try:
        atual = row.get("ATUAL")
        estimativa = row.get("ESTIMATIVA")
        if pd.notna(atual) and pd.notna(estimativa):
            return float(atual) > float(estimativa)
    except (ValueError, TypeError):
        pass
    return False


def should_highlight_revisado(row) -> bool:
    """Return True if REVISADO != ANTERIOR (highlight in green)."""
    try:
        revisado = row.get("REVISADO")
        anterior = row.get("ANTERIOR")
        if pd.notna(revisado) and revisado != "-":
            if pd.notna(anterior):
                return float(revisado) != float(anterior)
    except (ValueError, TypeError):
        pass
    return False


# ---------------------------------------------------------------------------
# TableSpec & pre-built specs
# ---------------------------------------------------------------------------


@dataclass
class TableSpec:
    """Specification for a single table section."""

    title: str
    columns: list[str]
    col_widths: list[float]
    highlight_rules: dict[str, Callable] = field(default_factory=dict)
    left_align_col: str | None = None


ECO_TABLE_SPEC = TableSpec(
    title="CALENDÁRIO ECONÔMICO",
    columns=[
        "PAÍS", "DATA", "HORÁRIO", "EVENTO", "PERÍODO",
        "ESTIMATIVA", "ATUAL", "ANTERIOR", "REVISADO",
    ],
    col_widths=[0.12, 0.10, 0.08, 0.25, 0.08, 0.10, 0.08, 0.10, 0.09],
    highlight_rules={
        "ATUAL": should_highlight_atual,
        "REVISADO": should_highlight_revisado,
    },
)

CB_TABLE_SPEC = TableSpec(
    title="BANCOS CENTRAIS",
    columns=["PAÍS", "DATA", "HORÁRIO", "EVENTO"],
    col_widths=[0.15, 0.12, 0.10, 0.61],
    left_align_col="EVENTO",
)

CB_TABLE_SPEC_COMBINED = TableSpec(
    title="BANCOS CENTRAIS",
    columns=["PAÍS", "DATA", "HORÁRIO", "EVENTO"],
    col_widths=[0.12, 0.10, 0.08, 0.68],
    left_align_col="EVENTO",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Ensure all columns exist and format dates."""
    for col in columns:
        if col not in df.columns:
            df[col] = "-"
    df = df[columns].copy()
    if "DATA" in df.columns:
        df["DATA"] = df["DATA"].apply(
            lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x)
        )
    return df


def _compute_x_positions(col_widths: list[float]) -> list[float]:
    """Compute x start positions for each column."""
    positions = [0.02]
    for w in col_widths[:-1]:
        positions.append(positions[-1] + w)
    return positions


# ---------------------------------------------------------------------------
# Standalone table rendering
# ---------------------------------------------------------------------------


def render_table(
    df: pd.DataFrame,
    spec: TableSpec,
    save_path: Path | None = None,
    allowed_root: Path | None = None,
) -> Figure | None:
    """Render a single table figure.

    Returns the Figure for inline display. Writes a PNG only when
    ``save_path`` is provided, and only inside ``allowed_root``, which
    ``save_figure`` requires whenever a PNG is actually written.
    """
    if df.empty:
        logger.warning("Empty DataFrame, cannot render %s", spec.title)
        return None

    df = _prepare_dataframe(df, spec.columns)
    n_rows = len(df)

    # Layout differs for ECO (9 cols) vs CB (4 cols) standalone tables
    is_eco = len(spec.columns) > 4

    fig_width = 14 if is_eco else 10
    fig_height = max(3 if is_eco else 2.5, 1 + n_rows * 0.4)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    title_y = 0.95 if is_eco else 0.92
    table_top = 0.85 if is_eco else 0.80
    usable_height = 0.7 if is_eco else 0.65
    row_height = usable_height / (n_rows + 1)

    # Title
    ax.text(
        0.5, title_y, spec.title,
        fontsize=FONT_SIZES["title"], fontweight="bold", color=COLORS["title"],
        ha="center", va="top", transform=ax.transAxes,
    )

    # Header
    x_positions = _compute_x_positions(spec.col_widths)
    header_y = table_top

    header_rect = mpatches.FancyBboxPatch(
        (0.01, header_y - row_height), 0.98, row_height,
        boxstyle="round,pad=0.01", facecolor=COLORS["header_bg"],
        edgecolor="none", transform=ax.transAxes,
    )
    ax.add_patch(header_rect)

    hdr_fs = FONT_SIZES["header"] if is_eco else FONT_SIZES["header_cb"]
    for i, col in enumerate(spec.columns):
        ax.text(
            x_positions[i] + spec.col_widths[i] / 2, header_y - row_height / 2,
            col, fontsize=hdr_fs, fontweight="bold",
            color=COLORS["header_text"], ha="center", va="center",
            transform=ax.transAxes,
        )

    # Data rows
    cell_fs = FONT_SIZES["cell"] if is_eco else FONT_SIZES["cell_cb"]

    for row_idx, (_, row) in enumerate(df.iterrows()):
        y = header_y - (row_idx + 1) * row_height - row_height

        bg_color = COLORS["row_odd"] if row_idx % 2 == 0 else COLORS["row_even"]
        row_rect = mpatches.FancyBboxPatch(
            (0.01, y), 0.98, row_height,
            boxstyle="round,pad=0.01", facecolor=bg_color,
            edgecolor="none", transform=ax.transAxes,
        )
        ax.add_patch(row_rect)

        for col_idx, col in enumerate(spec.columns):
            value = format_value(row[col])

            text_color = COLORS["text_normal"]
            if col in spec.highlight_rules and spec.highlight_rules[col](row):
                text_color = COLORS["text_positive"]

            if col == spec.left_align_col:
                ha = "left"
                x_offset = 0.01
            else:
                ha = "center"
                x_offset = spec.col_widths[col_idx] / 2

            ax.text(
                x_positions[col_idx] + x_offset, y + row_height / 2,
                value, fontsize=cell_fs, color=text_color,
                ha=ha, va="center", transform=ax.transAxes,
            )

    plt.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path, allowed_root=allowed_root)

    return fig


# ---------------------------------------------------------------------------
# Combined (stacked) table rendering
# ---------------------------------------------------------------------------


def render_combined_tables(
    tables: list[tuple[pd.DataFrame, TableSpec]],
    save_path: Path | None = None,
    fig_width: float = 14,
    allowed_root: Path | None = None,
) -> Figure | None:
    """Render N tables stacked vertically into a single figure.

    Returns the Figure for inline display. Writes a PNG only when
    ``save_path`` is provided, and only inside ``allowed_root``, which
    ``save_figure`` requires whenever a PNG is actually written.
    """
    non_empty = [(df, spec) for df, spec in tables if not df.empty]
    if not non_empty:
        logger.warning("All DataFrames empty, cannot render combined table")
        return None

    prepared = [(_prepare_dataframe(df, spec.columns), spec) for df, spec in non_empty]

    # Sizing constants (pixels)
    row_height_px = 28
    header_height_px = 35
    title_height_px = 45
    spacing_px = 30

    section_heights = []
    for df, _spec in prepared:
        h = title_height_px + header_height_px + len(df) * row_height_px
        section_heights.append(h)

    total_height_px = sum(section_heights) + spacing_px * (len(prepared) - 1) + 40
    fig_height = max(4, total_height_px / 80)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    total_content = sum(section_heights) + spacing_px * (len(prepared) - 1)
    current_y = 0.95

    for sec_idx, (df, spec) in enumerate(prepared):
        n_rows = len(df)
        section_ratio = section_heights[sec_idx] / total_content if total_content > 0 else 0.5
        row_height = 0.8 * section_ratio / (n_rows + 2)

        is_eco = len(spec.columns) > 4
        title_fs = FONT_SIZES["combined_title"]
        header_fs = FONT_SIZES["combined_header_eco"] if is_eco else FONT_SIZES["combined_header_cb"]
        cell_fs = FONT_SIZES["combined_cell_eco"] if is_eco else FONT_SIZES["combined_cell_cb"]

        x_positions = _compute_x_positions(spec.col_widths)

        # Title
        ax.text(
            0.5, current_y, spec.title,
            fontsize=title_fs, fontweight="bold", color=COLORS["title"],
            ha="center", va="top", transform=ax.transAxes,
        )
        current_y -= row_height * 1.2

        # Header
        header_rect = mpatches.FancyBboxPatch(
            (0.01, current_y - row_height), 0.98, row_height,
            boxstyle="round,pad=0.01", facecolor=COLORS["header_bg"],
            edgecolor="none", transform=ax.transAxes,
        )
        ax.add_patch(header_rect)

        for i, col in enumerate(spec.columns):
            ax.text(
                x_positions[i] + spec.col_widths[i] / 2, current_y - row_height / 2,
                col, fontsize=header_fs, fontweight="bold",
                color=COLORS["header_text"], ha="center", va="center",
                transform=ax.transAxes,
            )

        current_y -= row_height

        # Data rows
        for row_idx, (_, row) in enumerate(df.iterrows()):
            y = current_y - row_height

            bg_color = COLORS["row_odd"] if row_idx % 2 == 0 else COLORS["row_even"]
            row_rect = mpatches.FancyBboxPatch(
                (0.01, y), 0.98, row_height,
                boxstyle="round,pad=0.01", facecolor=bg_color,
                edgecolor="none", transform=ax.transAxes,
            )
            ax.add_patch(row_rect)

            for col_idx, col in enumerate(spec.columns):
                value = format_value(row[col])

                text_color = COLORS["text_normal"]
                if col in spec.highlight_rules and spec.highlight_rules[col](row):
                    text_color = COLORS["text_positive"]

                if col == spec.left_align_col:
                    ha = "left"
                    x_offset = 0.01
                else:
                    ha = "center"
                    x_offset = spec.col_widths[col_idx] / 2

                ax.text(
                    x_positions[col_idx] + x_offset, y + row_height / 2,
                    value, fontsize=cell_fs, color=text_color,
                    ha=ha, va="center", transform=ax.transAxes,
                )

            current_y = y

        # Spacing between sections
        if sec_idx < len(prepared) - 1:
            spacing_ratio = spacing_px / total_content if total_content > 0 else 0.05
            current_y -= spacing_ratio * 0.5

    plt.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path, allowed_root=allowed_root)

    return fig
