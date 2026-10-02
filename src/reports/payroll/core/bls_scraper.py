"""
BLS Employment Situation industry breakdown.

Busca a abertura setorial do emprego (CES, com ajuste sazonal) pela API pública v2
do BLS. A página da Tabela B (`empsit.b.htm`) responde 403 a qualquer requisição
automatizada, com ou sem User-Agent de navegador; a API é o caminho que o BLS
oferece para script, e sem chave aceita até 25 séries por consulta.
"""

import datetime as dt
import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# Setor → (série CES, nível na hierarquia). A ordem é a da Tabela B; os nomes são
# os que o INDUSTRY_ORDER dos notebooks procura.
BLS_SERIES: dict[str, tuple[str, int]] = {
    "Total nonfarm": ("CES0000000001", 0),
    "Total private": ("CES0500000001", 1),
    "Goods-producing": ("CES0600000001", 1),
    "Mining and logging": ("CES1000000001", 2),
    "Construction": ("CES2000000001", 2),
    "Manufacturing": ("CES3000000001", 2),
    "Durable goods": ("CES3100000001", 3),
    "Motor vehicles and parts": ("CES3133600101", 4),
    "Nondurable goods": ("CES3200000001", 3),
    "Private service-providing": ("CES0800000001", 1),
    "Wholesale trade": ("CES4142000001", 2),
    "Retail trade": ("CES4200000001", 2),
    "Transportation and warehousing": ("CES4300000001", 2),
    "Utilities": ("CES4422000001", 2),
    "Information": ("CES5000000001", 2),
    "Financial activities": ("CES5500000001", 2),
    "Professional and business services": ("CES6000000001", 2),
    "Temporary help services": ("CES6056132001", 3),
    "Private education and health services": ("CES6500000001", 2),
    "Health care and social assistance": ("CES6562000001", 3),
    "Leisure and hospitality": ("CES7000000001", 2),
    "Other services": ("CES8000000001", 2),
    "Government": ("CES9000000001", 1),
}


def fetch_industry_breakdown() -> pd.DataFrame:
    """Fetch industry breakdown data from the BLS API.

    Returns:
        DataFrame with columns:
        - industry: Industry name
        - level: Hierarchy level (0=total, 1=sector, 2=subsector, etc.)
        - current_month: Latest month change (thousands)
        - prior_month: Previous month change (thousands)
        - prior_year: Change over the last 12 months (thousands)

    Raises:
        RuntimeError: If data fetch or parsing fails.
    """
    year = dt.date.today().year
    payload = {
        "seriesid": [series for series, _ in BLS_SERIES.values()],
        "startyear": str(year - 1),
        "endyear": str(year),
    }
    logger.info(f"Fetching BLS data from {BLS_API_URL}")

    try:
        response = requests.post(BLS_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(f"Failed to fetch BLS data: {e}")

    return parse_bls_response(data)


def parse_bls_response(data: dict[str, Any]) -> pd.DataFrame:
    """Turn a BLS API v2 response into the industry breakdown table.

    As variações são diferenças de nível, em milhares: o mês corrente contra o
    anterior, o anterior contra o retrasado, e o corrente contra doze meses antes.

    Args:
        data: Decoded JSON from the BLS API.

    Returns:
        DataFrame in the format described in fetch_industry_breakdown().

    Raises:
        RuntimeError: If the API reports failure or returns no usable series.
    """
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {data.get('message')}")

    levels: dict[str, pd.Series] = {}
    for series in data.get("Results", {}).get("series", []):
        points = {
            pd.Period(f"{p['year']}-{p['period'][1:]}", freq="M"): float(p["value"])
            for p in series["data"]
            if p["period"].startswith("M") and p["period"] != "M13" and p["value"] != "-"
        }
        levels[series["seriesID"]] = pd.Series(points).sort_index()

    records = []
    for industry, (series_id, level) in BLS_SERIES.items():
        s = levels.get(series_id)
        if s is None or len(s) < 3:
            continue
        records.append(
            {
                "industry": industry,
                "level": level,
                "prior_year": s.iloc[-1] - s.iloc[-13] if len(s) >= 13 else None,
                "prior_month": s.iloc[-2] - s.iloc[-3],
                "current_month": s.iloc[-1] - s.iloc[-2],
            }
        )

    if not records:
        raise RuntimeError("No usable series in BLS API response")

    return pd.DataFrame(records)


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
