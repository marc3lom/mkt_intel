"""
Word document export utilities for payroll analysis.

This module provides constants and helper functions for generating
charts and tables that are optimized for Word document insertion.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# === Word Export Constants ===
WORD_PAGE_WIDTH_INCHES: float = 7.0  # Full page width minus margins
WORD_DPI: int = 150  # Good balance of quality vs file size
WORD_FIGSIZE: tuple[float, float] = (7.0, 4.0)  # Standard chart
WORD_FIGSIZE_TALL: tuple[float, float] = (7.0, 8.0)  # Tall charts
WORD_FIGSIZE_DASHBOARD: tuple[float, float] = (7.0, 5.0)  # 2x2 dashboard
WORD_FIGSIZE_WIDE: tuple[float, float] = (7.0, 3.5)  # Half-page charts

# === Word Table Styling Colors ===
HEADER_COLOR: str = "#2E4C59"  # COPOM[0] - dark teal
HEADER_TEXT_COLOR: str = "#FFFFFF"  # White
ALT_ROW_COLOR: str = "#F5F0E8"  # Light tan/cream
ROW_COLOR: str = "#FFFFFF"  # White
LABEL_BG_COLOR: str = "#2E4C59"  # Same as header

# === Font Sizes for Word Charts ===
WORD_TITLE_SIZE: int = 14
WORD_LABEL_SIZE: int = 11
WORD_TICK_SIZE: int = 10
WORD_LEGEND_SIZE: int = 10
WORD_ANNOTATION_SIZE: int = 9

# === Public API ===
__all__ = [
    "WORD_PAGE_WIDTH_INCHES",
    "WORD_DPI",
    "WORD_FIGSIZE",
    "WORD_FIGSIZE_TALL",
    "WORD_FIGSIZE_DASHBOARD",
    "WORD_TITLE_SIZE",
    "WORD_LABEL_SIZE",
    "WORD_TICK_SIZE",
    "WORD_LEGEND_SIZE",
    "create_styled_table_image",
    "save_chart_for_word",
    "get_word_export_path",
]


def get_word_export_path(
    output_dir: Path,
    base_name: str,
    suffix: str = "_word",
) -> Path:
    """Generate consistent file path for Word-optimized exports.

    Args:
        output_dir: Directory for output files.
        base_name: Base name for the file (without extension).
        suffix: Suffix to add before extension.

    Returns:
        Path object for the Word-optimized export.
    """
    return output_dir / f"{base_name}{suffix}.png"


def save_chart_for_word(
    fig: plt.Figure,
    output_path: Path,
    dpi: int = WORD_DPI,
) -> None:
    """Save matplotlib figure with Word-optimized settings.

    Args:
        fig: Matplotlib figure to save.
        output_path: Path to save the image.
        dpi: DPI for the output image.
    """
    fig.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
        pad_inches=0.1,
    )


def create_styled_table_image(
    data: pd.DataFrame,
    output_path: Path,
    title: str = "Payroll",
    highlight_column: str | None = "Atual",
    col_widths: list[float] | None = None,
) -> None:
    """Create a styled table image matching Word document styling.

    Creates a table with:
    - Dark teal header row
    - Alternating white/tan row colors
    - Bold values in highlight column
    - Vertical label on left side

    Args:
        data: DataFrame with table data.
        output_path: Path to save the image.
        title: Vertical label text on left side.
        highlight_column: Column name to highlight in bold.
        col_widths: Optional list of column widths (proportional).
    """
    n_rows = len(data)
    n_cols = len(data.columns)

    # Calculate figure height based on rows
    row_height = 0.35
    header_height = 0.4
    fig_height = header_height + (n_rows * row_height) + 0.3

    # Create figure
    fig, ax = plt.subplots(figsize=(WORD_PAGE_WIDTH_INCHES, fig_height))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Column widths
    if col_widths is None:
        label_width = 0.08
        remaining = 1.0 - label_width
        col_widths = [remaining / n_cols] * n_cols
    else:
        label_width = 0.08
        total = sum(col_widths)
        col_widths = [(w / total) * (1.0 - label_width) for w in col_widths]

    # Calculate positions
    x_positions = [label_width]
    for w in col_widths[:-1]:
        x_positions.append(x_positions[-1] + w)

    y_header = 1.0 - header_height / fig_height
    row_h = row_height / fig_height

    # Draw vertical label on left
    ax.add_patch(
        plt.Rectangle(
            (0, 0),
            label_width,
            1.0,
            facecolor=LABEL_BG_COLOR,
            edgecolor="none",
        )
    )
    ax.text(
        label_width / 2,
        0.5,
        title,
        fontsize=WORD_LABEL_SIZE,
        fontweight="bold",
        color=HEADER_TEXT_COLOR,
        ha="center",
        va="center",
        rotation=90,
    )

    # Draw header row
    for i, col in enumerate(data.columns):
        x = x_positions[i]
        w = col_widths[i]

        # Header background
        ax.add_patch(
            plt.Rectangle(
                (x, y_header),
                w,
                header_height / fig_height,
                facecolor=HEADER_COLOR,
                edgecolor="none",
            )
        )

        # Header text
        ax.text(
            x + w / 2,
            y_header + (header_height / fig_height) / 2,
            col,
            fontsize=WORD_LABEL_SIZE,
            fontweight="bold",
            color=HEADER_TEXT_COLOR,
            ha="center",
            va="center",
        )

    # Draw data rows
    for row_idx, (_, row) in enumerate(data.iterrows()):
        y = y_header - (row_idx + 1) * row_h

        # Alternating row color
        bg_color = ROW_COLOR if row_idx % 2 == 0 else ALT_ROW_COLOR

        for col_idx, col in enumerate(data.columns):
            x = x_positions[col_idx]
            w = col_widths[col_idx]

            # Cell background
            ax.add_patch(
                plt.Rectangle(
                    (x, y),
                    w,
                    row_h,
                    facecolor=bg_color,
                    edgecolor="#E0E0E0",
                    linewidth=0.5,
                )
            )

            # Cell text
            value = row[col]
            if pd.isna(value):
                text = ""
            elif isinstance(value, float):
                text = f"{value:.1f}" if abs(value) < 100 else f"{value:.0f}"
            else:
                text = str(value)

            # Bold for highlight column
            weight = "bold" if col == highlight_column else "normal"

            ax.text(
                x + w / 2,
                y + row_h / 2,
                text,
                fontsize=WORD_TICK_SIZE,
                fontweight=weight,
                color="#333333",
                ha="center",
                va="center",
            )

    plt.tight_layout(pad=0)
    save_chart_for_word(fig, output_path)
    plt.close(fig)


def apply_word_chart_style(ax: plt.Axes) -> None:
    """Apply Word-optimized styling to a matplotlib axis.

    Args:
        ax: Matplotlib axis to style.
    """
    # Set font sizes
    ax.title.set_fontsize(WORD_TITLE_SIZE)
    ax.xaxis.label.set_fontsize(WORD_LABEL_SIZE)
    ax.yaxis.label.set_fontsize(WORD_LABEL_SIZE)
    ax.tick_params(axis="both", labelsize=WORD_TICK_SIZE)

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Set tick positions
    ax.xaxis.set_ticks_position("bottom")
    ax.yaxis.set_ticks_position("left")


def create_unemployment_u6_chart(
    data: pd.DataFrame,
    u6_data: pd.DataFrame,
    output_path: Path,
    plot_start_date: str | None = None,
) -> None:
    """Create U3 + U6 unemployment chart on the same axis.

    Args:
        data: Main payroll DataFrame with 'Unemployment' column.
        u6_data: Extended DataFrame with 'U6' column.
        output_path: Path to save the chart.
        plot_start_date: Optional start date to filter the chart.
    """
    from reports._style import COPOM, clean_axes

    merged = data[["Unemployment"]].join(u6_data[["U6"]], how="inner")
    if plot_start_date:
        merged = merged[merged.index >= pd.to_datetime(plot_start_date)]

    if merged.empty:
        return

    fig, ax = plt.subplots(figsize=WORD_FIGSIZE_WIDE, dpi=WORD_DPI)

    ax.plot(
        merged.index,
        merged["Unemployment"],
        color=COPOM[0],
        linewidth=2,
        label="U3 - Taxa de Desemprego",
    )
    ax.plot(
        merged.index,
        merged["U6"],
        color=COPOM[5],
        linewidth=2,
        linestyle="--",
        label="U6 - Desemprego Ampliado",
    )
    ax.fill_between(merged.index, merged["Unemployment"], merged["U6"], alpha=0.1, color=COPOM[9])

    ax.set_title("Desemprego U3 vs U6 (%)", fontsize=WORD_TITLE_SIZE, fontweight="bold")
    ax.set_ylabel("%", fontsize=WORD_LABEL_SIZE)
    ax.tick_params(axis="both", labelsize=WORD_TICK_SIZE)
    ax.legend(loc="upper right", fontsize=WORD_LEGEND_SIZE)
    clean_axes(ax)

    plt.tight_layout()
    save_chart_for_word(fig, output_path)
    plt.close(fig)


def create_beveridge_curve(
    unemployment: pd.Series,
    jolts: pd.Series,
    output_path: Path,
    plot_start_date: str | None = None,
) -> None:
    """Create Beveridge curve (JOLTS Job Openings vs Unemployment Rate).

    Args:
        unemployment: Series with unemployment rate.
        jolts: Series with JOLTS job openings (thousands).
        output_path: Path to save the chart.
        plot_start_date: Optional start date to filter.
    """
    from reports._style import COPOM, clean_axes

    merged = pd.DataFrame({"Unemployment": unemployment, "JOLTS": jolts}).dropna()
    if plot_start_date:
        merged = merged[merged.index >= pd.to_datetime(plot_start_date)]

    if merged.empty:
        return

    fig, ax = plt.subplots(figsize=WORD_FIGSIZE_WIDE, dpi=WORD_DPI)

    n = len(merged)

    ax.scatter(
        merged["Unemployment"],
        merged["JOLTS"],
        c=range(n),
        cmap="viridis",
        s=30,
        alpha=0.7,
        zorder=3,
    )

    # Connect with line
    ax.plot(
        merged["Unemployment"], merged["JOLTS"], color=COPOM[9], linewidth=0.5, alpha=0.5, zorder=2
    )

    # Mark latest point
    ax.scatter(
        merged["Unemployment"].iloc[-1],
        merged["JOLTS"].iloc[-1],
        color=COPOM[5],
        s=100,
        zorder=4,
        edgecolors="black",
        linewidth=1.5,
        label="Ultimo",
    )

    ax.set_title("Curva de Beveridge", fontsize=WORD_TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Taxa de Desemprego (%)", fontsize=WORD_LABEL_SIZE)
    ax.set_ylabel("JOLTS Job Openings (mil)", fontsize=WORD_LABEL_SIZE)
    ax.tick_params(axis="both", labelsize=WORD_TICK_SIZE)
    ax.legend(loc="upper right", fontsize=WORD_LEGEND_SIZE)
    clean_axes(ax)

    plt.tight_layout()
    save_chart_for_word(fig, output_path)
    plt.close(fig)
