"""
Payroll report module for US Employment Situation analysis.

This module provides tools for fetching, analyzing, and visualizing
US Nonfarm Payrolls data from Bloomberg Terminal and BLS sources.
"""

from .core.calculations import (
    calculate_moving_averages,
    format_release_summary,
    style_release_table,
)
from .core.data_loader import fetch_payroll_data, get_latest_release

__all__ = [
    "fetch_payroll_data",
    "get_latest_release",
    "calculate_moving_averages",
    "format_release_summary",
    "style_release_table",
]
