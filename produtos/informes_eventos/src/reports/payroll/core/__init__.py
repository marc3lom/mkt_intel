"""Core modules for payroll data processing."""

from .calculations import (
    calculate_moving_averages,
    format_release_summary,
    style_release_table,
)
from .data_loader import fetch_payroll_data, get_latest_release
from .word_export import (
    WORD_DPI,
    WORD_FIGSIZE,
    WORD_FIGSIZE_DASHBOARD,
    WORD_FIGSIZE_TALL,
    WORD_PAGE_WIDTH_INCHES,
    create_styled_table_image,
    get_word_export_path,
    save_chart_for_word,
)

__all__ = [
    "fetch_payroll_data",
    "get_latest_release",
    "calculate_moving_averages",
    "format_release_summary",
    "style_release_table",
    "WORD_PAGE_WIDTH_INCHES",
    "WORD_DPI",
    "WORD_FIGSIZE",
    "WORD_FIGSIZE_TALL",
    "WORD_FIGSIZE_DASHBOARD",
    "create_styled_table_image",
    "get_word_export_path",
    "save_chart_for_word",
]
