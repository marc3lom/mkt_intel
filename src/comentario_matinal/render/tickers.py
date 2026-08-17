"""Ticker definitions and reference mappings for the monitor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TickerInfo:
    """Represents a single monitored asset."""

    ticker: str
    name: str
    display: str
    type: str  # "rate", "equity", "fx", "commodity", "vol"


MONITOR_TICKERS: list[TickerInfo] = [
    # Row 1: Rates | Equities | FX | Commodities
    TickerInfo("USGG10YR Index", "us_trsy_10y", "Trsy 10y", "rate"),
    TickerInfo("ES1 Index", "spx_fut", "S&P 500 Fut", "equity"),
    TickerInfo("DXY Curncy", "dxy", "DXY", "fx"),
    TickerInfo("XAU Curncy", "xau", "Ouro", "commodity"),
    # Row 2: Europe
    TickerInfo("GDBR10 Index", "bund_10y", "Bund 10y", "rate"),
    TickerInfo("VG1 Index", "eurostoxx_fut", "EuroStoxx 50 Fut", "equity"),
    TickerInfo("EUR Curncy", "eur", "EUR", "fx"),
    TickerInfo("CO1 Comdty", "brent", "Brent", "commodity"),
    # Row 3: Japan + VIX
    TickerInfo("GTJPY10Y Govt", "jgb_10y", "JGB 10y", "rate"),
    TickerInfo("NK1 Index", "nikkei_fut", "Nikkei 225 Fut", "equity"),
    TickerInfo("JPY Curncy", "jpy", "JPY", "fx"),
    TickerInfo("VIX Index", "vix", "VIX", "vol"),
    # Row 4: China + Bitcoin
    TickerInfo("GCNY10YR Index", "cgb_10y", "CGB 10y", "rate"),
    TickerInfo("IFB1 Index", "csi300_fut", "CSI 300 Fut", "equity"),
    TickerInfo("CNH Curncy", "cnh", "CNH", "fx"),
    TickerInfo("XBTUSD BGN Curncy", "bitcoin", "Bitcoin", "fx"),
]

ALL_TICKERS: list[str] = [t.ticker for t in MONITOR_TICKERS]

# Exchange calendars (pandas-market-calendars names) for holiday detection.
# Used by comentario_matinal.render.calendars to tell a genuine market holiday
# ("Feriado") apart
# from a missing-data error when no intraday bars come back. Only instruments
# with a reliable single-exchange calendar are mapped; FX, gold, oil and crypto
# trade ~24/5 and have no such calendar, so they are intentionally omitted and
# fall back to the generic "market closed" image.
MARKET_CALENDARS: dict[str, str] = {
    "USGG10YR Index": "SIFMAUS",   # US Treasury cash (SIFMA bond calendar)
    "ES1 Index": "CME_Equity",     # S&P 500 future (CME)
    "GDBR10 Index": "EUREX_Bond",  # Bund / German govt 10y (Eurex bond)
    "VG1 Index": "EUREX",          # EuroStoxx 50 future (Eurex)
    "GTJPY10Y Govt": "JPX",        # JGB 10y (Japan)
    "NK1 Index": "JPX",            # Nikkei 225 future (Osaka / JPX)
    "GJGB10 Index": "JPX",         # JGB 10y yield index (Japan)
    "GUKG10 Index": "LSE",         # Gilt 10y (UK)
    "Z 1 Index": "LSE",            # FTSE 100 future (ICE Europe, feriados do UK)
    "GCNY10YR Index": "XSHG",      # China govt 10y (mainland China calendar)
    "IFB1 Index": "XSHG",          # CSI 300 future (CFFEX ~ mainland China)
    "VIX Index": "CFE",            # VIX (CBOE)
}

# Tickers that require a reference for bdib calls
BDIB_REF_MAPPING: dict[str, str] = {
    "USGG10YR Index": "ES1 Index",
    "GDBR10 Index": "ES1 Index",
    "GCNY10YR Index": "ES1 Index",
    "NK1 Index": "ES1 Index",
    "CO1 Comdty": "ES1 Index",
    "VG1 Index": "ES1 Index",
    "IFB1 Index": "ES1 Index",
    "DXY Curncy": "EUR Curncy",
    "CNH Curncy": "EUR Curncy",
    "XBTUSD BGN Curncy": "EUR Curncy",
    "VIX Index": "ES1 Index",
}
