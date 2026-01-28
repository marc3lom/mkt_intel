"""
BLS Employment Situation Table B scraper.

This module provides functions for fetching and parsing the industry
breakdown data from the Bureau of Labor Statistics website.
"""

import logging
import re
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BLS_TABLE_B_URL = "https://www.bls.gov/news.release/empsit.b.htm"

# Headers to mimic browser request (BLS blocks requests without User-Agent)
BLS_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_industry_breakdown() -> pd.DataFrame:
    """Fetch industry breakdown data from BLS Table B.

    Returns:
        DataFrame with columns:
        - industry: Industry name
        - level: Hierarchy level (0=total, 1=sector, 2=subsector, etc.)
        - current_month: Latest month change (thousands)
        - prior_month: Previous month change (thousands)
        - prior_year: Year-ago change (thousands)

    Raises:
        RuntimeError: If data fetch or parsing fails.
    """
    logger.info(f"Fetching BLS data from {BLS_TABLE_B_URL}")

    try:
        response = requests.get(
            BLS_TABLE_B_URL, headers=BLS_REQUEST_HEADERS, timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch BLS data: {e}")

    html = response.text
    return parse_bls_table(html)


def parse_bls_table(html: str) -> pd.DataFrame:
    """Parse BLS Employment Situation Table B HTML.

    Args:
        html: Raw HTML content from BLS website.

    Returns:
        DataFrame with industry employment changes.

    Raises:
        RuntimeError: If parsing fails.
    """
    try:
        tables = pd.read_html(StringIO(html))
    except Exception as e:
        raise RuntimeError(f"Failed to parse BLS HTML: {e}")

    if not tables:
        raise RuntimeError("No tables found in BLS HTML")

    # Find the main employment table (usually the first large one)
    main_table = None
    for table in tables:
        if len(table) > 20 and len(table.columns) >= 4:
            # Look for "Total nonfarm" in first column
            first_col = table.iloc[:, 0].astype(str)
            if first_col.str.contains("nonfarm", case=False).any():
                main_table = table
                break

    if main_table is None:
        raise RuntimeError("Could not find employment table in BLS data")

    return _process_employment_table(main_table)


def _process_employment_table(table: pd.DataFrame) -> pd.DataFrame:
    """Process raw BLS employment table into clean format.

    Args:
        table: Raw table from BLS HTML.

    Returns:
        Cleaned DataFrame with industry hierarchy.
    """
    # Get column names from first few rows
    table = table.copy()

    # Find header row (contains month names)
    header_idx = 0
    for i in range(min(5, len(table))):
        row_str = " ".join(table.iloc[i].astype(str))
        if re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", row_str
        ):
            header_idx = i
            break

    # Set header and skip header rows
    if header_idx > 0:
        table.columns = table.iloc[header_idx]
        table = table.iloc[header_idx + 1 :].reset_index(drop=True)

    # First column is industry name
    table.columns = ["industry"] + [
        f"col_{i}" for i in range(1, len(table.columns))
    ]

    # Clean industry names and determine hierarchy level
    records = []
    for _, row in table.iterrows():
        industry = str(row["industry"]).strip()

        # Skip empty rows
        if not industry or industry == "nan":
            continue

        # Determine hierarchy level based on indentation/formatting
        level = _determine_hierarchy_level(industry)

        # Clean industry name
        industry_clean = re.sub(r"^\s+", "", industry)
        industry_clean = re.sub(r"\(\d+\)$", "", industry_clean).strip()

        # Get numeric values from remaining columns
        values = []
        for col in table.columns[1:4]:
            val = row.get(col)
            if pd.notna(val):
                try:
                    values.append(float(str(val).replace(",", "")))
                except ValueError:
                    values.append(None)
            else:
                values.append(None)

        # Pad values if needed
        while len(values) < 3:
            values.append(None)

        records.append(
            {
                "industry": industry_clean,
                "level": level,
                "prior_year": values[0],
                "prior_month": values[1],
                "current_month": values[2],
            }
        )

    df = pd.DataFrame(records)

    # Filter out non-industry rows
    df = df[df["industry"].str.len() > 0]
    df = df[~df["industry"].str.contains("Change|Percent|p =|Note", case=False)]

    return df.reset_index(drop=True)


def _determine_hierarchy_level(industry: str) -> int:
    """Determine hierarchy level based on industry name formatting.

    Args:
        industry: Raw industry name string.

    Returns:
        Hierarchy level (0=total, 1=major sector, 2=subsector, etc.)
    """
    # Count leading spaces for indentation
    leading_spaces = len(industry) - len(industry.lstrip())

    # Map spaces to levels
    if leading_spaces == 0:
        if "total" in industry.lower():
            return 0
        return 1
    elif leading_spaces <= 4:
        return 2
    elif leading_spaces <= 8:
        return 3
    else:
        return 4


def get_industry_hierarchy() -> dict[str, list[str]]:
    """Get the standard BLS industry hierarchy structure.

    Returns:
        Dictionary mapping major sectors to their subsectors.
    """
    return {
        "Total nonfarm": [
            "Total private",
            "Government",
        ],
        "Total private": [
            "Goods-producing",
            "Private service-providing",
        ],
        "Goods-producing": [
            "Mining and logging",
            "Construction",
            "Manufacturing",
        ],
        "Manufacturing": [
            "Durable goods",
            "Nondurable goods",
        ],
        "Private service-providing": [
            "Wholesale trade",
            "Retail trade",
            "Transportation and warehousing",
            "Utilities",
            "Information",
            "Financial activities",
            "Professional and business services",
            "Private education and health services",
            "Leisure and hospitality",
            "Other services",
        ],
    }
