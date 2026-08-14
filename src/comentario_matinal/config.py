"""Leitura da configuração canônica do painel.

O ``config/painel.toml`` é a única lista de ativos do sistema. Ela é convertida
aqui para os ``TickerInfo`` que a camada de renderização do ``daily`` consome, de
modo que imagem e texto partam literalmente da mesma sequência de ativos.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from daily.tickers import TickerInfo

TZ_BR = ZoneInfo("America/Sao_Paulo")

RAIZ = Path(__file__).resolve().parent.parent.parent
CONFIG_PADRAO = RAIZ / "config" / "painel.toml"
SAIDA_PADRAO = RAIZ / "saida"

# Os tipos do painel.toml estão em português; a camada de renderização do daily
# despacha o formatador por chaves em inglês. A tradução é aqui, e só aqui.
TIPOS = {
    "taxa": "rate",
    "acao": "equity",
    "cambio": "fx",
    "commodity": "commodity",
    "vol": "vol",
}


@dataclass(frozen=True)
class Ativo:
    """Um ativo do painel, com os dois rótulos que ele precisa carregar."""

    ticker: str
    rotulo: str          # texto direcional — precisa ser inequívoco
    rotulo_grade: str    # tile da imagem — espaço curto
    tipo: str            # chave em português, como no painel.toml

    @property
    def tipo_render(self) -> str:
        return TIPOS[self.tipo]

    @property
    def e_taxa(self) -> bool:
        return self.tipo == "taxa"


@dataclass(frozen=True)
class Config:
    ativos: list[Ativo]
    grade: tuple[int, int]
    limiar_estabilidade: float
    limiar_estabilidade_taxa: float

    @property
    def tickers(self) -> list[str]:
        return [a.ticker for a in self.ativos]

    def para_ticker_info(self) -> list[TickerInfo]:
        """Converte para o formato que ``daily.monitor`` espera."""
        return [
            TickerInfo(
                ticker=a.ticker,
                name=a.rotulo,
                display=a.rotulo_grade,
                type=a.tipo_render,
            )
            for a in self.ativos
        ]


def carrega_config(path: Path = CONFIG_PADRAO) -> Config:
    with path.open("rb") as fh:
        bruto = tomllib.load(fh)

    painel = bruto["painel"]
    entradas = painel.get("ativo", [])
    if not entradas:
        raise RuntimeError(
            f"{path} não declara nenhum [[painel.ativo]]. Sem lista de ativos não "
            "há painel nem bloco direcional."
        )

    ativos = []
    for i, e in enumerate(entradas):
        faltando = {"ticker", "rotulo", "rotulo_grade", "tipo"} - set(e)
        if faltando:
            raise RuntimeError(
                f"[[painel.ativo]] #{i + 1} em {path} sem os campos: "
                f"{', '.join(sorted(faltando))}"
            )
        if e["tipo"] not in TIPOS:
            raise RuntimeError(
                f"Tipo desconhecido {e['tipo']!r} em {e['ticker']}. "
                f"Esperado um de: {', '.join(sorted(TIPOS))}."
            )
        ativos.append(Ativo(e["ticker"], e["rotulo"], e["rotulo_grade"], e["tipo"]))

    duplicados = {t for t in (a.ticker for a in ativos)
                  if [a.ticker for a in ativos].count(t) > 1}
    if duplicados:
        raise RuntimeError(f"Tickers repetidos no painel: {', '.join(sorted(duplicados))}")

    linhas, colunas = painel.get("grade", [5, 4])
    if linhas * colunas < len(ativos):
        raise RuntimeError(
            f"Grade {linhas}x{colunas} comporta {linhas * colunas} tiles, "
            f"mas o painel tem {len(ativos)} ativos."
        )

    return Config(
        ativos=ativos,
        grade=(linhas, colunas),
        limiar_estabilidade=painel.get("limiar_estabilidade", 0.25),
        limiar_estabilidade_taxa=painel.get("limiar_estabilidade_taxa", 0.01),
    )
