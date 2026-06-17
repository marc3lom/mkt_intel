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
from zoneinfo import ZoneInfo

import pandas as pd

# Fusos usados na reação de mercado intraday
_TZ_ET = ZoneInfo("America/New_York")  # horários do FOMC são fixos em ET
_TZ_BRT = ZoneInfo("America/Sao_Paulo")  # fuso de exibição (Brasília)

logger = logging.getLogger(__name__)

# Meses das reuniões com SEP (Summary of Economic Projections)
SEP_MONTHS = {3, 6, 9, 12}

# Bloomberg tickers para o grid de reação de mercado (espelhando o Chart Grid da
# Bloomberg). Bolsas usam E-mini futures (front contínuo) para capturar a sessão
# asiática/overnight — só os futuros negociam ~23h. Dois painéis são DERIVADOS:
# a inclinação 2s10s (de UST_2Y/UST_10Y) e o OIS forward 1Y1Y (dos OIS 1Y/2Y).
FOMC_TICKERS: dict[str, str] = {
    # Bolsas — E-mini futures contínuos (overnight desde a Ásia)
    "NASDAQ": "NQ1 Index",  # Nasdaq 100 E-mini
    "SPX": "ES1 Index",  # S&P 500 E-mini
    "RUSSELL": "RTY1 Index",  # Russell 2000 E-mini
    # Juros
    "UST_2Y": "USGG2YR Index",
    "UST_10Y": "USGG10YR Index",
    # FX / Volatilidade
    "DXY": "DXY Curncy",
    "VIX": "VIX Index",
}

# Tickers auxiliares: OIS USD (SOFR) 1Y e 2Y, usados para derivar o forward 1Y1Y
# intraday (não há ticker intraday direto do 1Y1Y). Não viram painel próprio.
OIS_HELPER_TICKERS: dict[str, str] = {
    "OIS_1Y": "USSO1 Curncy",  # USD SWAP OIS 1Y
    "OIS_2Y": "USSO2 Curncy",  # USD SWAP OIS 2Y
}

# Chaves das séries derivadas, calculadas em fetch_market_reaction.
SPREAD_2S10S_KEY = "SPREAD_2S10S"  # inclinação 2s10s (bps) = (10Y - 2Y) * 100
OIS_1Y1Y_KEY = "OIS_1Y1Y"  # forward 1Y1Y (%) via fatores de desconto dos OIS 1Y/2Y

# Bloomberg tickers para DOTS medians por horizonte
DOTS_TICKERS: dict[str, str] = {
    "Dots Median Ano Corrente": "DOTDY0MD Index",
    "Dots Median Ano+1": "DOTDY1MD Index",
    "Dots Median Ano+2": "DOTDY2MD Index",
    "Dots Median Longer Run": "DOTDLTMD Index",
}

# Mapeamento de meses em português (abreviado)
_MONTH_NAMES_PTBR: dict[int, str] = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
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
        raise RuntimeError("Bloomberg (xbbg) not available. Install with: uv add xbbg")


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
    start_time: str | None = None,
    end_time: str | None = None,
) -> pd.DataFrame:
    """Fetch intraday market data around an FOMC announcement.

    Busca os painéis de FOMC_TICKERS (+ OIS 1Y/2Y auxiliares) via Bloomberg,
    deriva a inclinação 2s10s (bps) e o OIS forward 1Y1Y (%), e devolve a série
    com índice tz-aware em horário de Brasília. Por padrão traz o dia inteiro
    (session="allday"), começando na sessão asiática — os E-mini futures
    negociam overnight, então o grid mostra todo o caminho até a reação ao FOMC.

    Args:
        date: FOMC meeting date in YYYYMMDD format.
        start_time: Filtro opcional de início (HH:MM, em ET). None = sem corte.
        end_time: Filtro opcional de fim (HH:MM, em ET). None = sem corte.

    Returns:
        DataFrame intraday (index tz-aware em America/Sao_Paulo) com uma coluna
        por painel: NASDAQ, SPX, RUSSELL, UST_2Y, UST_10Y, SPREAD_2S10S,
        OIS_1Y1Y, DXY, VIX (as que o Bloomberg retornar).

    Raises:
        RuntimeError: If Bloomberg is not available or data fetch fails.
    """
    blp = _get_bloomberg_client()

    # Parse date
    meeting_date = dt.datetime.strptime(date, "%Y%m%d")

    win = (
        "dia inteiro (Ásia→US)"
        if start_time is None and end_time is None
        else f"{start_time}-{end_time} ET"
    )
    logger.info(f"Fetching intraday data for {date} — janela: {win}")

    import narwhals as nw

    from classes.functions.bloomberg import _run_async

    # xbbg 1.0 (backend rust): abdib() aceita 1 ticker por vez e devolve colunas
    # [ticker, time, open, high, low, close, volume, ...] com RangeIndex; o
    # timestamp ("time", em UTC) é uma COLUNA, não o índice.
    frames = {}
    for name, ticker in {**FOMC_TICKERS, **OIS_HELPER_TICKERS}.items():
        try:
            raw = _run_async(
                blp.abdib(
                    ticker=ticker,
                    dt=meeting_date.date(),
                    session="allday",
                    backend="pandas",
                )
            )
            if raw is None:
                continue
            # Normaliza eventual wrapper narwhals/pyarrow para pandas
            try:
                df = nw.from_native(raw).to_pandas()
            except TypeError, AttributeError:
                df = raw
            if df is None or df.empty or "time" not in df.columns or "close" not in df.columns:
                continue
            series = pd.Series(
                df["close"].to_numpy(),
                index=pd.DatetimeIndex(df["time"]),  # tz-aware UTC
                name=name,
            ).dropna()
            if not series.empty:
                frames[name] = series
        except Exception as e:
            logger.warning(f"Failed to fetch intraday data for {ticker}: {e}")

    if not frames:
        raise RuntimeError("No intraday data returned from Bloomberg")

    data = pd.DataFrame(frames)

    # Derivar inclinação 2s10s (bps) quando ambos os yields existem
    if {"UST_2Y", "UST_10Y"} <= set(data.columns):
        spread = (data["UST_10Y"] - data["UST_2Y"]) * 100
        data = data.assign(**{SPREAD_2S10S_KEY: spread})

    # Derivar OIS forward 1Y1Y (%) dos OIS 1Y/2Y via fatores de desconto:
    #   f(1y,1y) = (1 + S2)^2 / (1 + S1) - 1
    if {"OIS_1Y", "OIS_2Y"} <= set(data.columns):
        s1 = data["OIS_1Y"] / 100
        s2 = data["OIS_2Y"] / 100
        fwd = ((1 + s2) ** 2 / (1 + s1) - 1) * 100
        data = data.assign(**{OIS_1Y1Y_KEY: fwd})

    # Descartar tickers auxiliares (não são painéis)
    data = data.drop(columns=list(OIS_HELPER_TICKERS), errors="ignore")

    # Converter o índice para horário de Brasília (e filtrar à janela ET, se dada)
    if isinstance(data.index, pd.DatetimeIndex):
        # Garantir índice tz-aware em ET (abdib devolve "time" em UTC)
        if data.index.tz is None:
            data.index = data.index.tz_localize(_TZ_ET)
        else:
            data.index = data.index.tz_convert(_TZ_ET)

        if start_time is not None:
            start_t = dt.datetime.strptime(start_time, "%H:%M").time()
            start_et = pd.Timestamp(dt.datetime.combine(meeting_date.date(), start_t), tz=_TZ_ET)
            data = data[data.index >= start_et]
        if end_time is not None:
            end_t = dt.datetime.strptime(end_time, "%H:%M").time()
            end_et = pd.Timestamp(dt.datetime.combine(meeting_date.date(), end_t), tz=_TZ_ET)
            data = data[data.index <= end_et]

        # Exibição em horário de Brasília
        data.index = data.index.tz_convert(_TZ_BRT)

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
    sep_path = _get_module_path() / "input" / "email_info" / "SEP.xlsx"

    if not sep_path.exists():
        raise RuntimeError(f"SEP file not found: {sep_path}")

    try:
        # Get sheet names to find most recent if not specified
        xl = pd.ExcelFile(sep_path)
        sheets = xl.sheet_names

        if sheet_name is None:
            # Filter to month-year sheets and get most recent
            date_sheets = [
                s
                for s in sheets
                if re.match(
                    r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+\d{2}", s, re.IGNORECASE
                )
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


def is_sep_meeting(date: str) -> bool:
    """Verifica se a data corresponde a uma reunião com SEP.

    Reuniões SEP ocorrem em março, junho, setembro e dezembro.

    Args:
        date: Data no formato YYYYMMDD.

    Returns:
        True se é reunião com SEP.
    """
    meeting_dt = dt.datetime.strptime(date, "%Y%m%d")
    return meeting_dt.month in SEP_MONTHS


def get_prior_sep_projections(
    current_date: str,
) -> pd.DataFrame | None:
    """Carrega projeções da reunião SEP anterior.

    Tenta carregar do SEP.xlsx primeiro, depois fallback para PDF.

    Args:
        current_date: Data da reunião atual (YYYYMMDD).

    Returns:
        DataFrame com projeções da reunião anterior, ou None.
    """
    from .calculations import get_prior_sep_meeting_date

    prior_date = get_prior_sep_meeting_date(current_date)
    if prior_date is None:
        logger.warning("Não foi possível determinar a reunião SEP anterior")
        return None

    # Tentar carregar do SEP.xlsx
    try:
        # Mapear mês para nome de sheet (formato: "set 25", "dez 25")
        prior_dt = dt.datetime.strptime(prior_date, "%Y%m%d")
        month_names = {
            1: "jan",
            2: "fev",
            3: "mar",
            4: "abr",
            5: "mai",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "set",
            10: "out",
            11: "nov",
            12: "dez",
        }
        sheet = f"{month_names[prior_dt.month]} {prior_dt.year % 100:02d}"
        data = load_sep_data(sheet_name=sheet)
        if not data.empty:
            logger.info(f"Projeções anteriores carregadas do SEP.xlsx (sheet: {sheet})")
            return data
    except RuntimeError, KeyError:
        logger.info("SEP.xlsx não possui sheet para reunião anterior, tentando PDF")

    # Fallback: parse do PDF da reunião anterior
    try:
        from .pdf_parser import parse_projection_table

        documents = get_meeting_documents(prior_date)
        if documents.get("projections"):
            proj_data = parse_projection_table(documents["projections"])
            medians = proj_data.get("medians")
            if medians is not None and not medians.empty:
                logger.info(f"Projeções anteriores carregadas do PDF ({prior_date})")
                return medians
    except RuntimeError:
        logger.warning(f"Não foi possível carregar projeções da reunião {prior_date}")

    return None


def load_market_reaction_data(sheet_name: str = "Market Reaction") -> pd.DataFrame:
    """Load market reaction data from Excel file.

    Args:
        sheet_name: Sheet to load. Default is "Market Reaction".

    Returns:
        DataFrame with market reaction data.

    Raises:
        RuntimeError: If file not found or parsing fails.
    """
    file_path = _get_module_path() / "input" / "email_info" / "Market_Reaction_FOMC.xlsm"

    if not file_path.exists():
        raise RuntimeError(f"Market reaction file not found: {file_path}")

    try:
        logger.info(f"Loading market reaction data from sheet: {sheet_name}")
        data = pd.read_excel(file_path, sheet_name=sheet_name)
        return data

    except Exception as e:
        raise RuntimeError(f"Failed to load market reaction data: {e}")


def load_dots_history(
    start_date: str = "2012-01-01",
    end_date: str | None = None,
) -> pd.DataFrame:
    """Baixa série histórica dos DOTS medians via Bloomberg.

    Cada ponto na série corresponde ao valor publicado em cada reunião SEP.

    Args:
        start_date: Data de início (YYYY-MM-DD).
        end_date: Data de fim. Se None, usa hoje.

    Returns:
        DataFrame indexado por data, uma coluna por horizonte.

    Raises:
        RuntimeError: Se Bloomberg não estiver disponível.
    """
    blp = _get_bloomberg_client()

    tickers = list(DOTS_TICKERS.values())
    names = list(DOTS_TICKERS.keys())

    if end_date is None:
        end_date = dt.date.today().strftime("%Y-%m-%d")

    logger.info(f"Fetching DOTS history from {start_date} to {end_date}")

    from classes.functions.bloomberg import _run_async

    try:
        data = _run_async(
            blp.abdh(
                tickers=tickers,
                flds="PX_LAST",
                start_date=start_date,
                end_date=end_date,
                backend="pandas",
            )
        )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch DOTS history from Bloomberg: {e}")

    if data is None or data.empty:
        raise RuntimeError("No DOTS history returned from Bloomberg")

    # xbbg 1.0: LONG format [ticker, date, field, value] (tudo string)
    ticker_to_name = dict(zip(tickers, names))
    if "ticker" in data.columns and "value" in data.columns:
        data["date"] = pd.to_datetime(data["date"])
        data["value"] = pd.to_numeric(data["value"], errors="coerce")
        data = data.pivot(index="date", columns="ticker", values="value")
        data.columns = [ticker_to_name.get(c, c) for c in data.columns]
    elif isinstance(data.columns, pd.MultiIndex):
        data.columns = [ticker_to_name.get(col[0], col[0]) for col in data.columns]
    else:
        data.columns = names[: len(data.columns)]

    # Drop rows where all values are NaN (non-SEP dates)
    data = data.dropna(how="all")

    logger.info(f"DOTS history: {len(data)} observations loaded")
    return data


def load_dots_snapshot(
    grid_path: str | Path | None = None,
) -> dict[str, float]:
    """Lê último valor dos DOTS do grid1.xlsx como fallback.

    Args:
        grid_path: Caminho para grid1.xlsx. Se None, busca em input/.

    Returns:
        Dict ticker → último valor (ex: {"DOTDY0MD Index": 3.375}).
    """
    if grid_path is None:
        # Tentar caminho padrão do projeto
        grid_path = Path(__file__).parents[4] / "input" / "grid1.xlsx"

    grid_path = Path(grid_path)
    if not grid_path.exists():
        raise RuntimeError(f"Grid file not found: {grid_path}")

    logger.info(f"Loading DOTS snapshot from: {grid_path}")

    df = pd.read_excel(grid_path)

    # Buscar colunas de ticker e valor
    # O grid1.xlsx tipicamente tem colunas: Ticker, Last, ...
    # Procurar por nomes comuns
    ticker_col = None
    value_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if "ticker" in col_lower:
            ticker_col = col
        elif col_lower in ("last", "px_last", "value", "valor"):
            value_col = col

    if ticker_col is None or value_col is None:
        # Fallback: assume primeira coluna = ticker, segunda = valor
        ticker_col = df.columns[0]
        value_col = df.columns[1]

    # Filtrar apenas tickers de DOTS
    dots_tickers_set = set(DOTS_TICKERS.values())
    result = {}
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip()
        if ticker in dots_tickers_set:
            try:
                result[ticker] = float(row[value_col])
            except ValueError, TypeError:
                continue

    if result:
        logger.info(f"DOTS snapshot: {len(result)} tickers loaded")
    else:
        logger.warning("No DOTS tickers found in grid file")

    return result


def save_sep_to_excel(
    meeting_date: str,
    medians: pd.DataFrame,
    prior_medians: pd.DataFrame | None = None,
    prior_label: str = "Prior projection",
    ct: pd.DataFrame | None = None,
    ranges: pd.DataFrame | None = None,
) -> Path:
    """Salva dados do SEP no arquivo SEP.xlsx, adicionando nova sheet.

    A sheet é nomeada com o mês/ano da reunião (ex: "mar 26").
    Se a sheet já existe, ela é sobrescrita.

    Args:
        meeting_date: Data da reunião (YYYYMMDD).
        medians: DataFrame com medianas atuais.
        prior_medians: DataFrame com medianas anteriores (opcional).
        prior_label: Label da reunião anterior.
        ct: DataFrame com central tendency (opcional).
        ranges: DataFrame com ranges (opcional).

    Returns:
        Path do arquivo SEP.xlsx.
    """
    import openpyxl

    sep_path = _get_module_path() / "input" / "email_info" / "SEP.xlsx"

    # Calcular nome da sheet: "mar 26"
    meeting_dt = dt.datetime.strptime(meeting_date, "%Y%m%d")
    sheet_name = f"{_MONTH_NAMES_PTBR[meeting_dt.month]} {meeting_dt.year % 100:02d}"

    logger.info(f"Saving SEP data to sheet: {sheet_name}")

    # Abrir ou criar workbook
    if sep_path.exists():
        wb = openpyxl.load_workbook(str(sep_path))
    else:
        sep_path.parent.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()
        # Remover sheet padrão "Sheet"
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

    # Remover sheet existente se houver
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]

    ws = wb.create_sheet(sheet_name, 0)  # Inserir no início

    # --- Layout da sheet ---
    year_cols = [c for c in medians.columns if c != "Variable"]

    # Header: Medianas
    ws.cell(row=1, column=1, value="Variable")
    ws.cell(row=1, column=2, value="Mediana (Current)")
    for j, year in enumerate(year_cols):
        ws.cell(row=2, column=2 + j, value=str(year))

    # Medianas atuais
    row = 3
    for _, var_row in medians.iterrows():
        ws.cell(row=row, column=1, value=var_row["Variable"])
        for j, year in enumerate(year_cols):
            val = var_row.get(year)
            if pd.notna(val):
                ws.cell(row=row, column=2 + j, value=val)
        row += 1

    # Medianas anteriores
    if prior_medians is not None and not prior_medians.empty:
        row += 1
        ws.cell(row=row, column=1, value=f"Mediana ({prior_label})")
        row += 1
        for _, var_row in prior_medians.iterrows():
            ws.cell(row=row, column=1, value=var_row["Variable"])
            for j, year in enumerate(year_cols):
                val = var_row.get(year)
                if pd.notna(val):
                    ws.cell(row=row, column=2 + j, value=val)
            row += 1

    # Central Tendency
    if ct is not None and not ct.empty:
        row += 1
        ws.cell(row=row, column=1, value="Central Tendency (Current)")
        row += 1
        for _, var_row in ct.iterrows():
            ws.cell(row=row, column=1, value=var_row["Variable"])
            for j, year in enumerate(year_cols):
                val = var_row.get(year)
                if val is not None and str(val) != "nan":
                    ws.cell(row=row, column=2 + j, value=str(val))
            row += 1

    # Ranges
    if ranges is not None and not ranges.empty:
        row += 1
        ws.cell(row=row, column=1, value="Range (Current)")
        row += 1
        for _, var_row in ranges.iterrows():
            ws.cell(row=row, column=1, value=var_row["Variable"])
            for j, year in enumerate(year_cols):
                val = var_row.get(year)
                if val is not None and str(val) != "nan":
                    ws.cell(row=row, column=2 + j, value=str(val))
            row += 1

    wb.save(str(sep_path))
    logger.info(f"SEP data saved to: {sep_path} (sheet: {sheet_name})")

    return sep_path
