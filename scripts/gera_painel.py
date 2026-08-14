"""Generate the directional panel and the economic calendar as plain text.

The morning commentary workflow feeds three things to the LLM: news PDFs, the chart
panel, and the day's economic calendar. The panel and the calendar currently arrive as
images, which forces the model to read charts -- the least reliable thing it does, and
the source of the two error classes we care about most: wrong direction, and treating an
unreleased data point as a published fact.

This script emits both as text so those checks become deterministic.

Usage:
    uv run scripts/gera_painel.py --saida painel.txt
    uv run scripts/gera_painel.py --asof 2026-08-14T07:35 --saida painel.txt

Requires an active Bloomberg terminal session (xbbg/blpapi).
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from xbbg import blp

TZ_BR = ZoneInfo("America/Sao_Paulo")
TZ_NY = ZoneInfo("America/New_York")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "painel.toml"


def carrega_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _direcao(variacao: float, limiar: float) -> str:
    """Map a percentage change to a qualitative direction.

    The threshold exists so that noise is not narrated as a move: anything inside the
    band is reported as stable, which is what the commentary should say too.
    """
    if abs(variacao) < limiar:
        return "estável"
    if variacao > 0:
        return "alta"
    return "baixa"


def coleta_painel(cfg: dict) -> pd.DataFrame:
    """Pull last price and previous close for every panel ticker."""
    taxas = cfg["painel"]["taxas"]
    precos = cfg["painel"]["precos"]
    tickers = list(taxas) + list(precos)

    # PX_LAST vs PX_CLOSE_1D gives the day-over-day move without pulling history.
    dados = blp.bdp(tickers=tickers, flds=["PX_LAST", "PX_CLOSE_1D"])

    linhas = []
    for ticker in tickers:
        if ticker not in dados.index:
            linhas.append({"ticker": ticker, "rotulo": taxas.get(ticker) or precos.get(ticker),
                           "tipo": "taxa" if ticker in taxas else "preco",
                           "variacao_pct": float("nan"), "direcao": "indisponível"})
            continue

        ultimo = float(dados.loc[ticker, "px_last"])
        anterior = float(dados.loc[ticker, "px_close_1d"])
        # For yields the level IS the rate, so a percentage change on the level is a
        # poor scale. Report the move in basis points instead, but keep a percentage
        # column for the threshold test.
        if ticker in taxas:
            delta_bp = (ultimo - anterior) * 100
            variacao = delta_bp / 100  # in percentage points, for threshold purposes
            direcao = _direcao(variacao, 0.01)  # 1bp threshold for rates
        else:
            variacao = (ultimo / anterior - 1) * 100
            direcao = _direcao(variacao, cfg["painel"]["limiar_estabilidade"])

        linhas.append({
            "ticker": ticker,
            "rotulo": taxas.get(ticker) or precos.get(ticker),
            "tipo": "taxa" if ticker in taxas else "preco",
            "variacao_pct": variacao,
            "direcao": direcao,
        })

    return pd.DataFrame(linhas)


def coleta_calendario(cfg: dict, referencia: date) -> pd.DataFrame:
    """Pull release timing, survey median, and actual for the tracked indicators.

    ECO_RELEASE_DT and the actual value are what let the review step distinguish a
    published number from a scheduled one. An empty actual on a release dated today is
    exactly the case that must never appear in the text as a fact.
    """
    tickers = cfg["calendario"]["tickers"]
    flds = ["NAME", "ECO_RELEASE_DT", "ECO_RELEASE_TIME", "BN_SURVEY_MEDIAN", "PX_LAST"]
    dados = blp.bdp(tickers=tickers, flds=flds)

    linhas = []
    for ticker in tickers:
        if ticker not in dados.index:
            continue
        linha = dados.loc[ticker]
        data_release = pd.to_datetime(linha.get("eco_release_dt"), errors="coerce")
        if pd.isna(data_release) or data_release.date() != referencia:
            continue
        linhas.append({
            "evento": linha.get("name", ticker),
            "horario": linha.get("eco_release_time", ""),
            "estimativa": linha.get("bn_survey_median"),
            "atual": linha.get("px_last"),
        })

    return pd.DataFrame(linhas)


def formata(painel: pd.DataFrame, calendario: pd.DataFrame, asof: datetime) -> str:
    """Render both blocks as text meant to be pasted alongside the news PDFs."""
    out: list[str] = []

    asof_ny = asof.astimezone(TZ_NY)
    out.append("PAINEL DIRECIONAL")
    out.append(f"Referência: {asof:%d/%m/%Y %H:%M} de Brasília "
               f"({asof_ny:%H:%M} de Nova York)")
    out.append("Direções apuradas contra o fechamento anterior. "
               "Sem níveis — uso exclusivo para checagem de coerência.")
    out.append("")

    out.append("Taxas (direção da taxa):")
    for _, r in painel[painel.tipo == "taxa"].iterrows():
        out.append(f"  {r.rotulo}: {r.direcao}")

    out.append("")
    out.append("Preços:")
    for _, r in painel[painel.tipo == "preco"].iterrows():
        out.append(f"  {r.rotulo}: {r.direcao}")

    out.append("")
    out.append("CALENDÁRIO ECONÔMICO DO DIA")
    if calendario.empty:
        out.append("  Sem releases acompanhados para a data.")
    else:
        for _, r in calendario.iterrows():
            # The status flag is the point of this block: it is what the writing and
            # review prompts key on to refuse an unreleased number.
            divulgado = pd.notna(r.atual)
            status = "DIVULGADO" if divulgado else "AINDA NÃO DIVULGADO"
            out.append(f"  {r.evento} — previsto para {r.horario} — {status}")

    out.append("")
    out.append("Nota: item marcado como AINDA NÃO DIVULGADO não pode aparecer no "
               "comentário como fato consumado, ainda que citado por wrap de fonte.")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", type=str, default=None,
                        help="Horário de referência ISO, ex. 2026-08-14T07:35. "
                             "Padrão: agora, em horário de Brasília.")
    parser.add_argument("--saida", type=Path, default=None,
                        help="Arquivo de saída. Padrão: stdout.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    asof = (datetime.fromisoformat(args.asof).replace(tzinfo=TZ_BR)
            if args.asof else datetime.now(TZ_BR))

    cfg = carrega_config(args.config)
    painel = coleta_painel(cfg)
    calendario = coleta_calendario(cfg, asof.date())
    texto = formata(painel, calendario, asof)

    if args.saida:
        args.saida.write_text(texto, encoding="utf-8")
        print(f"Escrito em {args.saida}")
    else:
        print(texto)

    indisponiveis = painel[painel.direcao == "indisponível"]
    if not indisponiveis.empty:
        print(f"\nAviso: {len(indisponiveis)} ticker(s) sem dado — "
              f"{', '.join(indisponiveis.ticker)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
