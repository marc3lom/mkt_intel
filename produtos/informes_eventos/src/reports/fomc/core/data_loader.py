"""
Bloomberg data loader and file utilities for FOMC analysis.

This module provides functions for fetching market data from Bloomberg
and loading data from local Excel files.
"""

import datetime as dt
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Bloomberg tickers for FOMC-related market data
FOMC_TICKERS: dict[str, str] = {
    "UST_2Y": "USGG2YR Index",
    "UST_10Y": "USGG10YR Index",
    "SPX": "SPX Index",
    "DXY": "DXY Curncy",
    "FED_FUNDS": "FDTR Index",
}

# Document type patterns
DOCUMENT_PATTERNS: dict[str, str] = {
    "statement": r"monetary(\d{8})a1\.pdf",
    "minutes": r"fomcminutes(\d{8})\.pdf",
    "presser": r"FOMCpresconf(\d{8})\.pdf|fomcpresconf(\d{8})\.pdf",
    "projections": r"fomcprojtabl(\d{8})\.pdf",
}


def _get_bloomberg_client() -> Any:
    """Get Bloomberg client, raising error if not available.

    Returns:
        Bloomberg blp module.

    Raises:
        RuntimeError: If Bloomberg is not available.
    """
    try:
        from xbbg import blp

        return blp
    except ImportError:
        raise RuntimeError(
            "Bloomberg (xbbg) not available. Install with: uv add xbbg"
        )


def _get_module_path() -> Path:
    """Get the path to the fomc module root."""
    return Path(__file__).parent.parent


def get_fomc_dates() -> list[str]:
    """Get list of all available FOMC meeting dates from local documents.

    Returns:
        List of meeting dates in YYYYMMDD format, sorted descending.
    """
    docs_path = _get_module_path() / "input" / "committee_meeting_docs"

    if not docs_path.exists():
        logger.warning(f"Committee docs folder not found: {docs_path}")
        return []

    dates = set()
    for pdf_file in docs_path.glob("*.pdf"):
        # Try to extract date from each document type
        for pattern in DOCUMENT_PATTERNS.values():
            match = re.match(pattern, pdf_file.name, re.IGNORECASE)
            if match:
                # Get the first non-None group (date)
                date = next((g for g in match.groups() if g), None)
                if date:
                    dates.add(date)
                break

    return sorted(dates, reverse=True)


def get_meeting_documents(date: str) -> dict[str, Path | None]:
    """Get all available documents for a specific FOMC meeting.

    Args:
        date: Meeting date in YYYYMMDD format.

    Returns:
        Dictionary mapping document types to file paths (or None if missing).
    """
    docs_path = _get_module_path() / "input" / "committee_meeting_docs"

    documents: dict[str, Path | None] = {
        "statement": None,
        "minutes": None,
        "presser": None,
        "projections": None,
    }

    if not docs_path.exists():
        return documents

    # Look for each document type
    for doc_type, pattern in DOCUMENT_PATTERNS.items():
        for pdf_file in docs_path.glob("*.pdf"):
            match = re.match(pattern, pdf_file.name, re.IGNORECASE)
            if match:
                matched_date = next((g for g in match.groups() if g), None)
                if matched_date == date:
                    documents[doc_type] = pdf_file
                    break

    return documents


def fetch_market_reaction(
    date: str,
    start_time: str = "13:00",
    end_time: str = "16:00",
) -> pd.DataFrame:
    """Fetch intraday market data around an FOMC announcement.

    Args:
        date: FOMC meeting date in YYYYMMDD format.
        start_time: Start time for data (HH:MM). Default 13:00 ET.
        end_time: End time for data (HH:MM). Default 16:00 ET.

    Returns:
        DataFrame with intraday prices for UST 2Y, 10Y, SPX, DXY.

    Raises:
        RuntimeError: If Bloomberg is not available or data fetch fails.
    """
    blp = _get_bloomberg_client()

    # Parse date
    meeting_date = dt.datetime.strptime(date, "%Y%m%d")

    # Construct datetime range
    start_dt = dt.datetime.combine(
        meeting_date.date(),
        dt.datetime.strptime(start_time, "%H:%M").time(),
    )
    end_dt = dt.datetime.combine(
        meeting_date.date(),
        dt.datetime.strptime(end_time, "%H:%M").time(),
    )

    tickers = list(FOMC_TICKERS.values())

    logger.info(f"Fetching intraday data for {date} from {start_time} to {end_time}")

    try:
        data = blp.bdib(
            ticker=tickers,
            dt=meeting_date.date(),
            session="allday",
        )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch intraday data: {e}")

    if data is None or data.empty:
        raise RuntimeError("No intraday data returned from Bloomberg")

    # Rename columns from tickers to friendly names
    ticker_to_name = {v: k for k, v in FOMC_TICKERS.items()}

    # Filter to time range and rename
    if isinstance(data.index, pd.DatetimeIndex):
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]

    # Flatten multi-index columns if needed
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            ticker_to_name.get(col[0], col[0]) for col in data.columns
        ]
    else:
        data = data.rename(columns=ticker_to_name)

    logger.info(f"Retrieved {len(data)} data points")
    return data


def load_sep_data(sheet_name: str | None = None) -> pd.DataFrame:
    """Load Summary of Economic Projections data from Excel file.

    Args:
        sheet_name: Specific sheet to load (e.g., "dez 25", "jun 25").
                   If None, loads the most recent sheet.

    Returns:
        DataFrame with SEP projections.

    Raises:
        RuntimeError: If SEP file not found or parsing fails.
    """
    sep_path = (
        _get_module_path() / "input" / "email_info" / "SEP.xlsx"
    )

    if not sep_path.exists():
        raise RuntimeError(f"SEP file not found: {sep_path}")

    try:
        # Get sheet names to find most recent if not specified
        xl = pd.ExcelFile(sep_path)
        sheets = xl.sheet_names

        if sheet_name is None:
            # Filter to month-year sheets and get most recent
            date_sheets = [
                s for s in sheets
                if re.match(r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+\d{2}", s, re.IGNORECASE)
            ]
            if date_sheets:
                sheet_name = date_sheets[0]  # Assuming sorted by recency
            else:
                sheet_name = sheets[0]

        logger.info(f"Loading SEP data from sheet: {sheet_name}")
        data = pd.read_excel(sep_path, sheet_name=sheet_name)

        return data

    except Exception as e:
        raise RuntimeError(f"Failed to load SEP data: {e}")


def load_market_reaction_data(sheet_name: str = "Market Reaction") -> pd.DataFrame:
    """Load market reaction data from Excel file.

    Args:
        sheet_name: Sheet to load. Default is "Market Reaction".

    Returns:
        DataFrame with market reaction data.

    Raises:
        RuntimeError: If file not found or parsing fails.
    """
    file_path = (
        _get_module_path() / "input" / "email_info" / "Market_Reaction_FOMC.xlsm"
    )

    if not file_path.exists():
        raise RuntimeError(f"Market reaction file not found: {file_path}")

    try:
        logger.info(f"Loading market reaction data from sheet: {sheet_name}")
        data = pd.read_excel(file_path, sheet_name=sheet_name)
        return data

    except Exception as e:
        raise RuntimeError(f"Failed to load market reaction data: {e}")
