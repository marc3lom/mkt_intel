"""Coleta do calendário econômico via BQL.

Só o calendário: o dado de mercado do painel vem de ``dados.py``, que é o único
caminho até o Bloomberg para preço e barras intradiárias.
"""

import logging

import pandas as pd

logger = logging.getLogger("comentario_matinal")

# Países consultados no BQL
PAISES = [
    "US Country", "CA Country", "GB Country", "DE Country",
    "AU Country", "JP Country", "EZ Country", "CN Country",
]

# Janela de datas do BQL
JANELA = "range(-1d,0d)"


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


def busca_calendario() -> pd.DataFrame:
    """Busca o calendário econômico via BQL.

    Usa polars-bloomberg.BQuery porque marca a requisição BQL com
    ``clientContext.appName=EXCEL``, que a licença Bloomberg Anywhere exige
    para acesso ao BQL. O endpoint BQL do xbbg omite essa marca e é rejeitado
    com "User not authorized to use BQL" em licenças Anywhere.

    Retorna DataFrame com as colunas: PAÍS, DATA, HORÁRIO, EVENTO, PERÍODO,
    ESTIMATIVA, ATUAL, ANTERIOR, REVISADO
    """
    from polars_bloomberg import BQuery

    countries = ",".join(f"'{c}'" for c in PAISES)
    query = f"""
        get(dropna(calendar(relevancy=VERY_HIGH), remove_id=true))
        for ([{countries}])
        with(dates={JANELA})
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
        logger.error("Falha ao buscar o calendário econômico via BQL: %s", e)
        return pd.DataFrame()


def busca_bancos_centrais() -> pd.DataFrame:
    """Busca os eventos de bancos centrais via BQL.

    Retorna DataFrame com as colunas: PAÍS, DATA, HORÁRIO, EVENTO.
    Ver ``busca_calendario`` para o motivo de usar polars-bloomberg.
    """
    from polars_bloomberg import BQuery

    countries = ",".join(f"'{c}'" for c in PAISES)
    query = f"""
        get(dropna(calendar(view=condensed, type=central_banks), remove_id=true))
        for ([{countries}])
        with(dates={JANELA})
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
        logger.error("Falha ao buscar os eventos de bancos centrais via BQL: %s", e)
        return pd.DataFrame()
