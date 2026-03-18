"""
Core modules for FOMC analysis.

This package contains the core functionality for FOMC analysis including
data loading, PDF parsing, calculations, Word export and Word report generation.
"""

from .calculations import (
    classify_change_direction,
    calculate_projection_changes,
    calculate_rate_path,
    format_projection_table,
    get_meeting_summary,
    get_prior_meeting_label,
    get_prior_sep_meeting_date,
    process_dot_plot,
)
from .data_loader import (
    DOTS_TICKERS,
    FOMC_TICKERS,
    fetch_market_reaction,
    get_fomc_dates,
    get_meeting_documents,
    get_prior_sep_projections,
    is_sep_meeting,
    load_dots_history,
    load_dots_snapshot,
    load_market_reaction_data,
    load_sep_data,
    save_sep_to_excel,
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
from .word_report import generate_fomc_report

__all__ = [
    # Data loader
    "DOTS_TICKERS",
    "FOMC_TICKERS",
    "fetch_market_reaction",
    "get_fomc_dates",
    "get_meeting_documents",
    "get_prior_sep_projections",
    "is_sep_meeting",
    "load_dots_history",
    "load_dots_snapshot",
    "load_market_reaction_data",
    "load_sep_data",
    "save_sep_to_excel",
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
    "classify_change_direction",
    "calculate_projection_changes",
    "calculate_rate_path",
    "format_projection_table",
    "get_meeting_summary",
    "get_prior_meeting_label",
    "get_prior_sep_meeting_date",
    "process_dot_plot",
    # Word export (charts)
    "WORD_DPI",
    "WORD_FIGSIZE",
    "WORD_FIGSIZE_DASHBOARD",
    "create_dot_plot_chart",
    "create_market_reaction_charts",
    "create_rate_path_chart",
    "create_sep_charts",
    "create_summary_table_image",
    "save_chart_for_word",
    # Word report
    "generate_fomc_report",
]
