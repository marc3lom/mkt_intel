"""
Payroll report module for US Employment Situation analysis.

This module provides tools for fetching, analyzing, and visualizing
US Nonfarm Payrolls data from Bloomberg Terminal, FRED, and BLS sources.
"""

from .core.calculations import (
    calculate_moving_averages,
    format_date_ptbr,
    format_release_summary,
    generate_summary_text,
    style_release_table,
)
from .core.data_loader import fetch_extended_data, fetch_payroll_data, get_latest_release
from .core.word_report import generate_payroll_report

__all__ = [
    "fetch_payroll_data",
    "fetch_extended_data",
    "get_latest_release",
    "calculate_moving_averages",
    "format_release_summary",
    "format_date_ptbr",
    "generate_summary_text",
    "style_release_table",
    "generate_payroll_report",
]
