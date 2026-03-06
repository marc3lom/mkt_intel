"""Core modules for payroll data processing."""

from .calculations import (
    MESES_PTBR,
    MESES_PTBR_FULL,
    calculate_moving_averages,
    format_date_ptbr,
    format_release_summary,
    generate_summary_text,
    style_release_table,
)
from .data_loader import fetch_extended_data, fetch_payroll_data, get_latest_release
from .word_export import (
    WORD_DPI,
    WORD_FIGSIZE,
    WORD_FIGSIZE_DASHBOARD,
    WORD_FIGSIZE_TALL,
    WORD_FIGSIZE_WIDE,
    WORD_PAGE_WIDTH_INCHES,
    create_beveridge_curve,
    create_styled_table_image,
    create_unemployment_u6_chart,
    get_word_export_path,
    save_chart_for_word,
)
from .word_report import generate_payroll_report

__all__ = [
    "fetch_payroll_data",
    "fetch_extended_data",
    "get_latest_release",
    "calculate_moving_averages",
    "format_release_summary",
    "format_date_ptbr",
    "generate_summary_text",
    "style_release_table",
    "MESES_PTBR",
    "MESES_PTBR_FULL",
    "WORD_PAGE_WIDTH_INCHES",
    "WORD_DPI",
    "WORD_FIGSIZE",
    "WORD_FIGSIZE_TALL",
    "WORD_FIGSIZE_DASHBOARD",
    "WORD_FIGSIZE_WIDE",
    "create_styled_table_image",
    "create_unemployment_u6_chart",
    "create_beveridge_curve",
    "get_word_export_path",
    "save_chart_for_word",
    "generate_payroll_report",
]
