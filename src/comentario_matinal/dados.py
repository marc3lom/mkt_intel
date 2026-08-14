"""A consulta de mercado — uma só, servindo imagem e texto.

Toda a informação de mercado do plantão nasce aqui, num único ``DataFrame`` de
referência mais um dicionário de séries intradiárias. O painel em imagem e o
bloco direcional em texto consomem esse mesmo material; não existe segundo
caminho até o Bloomberg.
"""

from __future__ import annotations

import sys
from datetime import datetime

import pandas as pd

from comentario_matinal.config import Ativo

# Campos de referência. CHG_PCT_1D é pedido apenas para conferência: o valor
# usado é sempre recalculado (ver _com_variacao_confiavel).
CAMPOS_REF = ["PX_LAST", "CHG_NET_1D", "CHG_PCT_1D"]


def _para_longo(resultado) -> pd.DataFrame:
    """Normaliza o retorno do xbbg para um DataFrame pandas em formato longo.

    O xbbg 1.4.x devolve um DataFrame Narwhals com colunas (ticker, field,
    value). Converter uma vez aqui mantém o resto do módulo indiferente à forma e
    ao backend que o Narwhals embrulha.
    """
    df = resultado.to_pandas() if hasattr(resultado, "to_pandas") else resultado
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["ticker", "field", "value"])
    if not {"ticker", "field", "value"}.issubset(df.columns):
        raise RuntimeError(
            "Formato inesperado no retorno do Bloomberg: colunas "
            f"{list(df.columns)}. Esperado ticker/field/value."
        )
    return df


def _com_variacao_confiavel(ref: pd.DataFrame) -> pd.DataFrame:
    """Recalcula ``chg_pct_1d`` a partir de ``px_last`` e do fechamento anterior.

    O CHG_PCT_1D do Bloomberg vem calculado sobre a convenção invertida em alguns
    pares de câmbio: em USD/JPY e USD/CNH o campo chega com o sinal trocado — a
    magnitude bate, mas a direção é a do par inverso. Como o sinal decide a cor do
    tile e a palavra do texto, um campo que erra a direção em parte dos ativos não
    serve para nenhum. O fechamento anterior é reconstruído de px_last menos a
    variação líquida, que é confiável, e a percentagem sai daí.
    """
    ref = ref.copy()
    anterior = ref["px_last"] - ref["chg_net_1d"]
    ref["px_close_1d"] = anterior
    ref["chg_pct_1d"] = (ref["px_last"] / anterior - 1.0) * 100.0
    ref.loc[anterior == 0, "chg_pct_1d"] = float("nan")
    return ref


def coleta_referencia(ativos: list[Ativo]) -> tuple[pd.DataFrame, list[str]]:
    """Puxa preço e variação diária de todos os ativos numa única chamada.

    Devolve o DataFrame indexado por ticker e a lista de ativos sem dado
    utilizável — ticker ausente da resposta ou com campo nulo, que é o caso de
    contrato vencido ou feriado de praça.
    """
    from xbbg import blp

    tickers = [a.ticker for a in ativos]
    longo = _para_longo(blp.bdp(tickers=tickers, flds=CAMPOS_REF))

    if longo.empty:
        return pd.DataFrame(), list(tickers)

    ref = longo.pivot(index="ticker", columns="field", values="value")
    ref.columns = [str(c).lower() for c in ref.columns]
    ref = ref.apply(pd.to_numeric, errors="coerce")
    ref.index.name = None

    for campo in ("px_last", "chg_net_1d", "chg_pct_1d"):
        if campo not in ref.columns:
            ref[campo] = float("nan")

    ref = ref.reindex(tickers)
    indisponiveis = [
        t for t in tickers
        if pd.isna(ref.at[t, "px_last"]) or pd.isna(ref.at[t, "chg_net_1d"])
    ]
    return _com_variacao_confiavel(ref), indisponiveis


def coleta_intraday(ativos: list[Ativo], quando: datetime) -> dict[str, pd.Series]:
    """Puxa as barras intradiárias de cada ativo, para as sparklines.

    Uma chamada por ativo: é assim que a API de barras funciona, não há forma de
    pedir vários instrumentos de uma vez. Falha de um ativo não derruba o painel —
    o tile correspondente cai para a imagem de mercado fechado.
    """
    from xbbg import blp

    dia = quando.date()
    series: dict[str, pd.Series] = {}

    for ativo in ativos:
        try:
            barras = blp.bdib(ticker=ativo.ticker, dt=dia, session="allday")
            if hasattr(barras, "to_pandas"):
                barras = barras.to_pandas()
            if barras is None or len(barras) == 0:
                series[ativo.ticker] = pd.Series(dtype="float64")
                continue

            if "ticker" in barras.columns:
                barras = barras[barras["ticker"] == ativo.ticker]
            if "time" in barras.columns and "close" in barras.columns:
                serie = barras.set_index("time")["close"]
            else:
                serie = barras["close"] if "close" in barras.columns else pd.Series(dtype="float64")

            series[ativo.ticker] = pd.to_numeric(serie, errors="coerce").dropna()
        except Exception as e:  # noqa: BLE001 — um ativo não pode derrubar o painel
            print(f"Aviso: barras intradiárias indisponíveis para {ativo.ticker} "
                  f"({type(e).__name__}: {e})", file=sys.stderr)
            series[ativo.ticker] = pd.Series(dtype="float64")

    return series
