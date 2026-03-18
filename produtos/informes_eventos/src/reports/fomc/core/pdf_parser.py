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

# Variáveis econômicas esperadas na Table 1 do SEP
# (label no PDF sem espaços, nome canônico, tem Longer run?)
_TABLE1_VARIABLES = [
    ("ChangeinrealGDP", "Change in real GDP", True),
    ("Unemploymentrate", "Unemployment rate", True),
    ("PCEinflation", "PCE inflation", True),
    ("CorePCEinflation", "Core PCE inflation", False),  # nota 4: sem Longer run
    ("Federalfundsrate", "Federal funds rate", True),
]

# Regex para capturar valores numéricos e ranges "X.X–X.X"
_NUM = r"[\d.]+"
_RANGE = r"[\d.]+[–\-][\d.]+"
_TOKEN = rf"(?:{_RANGE}|{_NUM})"


def _ensure_pdfplumber() -> Any:
    """Ensure pdfplumber is available."""
    try:
        import pdfplumber

        return pdfplumber
    except ImportError:
        raise RuntimeError(
            "pdfplumber not available. Install with: uv add pdfplumber"
        )


def parse_projection_table(pdf_path: Path | str) -> dict[str, Any]:
    """Parse FOMC projection table PDF to extract economic projections.

    Extracts median, central tendency, range projections and prior projections
    from the Summary of Economic Projections PDF (Table 1).

    Args:
        pdf_path: Path to fomcprojtabl*.pdf file.

    Returns:
        Dictionary with keys:
        - 'medians': DataFrame with current median projections (backward-compatible)
        - 'prior_medians': DataFrame with prior projection medians
        - 'prior_label': str like "December projection"
        - 'central_tendency': DataFrame with current CT ranges
        - 'prior_ct': DataFrame with prior CT ranges
        - 'range': DataFrame with current full ranges
        - 'prior_range': DataFrame with prior full ranges
        - 'year_columns': list of year strings e.g. ["2026", "2027", "2028", "Longer run"]
        - 'dot_distribution': DataFrame with fed funds rate distribution
    """
    pdfplumber = _ensure_pdfplumber()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")

    logger.info(f"Parsing projection table: {pdf_path.name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            table1_data = _extract_full_table1(pdf)
            dot_dist_df = _extract_fed_funds_distribution(pdf)
            table1_data["dot_distribution"] = dot_dist_df
            return table1_data

    except Exception as e:
        raise RuntimeError(f"Failed to parse projection table: {e}")


def _extract_full_table1(pdf: Any) -> dict[str, Any]:
    """Extract complete Table 1 from page 2: medians, CT, ranges, current + prior.

    Uses text-based parsing which is more reliable than extract_tables() for
    this PDF layout.
    """
    if len(pdf.pages) < 2:
        return _empty_table1_result()

    page = pdf.pages[1]
    text = page.extract_text() or ""

    # 1. Detect year columns from header row
    year_columns = _detect_year_columns(text)
    if not year_columns:
        logger.warning("Could not detect year columns from Table 1 header")
        return _empty_table1_result()

    # Separate numeric years and "Longer run"
    numeric_years = [y for y in year_columns if y != "Longer run"]
    has_longer_run = "Longer run" in year_columns
    n_years = len(numeric_years)

    # 2. Detect prior label (e.g. "December projection", "September projection")
    prior_label = _detect_prior_label(text)

    # 3. Parse each variable block (current line + prior line)
    medians_records = []
    prior_medians_records = []
    ct_records = []
    prior_ct_records = []
    range_records = []
    prior_range_records = []

    for pdf_label, var_name, has_lr in _TABLE1_VARIABLES:
        block = _extract_variable_block(
            text, pdf_label, var_name, n_years, has_lr and has_longer_run,
        )
        if block is None:
            continue

        medians_records.append(block["current_medians"])
        ct_records.append(block["current_ct"])
        range_records.append(block["current_range"])

        if block["prior_medians"] is not None:
            prior_medians_records.append(block["prior_medians"])
        if block["prior_ct"] is not None:
            prior_ct_records.append(block["prior_ct"])
        if block["prior_range"] is not None:
            prior_range_records.append(block["prior_range"])

    # Build DataFrames
    df_cols = numeric_years + (["Longer run"] if has_longer_run else [])

    result = {
        "medians": _records_to_df(medians_records, df_cols),
        "prior_medians": _records_to_df(prior_medians_records, df_cols) if prior_medians_records else pd.DataFrame(),
        "prior_label": prior_label,
        "central_tendency": _records_to_df(ct_records, df_cols),
        "prior_ct": _records_to_df(prior_ct_records, df_cols) if prior_ct_records else pd.DataFrame(),
        "range": _records_to_df(range_records, df_cols),
        "prior_range": _records_to_df(prior_range_records, df_cols) if prior_range_records else pd.DataFrame(),
        "year_columns": df_cols,
    }

    logger.info(
        f"Table 1 parsed: {len(medians_records)} variables, "
        f"years={df_cols}, prior_label='{prior_label}'"
    )
    return result


def _detect_year_columns(text: str) -> list[str]:
    """Detect year columns from the header row.

    Looks for a line with consecutive 4-digit years (e.g. "2026 2027 2028 Longer").
    Returns list like ["2026", "2027", "2028", "Longer run"].
    """
    # Find header line with years — appears in the Median section header
    # Pattern: years repeated 3 times (Median, CT, Range) on the same line
    header_match = re.search(
        r"(\d{4})\s+(\d{4})\s+(\d{4})(?:\s+(\d{4}))?\s+Longer",
        text,
    )
    if header_match:
        years = [g for g in header_match.groups() if g is not None]
        return years + ["Longer run"]

    # Fallback: just find consecutive years
    header_match = re.search(
        r"(\d{4})\s+(\d{4})\s+(\d{4})(?:\s+(\d{4}))?",
        text,
    )
    if header_match:
        years = [g for g in header_match.groups() if g is not None]
        # Check if "Longer" appears nearby
        if "Longer" in text[:500]:
            years.append("Longer run")
        return years

    return []


def _detect_prior_label(text: str) -> str:
    """Detect the prior meeting label (e.g. 'December projection')."""
    match = re.search(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s*projection",
        text,
        re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)} projection"
    return "Prior projection"


def _extract_variable_block(
    text: str,
    pdf_label: str,
    var_name: str,
    n_years: int,
    has_longer_run: bool,
) -> dict[str, Any] | None:
    """Extract current and prior data for a single variable across all sections.

    For each variable, the PDF has two consecutive lines:
    - Current: "ChangeinrealGDP 2.4 2.3 2.1 2.0 2.2–2.5 2.0–2.4 ..."
    - Prior:   "Decemberprojection 2.3 2.0 1.9 1.8 2.1–2.5 1.9–2.3 ..."

    Each line has: n_years medians + (LR median if applicable) +
                   n_years CT + (LR CT) + n_years Range + (LR Range)
    """
    # Special handling for Federal funds rate — preceded by "Memo:" block
    if pdf_label == "Federalfundsrate":
        # Find the line starting with "Federalfundsrate" after "Memo"
        pattern = re.compile(
            rf"Federalfundsrate\s+({_TOKEN}(?:\s+{_TOKEN})*)",
            re.IGNORECASE,
        )
    else:
        # Match variable label followed by optional superscript digit
        pattern = re.compile(
            rf"{pdf_label}\d*\s+({_TOKEN}(?:\s+{_TOKEN})*)",
            re.IGNORECASE,
        )

    match = pattern.search(text)
    if not match:
        logger.warning(f"Could not find variable: {var_name}")
        return None

    current_tokens = re.findall(_TOKEN, match.group(1))

    # Find prior line — immediately after current
    prior_start = match.end()
    # Prior label pattern (e.g. "Decemberprojection", "Septemberprojection")
    prior_pattern = re.compile(
        rf"([A-Z][a-z]+projection)\s+({_TOKEN}(?:\s+{_TOKEN})*)",
        re.IGNORECASE,
    )
    prior_match = prior_pattern.search(text, prior_start, prior_start + 500)

    prior_tokens = None
    if prior_match:
        prior_tokens = re.findall(_TOKEN, prior_match.group(2))

    # Parse tokens into Median / CT / Range sections
    current_parsed = _parse_variable_tokens(current_tokens, n_years, has_longer_run)
    prior_parsed = _parse_variable_tokens(prior_tokens, n_years, has_longer_run) if prior_tokens else None

    result = {
        "current_medians": {"Variable": var_name, **current_parsed["medians"]},
        "current_ct": {"Variable": var_name, **current_parsed["ct"]},
        "current_range": {"Variable": var_name, **current_parsed["range"]},
        "prior_medians": None,
        "prior_ct": None,
        "prior_range": None,
    }

    if prior_parsed:
        result["prior_medians"] = {"Variable": var_name, **prior_parsed["medians"]}
        result["prior_ct"] = {"Variable": var_name, **prior_parsed["ct"]}
        result["prior_range"] = {"Variable": var_name, **prior_parsed["range"]}

    return result


def _parse_variable_tokens(
    tokens: list[str] | None,
    n_years: int,
    has_longer_run: bool,
) -> dict[str, dict]:
    """Parse a list of tokens into Median, CT, Range sections.

    Token layout per line:
    [median_y1, ..., median_yn, (median_LR,)
     ct_y1, ..., ct_yn, (ct_LR,)
     range_y1, ..., range_yn, (range_LR)]

    Medians are plain numbers; CT and Range are "X.X–X.X" or plain numbers.
    """
    empty = {"medians": {}, "ct": {}, "range": {}}
    if not tokens:
        return empty

    # Classify tokens as numeric (median) or range
    # Medians come first, then CT, then Range
    # We know n_years + (1 if LR) per section
    section_size = n_years + (1 if has_longer_run else 0)

    # For Core PCE, there's no Longer run for medians but layout differs:
    # Core PCE has no LR for any section
    # The total expected tokens = section_size * 3 (median + ct + range)

    # However, some cells might be a single value instead of range (e.g., "2.0" in CT)
    # We need to split based on whether token contains dash

    # Strategy: first section_size tokens are medians (always plain numbers)
    # Next section_size are CT (may be ranges or single values)
    # Remaining are Range

    if len(tokens) < section_size:
        # Not enough tokens even for medians
        medians = _assign_to_years(tokens, n_years, has_longer_run)
        return {"medians": medians, "ct": {}, "range": {}}

    median_tokens = tokens[:section_size]
    ct_tokens = tokens[section_size:section_size * 2] if len(tokens) >= section_size * 2 else []
    range_tokens = tokens[section_size * 2:section_size * 3] if len(tokens) >= section_size * 3 else []

    medians = _assign_to_years(median_tokens, n_years, has_longer_run)
    ct = _assign_to_years(ct_tokens, n_years, has_longer_run)
    ranges = _assign_to_years(range_tokens, n_years, has_longer_run)

    return {"medians": medians, "ct": ct, "range": ranges}


def _assign_to_years(
    tokens: list[str],
    n_years: int,
    has_longer_run: bool,
) -> dict:
    """Assign tokens to year keys.

    Returns dict with year indices (0, 1, ...) and optionally "lr" for Longer run.
    Keys will be replaced by actual year labels when building DataFrame.
    """
    result = {}
    for i in range(min(n_years, len(tokens))):
        result[i] = _parse_token(tokens[i])

    if has_longer_run and len(tokens) > n_years:
        result["lr"] = _parse_token(tokens[n_years])

    return result


def _parse_token(token: str) -> str | float:
    """Parse a single token: plain number → float, range → string."""
    # Check if it's a range (contains en-dash or hyphen between numbers)
    if re.match(r"[\d.]+[–\-][\d.]+", token):
        # Normalize en-dash to regular dash for display
        return token.replace("–", "–")  # keep en-dash for consistency
    try:
        return float(token)
    except ValueError:
        return token


def _records_to_df(records: list[dict], year_columns: list[str]) -> pd.DataFrame:
    """Convert list of records (with positional year keys) to DataFrame.

    Each record has: Variable, 0, 1, 2, ..., "lr" → remap to year names.
    """
    if not records:
        return pd.DataFrame()

    numeric_years = [y for y in year_columns if y != "Longer run"]
    has_lr = "Longer run" in year_columns

    rows = []
    for record in records:
        row = {"Variable": record["Variable"]}
        for i, year in enumerate(numeric_years):
            row[year] = record.get(i)
        if has_lr:
            row["Longer run"] = record.get("lr")
        rows.append(row)

    return pd.DataFrame(rows)


def _empty_table1_result() -> dict[str, Any]:
    """Return empty result dict for Table 1."""
    return {
        "medians": pd.DataFrame(),
        "prior_medians": pd.DataFrame(),
        "prior_label": "Prior projection",
        "central_tendency": pd.DataFrame(),
        "prior_ct": pd.DataFrame(),
        "range": pd.DataFrame(),
        "prior_range": pd.DataFrame(),
        "year_columns": [],
    }


def _extract_fed_funds_distribution(pdf: Any) -> pd.DataFrame:
    """Extract federal funds rate distribution from Figure 3.E."""
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

    rate_ranges = []
    pattern = r"([\d.]+)[−\-–]([\d.]+)"

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
    """Parse FOMC monetary policy statement PDF."""
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
    """Parse statement text to extract key information."""
    result: dict[str, Any] = {
        "target_rate_low": None,
        "target_rate_high": None,
        "decision": None,
        "unanimous": None,
        "dissenters": [],
        "key_phrases": [],
    }

    rate_pattern = r"target range.*?(\d+(?:-\d+/\d+)?)\s*to\s*(\d+(?:-\d+/\d+)?)\s*percent"
    rate_match = re.search(rate_pattern, text, re.IGNORECASE)

    if rate_match:
        result["target_rate_low"] = _parse_rate_fraction(rate_match.group(1))
        result["target_rate_high"] = _parse_rate_fraction(rate_match.group(2))

    if "decided to maintain" in text.lower() or "decided to hold" in text.lower():
        result["decision"] = "hold"
    elif "decided to lower" in text.lower() or "decided to reduce" in text.lower():
        result["decision"] = "cut"
    elif "decided to raise" in text.lower() or "decided to increase" in text.lower():
        result["decision"] = "hike"

    result["unanimous"] = "voting against" not in text.lower()

    dissent_pattern = r"Voting against.*?:\s*([^.]+)"
    dissent_match = re.search(dissent_pattern, text, re.IGNORECASE)
    if dissent_match:
        dissenters = dissent_match.group(1).strip()
        result["dissenters"] = [d.strip() for d in dissenters.split(",")]

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
    """Parse rate string that may contain fractions."""
    if "-" in rate_str and "/" in rate_str:
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
    """Parse FOMC meeting minutes PDF."""
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
    """Parse minutes text to extract key sections."""
    result: dict[str, Any] = {
        "participants_views": "",
        "staff_review": "",
        "committee_action": "",
        "full_text": text,
    }

    views_pattern = r"Participants['\"]?\s*Views.*?(?=Staff Review|Committee Policy|$)"
    views_match = re.search(views_pattern, text, re.IGNORECASE | re.DOTALL)
    if views_match:
        result["participants_views"] = views_match.group(0)[:2000]

    staff_pattern = r"Staff Review.*?(?=Participants|Committee Policy|$)"
    staff_match = re.search(staff_pattern, text, re.IGNORECASE | re.DOTALL)
    if staff_match:
        result["staff_review"] = staff_match.group(0)[:2000]

    action_pattern = r"Committee Policy Action.*?(?=Voting|$)"
    action_match = re.search(action_pattern, text, re.IGNORECASE | re.DOTALL)
    if action_match:
        result["committee_action"] = action_match.group(0)[:2000]

    return result


def get_projection_dates() -> list[str]:
    """Get list of meeting dates that have projection tables."""
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
