"""Market-holiday detection for the monitor panel.

The monitor draws a "market closed" tile whenever Bloomberg returns no
intraday bars for an instrument. That alone can't tell a genuine exchange
holiday apart from a data error. This module maps each ticker to a
``pandas-market-calendars`` exchange and reports whether that market is
closed for a holiday on a given day, so the panel can label the tile
"Feriado" instead of the generic closed image.

FX, gold, oil and crypto trade ~24/5 and have no reliable single-exchange
holiday calendar, so they are intentionally unmapped (see
``tickers.MARKET_CALENDARS``) and keep the generic closed image.
"""

import logging
from datetime import date, datetime

import pandas as pd

from comentario_matinal.render.tickers import MARKET_CALENDARS

logger = logging.getLogger("comentario_matinal")

# Cache calendar objects — building them is non-trivial and tickers repeat.
_CAL_CACHE: dict[str, object] = {}


def _get_calendar(name: str):
    if name not in _CAL_CACHE:
        import pandas_market_calendars as mcal

        _CAL_CACHE[name] = mcal.get_calendar(name)
    return _CAL_CACHE[name]


def is_market_holiday(ticker: str, day: date | None = None) -> bool:
    """Return True if ``ticker``'s mapped exchange is closed for a holiday.

    Returns False when the market is open, when ``day`` is a weekend (not a
    "holiday"), or when the ticker has no calendar mapping. Early-close /
    half-day sessions count as open and return False.

    The monitor uses this to force the "market closed" tile on a holiday even
    when a few stray bars come back (e.g. USGG10YR keeps ticking from
    overnight London/Asia trading on a SIFMA holiday).
    """
    name = MARKET_CALENDARS.get(ticker)
    if name is None:
        return False

    day = day or datetime.now().date()
    ts = pd.Timestamp(day)
    if ts.weekday() >= 5:  # weekend — not a holiday
        return False

    try:
        cal = _get_calendar(name)
        sched = cal.schedule(start_date=ts, end_date=ts)
    except Exception as e:
        logger.warning("Holiday lookup failed for %s (%s): %s", ticker, name, e)
        return False

    return len(sched) == 0  # no session that day → holiday
