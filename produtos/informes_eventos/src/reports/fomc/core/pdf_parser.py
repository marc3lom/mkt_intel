"""
PDF parser for FOMC documents.

This module provides functions for extracting data from FOMC PDF documents
including statements, projection tables, and meeting minutes.
"""

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _ensure_pdfplumber() -> Any:
    """Ensure pdfplumber is available.

    Returns:
        pdfplumber module.

    Raises:
        RuntimeError: If pdfplumber is not installed.
    """
    try:
        import pdfplumber

        return pdfplumber
    except ImportError:
        raise RuntimeError(
            "pdfplumber not available. Install with: uv add pdfplumber"
        )


def parse_projection_table(pdf_path: Path | str) -> dict[str, pd.DataFrame]:
    """Parse FOMC projection table PDF to extract economic projections.

    Extracts median projections for GDP, unemployment, inflation, and
    fed funds rate from the Summary of Economic Projections PDF.

    Args:
        pdf_path: Path to fomcprojtabl*.pdf file.

    Returns:
        Dictionary with keys:
        - 'medians': DataFrame with median projections by variable and year
        - 'dot_distribution': DataFrame with fed funds rate distribution

    Raises:
        RuntimeError: If parsing fails.
    """
    pdfplumber = _ensure_pdfplumber()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")

    logger.info(f"Parsing projection table: {pdf_path.name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Page 2 contains Table 1 with median projections
            medians_df = _extract_table1_medians(pdf)

            # Page 9 contains fed funds rate distribution
            dot_dist_df = _extract_fed_funds_distribution(pdf)

            return {
                "medians": medians_df,
                "dot_distribution": dot_dist_df,
            }

    except Exception as e:
        raise RuntimeError(f"Failed to parse projection table: {e}")


def _extract_table1_medians(pdf: Any) -> pd.DataFrame:
    """Extract median projections from Table 1 on page 2.

    Args:
        pdf: Open pdfplumber PDF object.

    Returns:
        DataFrame with columns: Variable, 2025, 2026, 2027, 2028
    """
    if len(pdf.pages) < 2:
        return pd.DataFrame()

    page = pdf.pages[1]  # Page 2 (0-indexed)
    text = page.extract_text() or ""

    # Variables to extract - match the indicator name then capture 4-5 numbers
    variable_patterns = [
        ("Change in real GDP", r"ChangeinrealGDP\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"),
        ("Unemployment rate", r"Unemploymentrate\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"),
        ("PCE inflation", r"PCEinflation\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"),
        ("Core PCE inflation", r"CorePCEinflation\d*\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"),
        ("Federal funds rate", r"Federalfundsrate\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"),
    ]

    records = []
    for var_name, pattern in variable_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            values = []
            for i in range(1, len(match.groups()) + 1):
                try:
                    val = float(match.group(i))
                    values.append(val)
                except (ValueError, IndexError):
                    values.append(None)

            # Ensure we have 4 values
            while len(values) < 4:
                values.append(None)

            records.append(
                {
                    "Variable": var_name,
                    "2025": values[0],
                    "2026": values[1],
                    "2027": values[2],
                    "2028": values[3] if len(values) > 3 else None,
                }
            )

    return pd.DataFrame(records)


def _extract_fed_funds_distribution(pdf: Any) -> pd.DataFrame:
    """Extract federal funds rate distribution from Figure 3.E.

    This extracts the histogram data for fed funds rate projections
    by year to create the dot plot visualization.

    Args:
        pdf: Open pdfplumber PDF object.

    Returns:
        DataFrame with rate ranges and participant counts by year.
    """
    # Find the page with Figure 3.E (fed funds distribution)
    target_page = None
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Figure3.E" in text.replace(" ", "") or "federal funds rate" in text.lower():
            if "Distribution" in text and "participants" in text.lower():
                target_page = i
                break

    if target_page is None:
        logger.warning("Could not find fed funds distribution page")
        return pd.DataFrame()

    page = pdf.pages[target_page]
    text = page.extract_text() or ""

    # Parse the distribution data
    # Format: ranges like "3.13- 3.37" with participant counts
    rate_ranges = []
    pattern = r"([\d.]+)[−-]([\d.]+)"

    matches = re.findall(pattern, text)
    for low, high in matches:
        try:
            rate_ranges.append(
                {
                    "rate_low": float(low),
                    "rate_high": float(high),
                    "midpoint": (float(low) + float(high)) / 2,
                }
            )
        except ValueError:
            continue

    return pd.DataFrame(rate_ranges)


def parse_statement(pdf_path: Path | str) -> dict[str, Any]:
    """Parse FOMC monetary policy statement PDF.

    Extracts key information from the statement including:
    - Target rate range
    - Decision type (hold, cut, hike)
    - Key policy language
    - Voting record

    Args:
        pdf_path: Path to monetary*.pdf file.

    Returns:
        Dictionary with extracted statement information.

    Raises:
        RuntimeError: If parsing fails.
    """
    pdfplumber = _ensure_pdfplumber()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")

    logger.info(f"Parsing statement: {pdf_path.name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return {}

            page = pdf.pages[0]
            text = page.extract_text() or ""

            return _parse_statement_text(text)

    except Exception as e:
        raise RuntimeError(f"Failed to parse statement: {e}")


def _parse_statement_text(text: str) -> dict[str, Any]:
    """Parse statement text to extract key information.

    Args:
        text: Full text from statement PDF.

    Returns:
        Dictionary with parsed statement data.
    """
    result: dict[str, Any] = {
        "target_rate_low": None,
        "target_rate_high": None,
        "decision": None,
        "unanimous": None,
        "dissenters": [],
        "key_phrases": [],
    }

    # Extract target rate range
    # Pattern: "target range for the federal funds rate at 4-1/4 to 4-1/2 percent"
    rate_pattern = r"target range.*?(\d+(?:-\d+/\d+)?)\s*to\s*(\d+(?:-\d+/\d+)?)\s*percent"
    rate_match = re.search(rate_pattern, text, re.IGNORECASE)

    if rate_match:
        result["target_rate_low"] = _parse_rate_fraction(rate_match.group(1))
        result["target_rate_high"] = _parse_rate_fraction(rate_match.group(2))

    # Determine decision type
    if "decided to maintain" in text.lower() or "decided to hold" in text.lower():
        result["decision"] = "hold"
    elif "decided to lower" in text.lower() or "decided to reduce" in text.lower():
        result["decision"] = "cut"
    elif "decided to raise" in text.lower() or "decided to increase" in text.lower():
        result["decision"] = "hike"

    # Check for unanimous decision
    result["unanimous"] = "voting against" not in text.lower()

    # Extract dissenters if any
    dissent_pattern = r"Voting against.*?:\s*([^.]+)"
    dissent_match = re.search(dissent_pattern, text, re.IGNORECASE)
    if dissent_match:
        dissenters = dissent_match.group(1).strip()
        result["dissenters"] = [d.strip() for d in dissenters.split(",")]

    # Extract key policy phrases
    key_patterns = [
        r"inflation remains ([\w\s]+)",
        r"economic activity ([\w\s]+)",
        r"labor market ([\w\s]+)",
        r"risks .* are ([\w\s]+)",
    ]

    for pattern in key_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["key_phrases"].append(match.group(0).strip())

    return result


def _parse_rate_fraction(rate_str: str) -> float:
    """Parse rate string that may contain fractions.

    Args:
        rate_str: Rate string like "4-1/4" or "4.25"

    Returns:
        Float rate value.
    """
    if "-" in rate_str and "/" in rate_str:
        # Format: "4-1/4" means 4.25
        parts = rate_str.split("-")
        whole = float(parts[0])
        if "/" in parts[1]:
            num, denom = parts[1].split("/")
            fraction = float(num) / float(denom)
            return whole + fraction
        return whole
    else:
        return float(rate_str)


def parse_minutes(pdf_path: Path | str) -> dict[str, Any]:
    """Parse FOMC meeting minutes PDF.

    Extracts key sections from the minutes including:
    - Economic outlook discussion
    - Policy discussion
    - Voting record

    Args:
        pdf_path: Path to fomcminutes*.pdf file.

    Returns:
        Dictionary with extracted minutes information.

    Raises:
        RuntimeError: If parsing fails.
    """
    pdfplumber = _ensure_pdfplumber()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")

    logger.info(f"Parsing minutes: {pdf_path.name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            return _parse_minutes_text(full_text)

    except Exception as e:
        raise RuntimeError(f"Failed to parse minutes: {e}")


def _parse_minutes_text(text: str) -> dict[str, Any]:
    """Parse minutes text to extract key sections.

    Args:
        text: Full text from minutes PDF.

    Returns:
        Dictionary with parsed sections.
    """
    result: dict[str, Any] = {
        "participants_views": "",
        "staff_review": "",
        "committee_action": "",
        "full_text": text,
    }

    # Extract "Participants' Views" section
    views_pattern = r"Participants['\"]?\s*Views.*?(?=Staff Review|Committee Policy|$)"
    views_match = re.search(views_pattern, text, re.IGNORECASE | re.DOTALL)
    if views_match:
        result["participants_views"] = views_match.group(0)[:2000]  # First 2000 chars

    # Extract "Staff Review" section
    staff_pattern = r"Staff Review.*?(?=Participants|Committee Policy|$)"
    staff_match = re.search(staff_pattern, text, re.IGNORECASE | re.DOTALL)
    if staff_match:
        result["staff_review"] = staff_match.group(0)[:2000]

    # Extract "Committee Policy Action" section
    action_pattern = r"Committee Policy Action.*?(?=Voting|$)"
    action_match = re.search(action_pattern, text, re.IGNORECASE | re.DOTALL)
    if action_match:
        result["committee_action"] = action_match.group(0)[:2000]

    return result


def get_projection_dates() -> list[str]:
    """Get list of meeting dates that have projection tables.

    Returns:
        List of dates in YYYYMMDD format with projection tables available.
    """
    from .data_loader import _get_module_path

    docs_path = _get_module_path() / "input" / "committee_meeting_docs"

    if not docs_path.exists():
        return []

    dates = []
    for pdf_file in docs_path.glob("fomcprojtabl*.pdf"):
        match = re.match(r"fomcprojtabl(\d{8})\.pdf", pdf_file.name)
        if match:
            dates.append(match.group(1))

    return sorted(dates, reverse=True)
