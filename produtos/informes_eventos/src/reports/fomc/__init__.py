"""
FOMC Analysis Module.

This module provides tools for analyzing Federal Open Market Committee
(FOMC) meetings, including statement parsing, projection visualization,
and market reaction analysis.

Modules:
    core.data_loader: Bloomberg data fetching and Excel file loading
    core.pdf_parser: PDF document parsing for FOMC materials
    core.fed_scraper: Federal Reserve website scraping
    core.calculations: Projection calculations and formatting
    core.word_export: Word-optimized chart and table generation
"""

from .core import (
    # Data loading
    FOMC_TICKERS,
    fetch_market_reaction,
    get_fomc_dates,
    get_meeting_documents,
    load_market_reaction_data,
    load_sep_data,
    # Fed scraper
    check_for_updates,
    fetch_latest_documents,
    get_available_documents,
    sync_all_documents,
    # PDF parsing
    get_projection_dates,
    parse_minutes,
    parse_projection_table,
    parse_statement,
    # Calculations
    calculate_projection_changes,
    calculate_rate_path,
    format_projection_table,
    get_meeting_summary,
    process_dot_plot,
    # Word export
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
    # Data loading
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
    # PDF parsing
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
