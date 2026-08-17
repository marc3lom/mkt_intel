"""Bloomberg data fetching for monitor and calendar notebooks."""

import logging
from datetime import datetime

import pandas as pd

from comentario_matinal.render.estilo import BQL_COUNTRIES, BQL_DATE_RANGE


logger = logging.getLogger("comentario_matinal")


# ---------------------------------------------------------------------------
# xbbg helpers (monitor_matinal)
# ---------------------------------------------------------------------------

MARKET_SESSIONS_UTC: dict[str, tuple[int, int, int, int]] = {
    "ES1 Index": (0, 0, 23, 59),
    "VG1 Index": (1, 0, 21, 0),
    "NK1 Index": (0, 0, 23, 59),
    "IFB1 Index": (1, 30, 7, 0),
    "USGG10YR Index": (0, 0, 21, 0),
    "GDBR10 Index": (7, 0, 17, 30),
    "GTJPY10Y Govt": (0, 0, 9, 0),
    "GCNY10YR Index": (1, 30, 9, 30),
    "DXY Curncy": (0, 0, 23, 59),
    "EUR Curncy": (0, 0, 23, 59),
    "JPY Curncy": (0, 0, 23, 59),
    "CNH Curncy": (0, 0, 23, 59),
    "XBTUSD BGN Curncy": (0, 0, 23, 59),
    "XAU Curncy": (0, 0, 23, 59),
    "CO1 Comdty": (1, 0, 21, 0),
    "VIX Index": (0, 0, 23, 59),
}

BDIB_EVENT_TYPE: dict[str, str] = {
    "USGG10YR Index": "BID",
    "GDBR10 Index": "BID",
    "GCNY10YR Index": "BID",
}

# Tickers where the display should show yield (not price).
# Maps ticker → Bloomberg yield field for bdp/bdh.
YIELD_DISPLAY_TICKERS: dict[str, str] = {
    "GTJPY10Y Govt": "YLD_YTM_BID",
}


async def get_reference_data(tickers: list[str]) -> pd.DataFrame:
    """Fetch reference data (price, 1-day change) from Bloomberg via xbbg."""
    from xbbg import blp

    fields = ["PX_LAST", "CHG_NET_1D", "CHG_PCT_1D"]
    try:
        raw = await blp.abdp(
            tickers=tickers, flds=fields,
            backend="pandas",
        )
    except Exception as e:
        logger.error("Failed to fetch reference data: %s", e)
        return pd.DataFrame()

    if raw.empty:
        return raw

    # xbbg 1.0 returns LONG format (ticker, field, value) with string values.
    # Pivot to ticker-indexed rows with lowercase field columns.
    df = raw.pivot(index="ticker", columns="field", values="value")
    df = df.apply(pd.to_numeric, errors="coerce")
    df.columns = df.columns.str.lower()
    df.index.name = None

    # For yield tickers, fetch yield via bdh and store as display overrides.
    # px_last / chg_net_1d stay price-based (used by get_intraday_data for
    # prev_close); the *_display columns are used by the monitor panel.
    for ticker, yld_field in YIELD_DISPLAY_TICKERS.items():
        if ticker not in df.index:
            continue
        try:
            from datetime import timedelta

            end = datetime.now().date()
            start = end - timedelta(days=7)
            hist = await blp.abdh(
                tickers=ticker, flds=[yld_field], start_date=start, end_date=end,
                backend="pandas",
            )
            if hist is None or hist.empty or len(hist) < 2:
                continue
            # abdh returns LONG format: ticker, date, field, value
            yld_values = hist["value"].astype(float)
            cur_yld = yld_values.iloc[-1]
            prev_yld = yld_values.iloc[-2]
            df.loc[ticker, "px_last_display"] = cur_yld
            df.loc[ticker, "chg_net_display"] = cur_yld - prev_yld
        except Exception as e:
            logger.warning("Yield override failed for %s: %s", ticker, e)

    return df


async def get_intraday_data(
    ticker: str,
    ref_data: pd.DataFrame,
) -> pd.Series:
    """Fetch previous close + today's intraday bars for sparkline.

    The previous close becomes the first point so the sparkline shows
    performance relative to yesterday's close.

    Uses explicit UTC time windows and event types (BID for rates, TRADE
    for everything else) to bypass xbbg's session resolution, which fails
    for some instruments (e.g. JGB, Nikkei).
    """
    from xbbg import blp

    today = datetime.now().date()
    typ = BDIB_EVENT_TYPE.get(ticker, "TRADE")
    start_h, start_m, end_h, end_m = MARKET_SESSIONS_UTC.get(ticker, (0, 0, 23, 59))
    start_dt = f"{today} {start_h:02d}:{start_m:02d}:00"
    end_dt = f"{today} {end_h:02d}:{end_m:02d}:00"

    try:
        try:
            bars = await blp.abdib(
                ticker=ticker,
                start_datetime=start_dt,
                end_datetime=end_dt,
                typ=typ,
                backend="pandas",
            )
        except AttributeError:
            bars = await blp.abdib(
                ticker=ticker, dt=today, session="allday", typ=typ,
                backend="pandas",
            )

        if bars is None or bars.empty:
            return pd.Series()

        logger.info(
            "  [debug] bdib %s: %d rows, cols=%s", ticker, len(bars), list(bars.columns),
        )

        # xbbg 0.12.1 returns flat format with columns:
        # [ticker, time, open, high, low, close, volume, num_trds]
        if "time" in bars.columns and "close" in bars.columns:
            if "ticker" in bars.columns:
                bars = bars[bars["ticker"] == ticker]
            intraday = bars.set_index("time")["close"]
        else:
            # Fallback for older xbbg MultiIndex column format
            try:
                intraday = bars[ticker]["close"]
            except KeyError:
                intraday = bars.xs("close", axis=1, level=1).iloc[:, 0]

        if intraday.empty:
            return pd.Series()

        logger.info(
            "  intraday %s: %d pts, first=%.4f, last=%.4f",
            ticker, len(intraday), intraday.iloc[0], intraday.iloc[-1],
        )

        # Prepend previous close from ref_data
        if ticker in ref_data.index:
            row = ref_data.loc[ticker]

            # For yield tickers, bdib already returns yield values;
            # compute prev_close from the yield override columns.
            if (
                ticker in YIELD_DISPLAY_TICKERS
                and "px_last_display" in row.index
                and pd.notna(row.get("px_last_display"))
                and pd.notna(row.get("chg_net_display"))
            ):
                prev_close = row["px_last_display"] - row["chg_net_display"]
            else:
                px_last = row["px_last"]
                chg_net = row["chg_net_1d"]
                prev_close = px_last - chg_net

            if pd.notna(prev_close):
                prev_close_time = intraday.index[0] - pd.Timedelta(minutes=1)
                prev_close_series = pd.Series([prev_close], index=[prev_close_time])
                return pd.concat([prev_close_series, intraday])

        return intraday

    except Exception as e:
        logger.warning("bdib failed for %s: %s", ticker, e)

    return pd.Series()


# ---------------------------------------------------------------------------
# BQL helpers (calendario_economico)
# ---------------------------------------------------------------------------


def _bql_to_pandas(result) -> "pd.DataFrame | None":
    """Convert a polars-bloomberg BqlResult to a pandas DataFrame."""
    if result is None:
        return None
    try:
        df_pl = result.combine()
    except Exception:
        try:
            dfs = result.dataframes
            df_pl = dfs[0] if dfs else None
        except Exception:
            return None
    if df_pl is None or len(df_pl) == 0:
        return None
    return df_pl.to_pandas()


def _map_bql_columns(df: pd.DataFrame, column_mapping: dict[str, str]) -> pd.DataFrame:
    """Rename BQL columns using fuzzy matching on uppercase names."""
    rename_dict = {}
    for old, new in column_mapping.items():
        matching_cols = [c for c in df.columns if old in c.upper()]
        if matching_cols:
            rename_dict[matching_cols[0]] = new
    return df.rename(columns=rename_dict)


def fetch_eco_calendar() -> pd.DataFrame:
    """Fetch economic calendar via BQL.

    Uses polars-bloomberg.BQuery because it tags the BQL request with
    ``clientContext.appName=EXCEL``, which Bloomberg Anywhere requires for
    BQL access. xbbg's BQL endpoint omits that tag and is rejected with
    "User not authorized to use BQL" on Anywhere licenses.

    Returns DataFrame with columns: PAÍS, DATA, HORÁRIO, EVENTO, PERÍODO,
    ESTIMATIVA, ATUAL, ANTERIOR, REVISADO
    """
    from polars_bloomberg import BQuery

    countries = ",".join(f"'{c}'" for c in BQL_COUNTRIES)
    query = f"""
        get(dropna(calendar(relevancy=VERY_HIGH), remove_id=true))
        for ([{countries}])
        with(dates={BQL_DATE_RANGE})
    """

    try:
        with BQuery() as bq:
            result = bq.bql(query)

        df = _bql_to_pandas(result)
        if df is None:
            return pd.DataFrame()

        column_mapping = {
            "COUNTRY_NAME": "PAÍS",
            "RELEASE_DATE": "DATA",
            "RELEASE_TIME": "HORÁRIO",
            "EVENT_NAME": "EVENTO",
            "PERIOD": "PERÍODO",
            "SURVEY_MEDIAN": "ESTIMATIVA",
            "ACTUAL": "ATUAL",
            "PRIOR": "ANTERIOR",
            "REVISION": "REVISADO",
        }

        df = _map_bql_columns(df, column_mapping)

        cols_needed = [
            "PAÍS", "DATA", "HORÁRIO", "EVENTO", "PERÍODO",
            "ESTIMATIVA", "ATUAL", "ANTERIOR", "REVISADO",
        ]
        cols_present = [c for c in cols_needed if c in df.columns]
        return df[cols_present]

    except Exception as e:
        logger.error("Failed to fetch economic calendar via BQL: %s", e)
        return pd.DataFrame()


def fetch_central_banks() -> pd.DataFrame:
    """Fetch central bank events via BQL.

    Returns DataFrame with columns: PAÍS, DATA, HORÁRIO, EVENTO.
    See ``fetch_eco_calendar`` for why this uses polars-bloomberg.
    """
    from polars_bloomberg import BQuery

    countries = ",".join(f"'{c}'" for c in BQL_COUNTRIES)
    query = f"""
        get(dropna(calendar(view=condensed, type=central_banks), remove_id=true))
        for ([{countries}])
        with(dates={BQL_DATE_RANGE})
    """

    try:
        with BQuery() as bq:
            result = bq.bql(query)

        df = _bql_to_pandas(result)
        if df is None:
            return pd.DataFrame()

        column_mapping = {
            "COUNTRY_NAME": "PAÍS",
            "RELEASE_DATE": "DATA",
            "RELEASE_TIME": "HORÁRIO",
            "EVENT_NAME": "EVENTO",
        }

        df = _map_bql_columns(df, column_mapping)

        cols_needed = ["PAÍS", "DATA", "HORÁRIO", "EVENTO"]
        cols_present = [c for c in cols_needed if c in df.columns]
        return df[cols_present]

    except Exception as e:
        logger.error("Failed to fetch central bank events via BQL: %s", e)
        return pd.DataFrame()
