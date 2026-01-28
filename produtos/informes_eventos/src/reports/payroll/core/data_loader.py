"""
Bloomberg data loader for US Employment Situation (Payroll) data.

This module provides functions for fetching payroll-related data from
Bloomberg Terminal, including NFP, unemployment rate, and wage data.
"""

import datetime as dt
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Bloomberg tickers for payroll indicators
PAYROLL_TICKERS: dict[str, str] = {
    "NFP": "NFP TCH Index",
    "Unemployment": "USURTOT Index",
    "AHE_MoM": "AHE MOM% Index",
    "AHE_YoY": "AHE YOY% Index",
    "LFPR": "PRUSTOT Index",
}

# Bloomberg fields for release data
RELEASE_FIELDS: list[str] = [
    "PX_LAST",
    "PREV_CLOSE_VAL",
    "BN_SURVEY_MEDIAN",
    "ECO_RELEASE_DT",
    "OBSERVATION_PERIOD",
]


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


def fetch_payroll_data(
    start_date: str | dt.datetime = "2022-01-01",
    end_date: str | dt.datetime | None = None,
) -> pd.DataFrame:
    """Fetch historical payroll data from Bloomberg.

    Args:
        start_date: Start date for data retrieval (YYYY-MM-DD or datetime).
        end_date: End date for data retrieval. Defaults to today.

    Returns:
        DataFrame with columns: NFP, Unemployment, AHE_MoM, AHE_YoY, LFPR.
        Index is datetime (month-end).

    Raises:
        RuntimeError: If Bloomberg is not available or data fetch fails.
    """
    blp = _get_bloomberg_client()

    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, "%Y-%m-%d")
    if end_date is None:
        end_date = dt.datetime.now()
    elif isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, "%Y-%m-%d")

    tickers = list(PAYROLL_TICKERS.values())

    logger.info(f"Fetching payroll data from {start_date} to {end_date}")

    try:
        data = blp.bdh(
            tickers=tickers,
            flds="PX_LAST",
            start_date=start_date,
            end_date=end_date,
            Per="M",
        )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch payroll data: {e}")

    if data is None or data.empty:
        raise RuntimeError("No payroll data returned from Bloomberg")

    # Flatten multi-index columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Rename columns from tickers to friendly names
    ticker_to_name = {v: k for k, v in PAYROLL_TICKERS.items()}
    data = data.rename(columns=ticker_to_name)

    # Ensure we have all expected columns
    for col in PAYROLL_TICKERS.keys():
        if col not in data.columns:
            data[col] = None

    data = data[list(PAYROLL_TICKERS.keys())]

    # Forward-fill NA values (e.g., government shutdowns)
    data = data.ffill()

    # Ensure index is DatetimeIndex (Bloomberg may return date objects)
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    logger.info(f"Retrieved {len(data)} months of payroll data")
    return data


def get_latest_release() -> dict[str, dict[str, Any]]:
    """Get the latest payroll release data with survey expectations.

    Returns:
        Dictionary with indicator names as keys, each containing:
        - ticker: Bloomberg ticker
        - actual: Latest value
        - prior: Previous value
        - survey: Survey median expectation
        - release_date: Date of next/latest release
        - period: Observation period (e.g., "Dec")

    Raises:
        RuntimeError: If Bloomberg is not available or data fetch fails.
    """
    blp = _get_bloomberg_client()

    tickers = list(PAYROLL_TICKERS.values())

    logger.info("Fetching latest release data")

    try:
        data = blp.bdp(tickers=tickers, flds=RELEASE_FIELDS)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch release data: {e}")

    if data is None or data.empty:
        raise RuntimeError("No release data returned from Bloomberg")

    result: dict[str, dict[str, Any]] = {}

    for name, ticker in PAYROLL_TICKERS.items():
        if ticker in data.index:
            row = data.loc[ticker]
            result[name] = {
                "ticker": ticker,
                "actual": row.get("px_last"),
                "prior": row.get("prev_close_val"),
                "survey": row.get("bn_survey_median"),
                "release_date": row.get("eco_release_dt"),
                "period": row.get("observation_period"),
            }
        else:
            result[name] = {
                "ticker": ticker,
                "actual": None,
                "prior": None,
                "survey": None,
                "release_date": None,
                "period": None,
            }

    logger.info("Retrieved latest release data for all indicators")
    return result


def get_indicator_labels() -> dict[str, str]:
    """Get human-readable labels for payroll indicators.

    Returns:
        Dictionary mapping indicator codes to Portuguese labels.
    """
    return {
        "NFP": "Nonfarm Payrolls (mil)",
        "Unemployment": "Taxa de Desemprego (%)",
        "AHE_MoM": "Salarios MoM (%)",
        "AHE_YoY": "Salarios YoY (%)",
        "LFPR": "Participacao Forca de Trabalho (%)",
    }
