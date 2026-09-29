"""
Data loader for US Employment Situation (Payroll) data.

This module provides functions for fetching payroll-related data from
Bloomberg Terminal (primary) or FRED API (fallback), including NFP,
unemployment rate, wage data, U6, and JOLTS.
"""

import datetime as dt
import logging
from typing import Any

import pandas as pd

from reports import _paths
from reports._env import get_secret, misnamed_env_file

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

# FRED series for payroll fallback
FRED_SERIES: dict[str, str] = {
    "NFP_LEVEL": "PAYEMS",
    "Unemployment": "UNRATE",
    "AHE_LEVEL": "CES0500000003",
    "LFPR": "CIVPART",
}

# FRED series for extended indicators
FRED_EXTENDED_SERIES: dict[str, str] = {
    "U6": "U6RATE",
    "JOLTS": "JTSJOL",
}


def _get_bloomberg_client() -> Any:
    """Get Bloomberg client, raising error if not available."""
    try:
        from xbbg import blp

        return blp
    except ImportError:
        raise RuntimeError("Bloomberg (xbbg) not available. Install with: uv add xbbg")


def _get_fred_client() -> Any:
    """Get FRED API client."""
    from fredapi import Fred

    # Resolvida só aqui, na hora do uso: quem não usa o fallback do FRED não
    # precisa da chave.
    api_key = get_secret("FRED_API_KEY")
    if api_key is None:
        wrong = misnamed_env_file()
        if wrong is not None:
            raise ValueError(
                f"FRED API key not found: the file is named {wrong.name}, not "
                f"{_paths.ENV_FILE.name}. Rename {wrong} to {_paths.ENV_FILE} "
                "(Windows Explorer hides the .txt extension)"
            )
        raise ValueError(
            f"FRED API key not found. Create {_paths.ENV_FILE} from "
            "etc/env.exemplo with a line FRED_API_KEY=<your key> (free at "
            "https://fred.stlouisfed.org/docs/api/api_key.html), or set "
            "FRED_API_KEY in the environment"
        )
    return Fred(api_key=api_key)


def _fetch_from_bloomberg(
    start_date: dt.datetime,
    end_date: dt.datetime,
) -> pd.DataFrame:
    """Fetch payroll data from Bloomberg."""
    blp = _get_bloomberg_client()
    tickers = list(PAYROLL_TICKERS.values())

    from reports._bloomberg import run_async as _run_async

    data = _run_async(
        blp.abdh(
            tickers=tickers,
            flds="PX_LAST",
            start_date=start_date,
            end_date=end_date,
            periodicitySelection="MONTHLY",
            backend="pandas",
        )
    )

    if data is None or data.empty:
        raise RuntimeError("No payroll data returned from Bloomberg")

    # xbbg 1.0: LONG format [ticker, date, field, value] (tudo string)
    ticker_to_name = {v: k for k, v in PAYROLL_TICKERS.items()}
    if "ticker" in data.columns and "value" in data.columns:
        data["date"] = pd.to_datetime(data["date"])
        data["value"] = pd.to_numeric(data["value"], errors="coerce")
        data = data.pivot(index="date", columns="ticker", values="value")
        data.columns = [ticker_to_name.get(c, c) for c in data.columns]
    elif isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        data = data.rename(columns=ticker_to_name)
    else:
        data = data.rename(columns=ticker_to_name)

    for col in PAYROLL_TICKERS.keys():
        if col not in data.columns:
            data[col] = None

    data = data[list(PAYROLL_TICKERS.keys())]
    data = data.ffill()

    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    return data


def _fetch_from_fred(
    start_date: dt.datetime,
    end_date: dt.datetime,
) -> pd.DataFrame:
    """Fetch payroll data from FRED API as fallback."""
    fred = _get_fred_client()

    data_dict: dict[str, pd.Series] = {}
    for name, series_id in FRED_SERIES.items():
        try:
            data_dict[name] = fred.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch {series_id} from FRED: {e}")

    if not data_dict:
        raise RuntimeError("No data returned from FRED")

    df = pd.DataFrame(data_dict)
    df.index = pd.to_datetime(df.index)

    # Resample to month-end
    df = df.resample("ME").last()

    # Compute NFP MoM change from level (PAYEMS is in thousands)
    if "NFP_LEVEL" in df.columns:
        df["NFP"] = df["NFP_LEVEL"].diff()
        df = df.drop(columns=["NFP_LEVEL"])

    # Compute AHE MoM and YoY from level
    if "AHE_LEVEL" in df.columns:
        df["AHE_MoM"] = df["AHE_LEVEL"].pct_change() * 100
        df["AHE_YoY"] = df["AHE_LEVEL"].pct_change(periods=12) * 100
        df = df.drop(columns=["AHE_LEVEL"])

    # Reorder columns to match Bloomberg output
    expected_cols = ["NFP", "Unemployment", "AHE_MoM", "AHE_YoY", "LFPR"]
    available_cols = [c for c in expected_cols if c in df.columns]
    df = df[available_cols]

    df = df.ffill()
    return df


def fetch_payroll_data(
    start_date: str | dt.datetime = "2022-01-01",
    end_date: str | dt.datetime | None = None,
) -> pd.DataFrame:
    """Fetch historical payroll data (Bloomberg primary, FRED fallback).

    Args:
        start_date: Start date for data retrieval (YYYY-MM-DD or datetime).
        end_date: End date for data retrieval. Defaults to today.

    Returns:
        DataFrame with columns: NFP, Unemployment, AHE_MoM, AHE_YoY, LFPR.
        Index is datetime (month-end).
    """
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, "%Y-%m-%d")
    if end_date is None:
        end_date = dt.datetime.now()
    elif isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, "%Y-%m-%d")

    logger.info(f"Fetching payroll data from {start_date} to {end_date}")

    # Try Bloomberg first
    try:
        data = _fetch_from_bloomberg(start_date, end_date)
        logger.info(f"Bloomberg: {len(data)} months loaded")
        return data
    except Exception as e:
        logger.warning(f"Bloomberg unavailable: {e}. Trying FRED fallback...")

    # FRED fallback
    try:
        data = _fetch_from_fred(start_date, end_date)
        logger.info(f"FRED fallback: {len(data)} months loaded")
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to fetch payroll data from any source: {e}")


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

    from reports._bloomberg import run_async as _run_async

    try:
        data = _run_async(blp.abdp(tickers=tickers, flds=RELEASE_FIELDS, backend="pandas"))
    except Exception as e:
        raise RuntimeError(f"Failed to fetch release data: {e}")

    if data is None or data.empty:
        raise RuntimeError("No release data returned from Bloomberg")

    # xbbg 1.0: LONG format [ticker, field, value] → pivot to ticker x field
    if "ticker" in data.columns and "value" in data.columns:
        data = data.pivot(index="ticker", columns="field", values="value")
        data.columns = [c.lower() for c in data.columns]

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


def fetch_extended_data(
    start_date: str | dt.datetime = "1990-01-01",
    end_date: str | dt.datetime | None = None,
) -> pd.DataFrame:
    """Fetch extended labor market data (U6, JOLTS) from FRED.

    Args:
        start_date: Start date for data retrieval.
        end_date: End date for data retrieval. Defaults to today.

    Returns:
        DataFrame with columns: U6, JOLTS.
        Index is datetime (month-end).
    """
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, "%Y-%m-%d")
    if end_date is None:
        end_date = dt.datetime.now()
    elif isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, "%Y-%m-%d")

    fred = _get_fred_client()

    data_dict: dict[str, pd.Series] = {}
    for name, series_id in FRED_EXTENDED_SERIES.items():
        try:
            data_dict[name] = fred.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch {series_id} from FRED: {e}")

    if not data_dict:
        raise RuntimeError("No extended data returned from FRED")

    df = pd.DataFrame(data_dict)
    df.index = pd.to_datetime(df.index)
    df = df.resample("ME").last()
    df = df.ffill()

    logger.info(f"Extended data: {len(df)} months loaded")
    return df


def get_indicator_labels() -> dict[str, str]:
    """Get human-readable labels for payroll indicators."""
    return {
        "NFP": "Nonfarm Payrolls (mil)",
        "Unemployment": "Taxa de Desemprego (%)",
        "AHE_MoM": "Salarios MoM (%)",
        "AHE_YoY": "Salarios YoY (%)",
        "LFPR": "Participacao Forca de Trabalho (%)",
        "U6": "Desemprego Ampliado U6 (%)",
        "JOLTS": "JOLTS Job Openings (mil)",
    }
