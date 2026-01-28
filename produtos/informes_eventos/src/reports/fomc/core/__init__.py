"""
Core modules for FOMC analysis.

This package contains the core functionality for FOMC analysis including
data loading, PDF parsing, calculations, and Word export utilities.
"""

from .calculations import (
    calculate_projection_changes,
    calculate_rate_path,
    format_projection_table,
    get_meeting_summary,
    process_dot_plot,
)
from .data_loader import (
    FOMC_TICKERS,
    fetch_market_reaction,
    get_fomc_dates,
    get_meeting_documents,
    load_market_reaction_data,
    load_sep_data,
)
from .fed_scraper import (
    check_for_updates,
    fetch_latest_documents,
    get_available_documents,
    sync_all_documents,
)
from .pdf_parser import (
    get_projection_dates,
    parse_minutes,
    parse_projection_table,
    parse_statement,
)
from .word_export import (
    WORD_DPI,
    WORD_FIGSIZE,
    WORD_FIGSIZE_DASHBOARD,
    create_dot_plot_chart,
    create_market_reaction_charts,
    create_rate_path_chart,
    create_sep_charts,
    create_summary_table_image,
    save_chart_for_word,
)

__all__ = [
    # Data loader
    "FOMC_TICKERS",
    "fetch_market_reaction",
    "get_fomc_dates",
    "get_meeting_documents",
    "load_market_reaction_data",
    "load_sep_data",
    # Fed scraper
    "check_for_updates",
    "fetch_latest_documents",
    "get_available_documents",
    "sync_all_documents",
    # PDF parser
    "get_projection_dates",
    "parse_minutes",
    "parse_projection_table",
    "parse_statement",
    # Calculations
    "calculate_projection_changes",
    "calculate_rate_path",
    "format_projection_table",
    "get_meeting_summary",
    "process_dot_plot",
    # Word export
    "WORD_DPI",
    "WORD_FIGSIZE",
    "WORD_FIGSIZE_DASHBOARD",
    "create_dot_plot_chart",
    "create_market_reaction_charts",
    "create_rate_path_chart",
    "create_sep_charts",
    "create_summary_table_image",
    "save_chart_for_word",
]
