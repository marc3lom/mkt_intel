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
    # Índice cujo valor é um nível, não um preço em dólares. Renderiza como
    # ação de propósito: o formatador de commodity prefixa "$", o que estaria
    # errado para o nível de um índice como o BCOM.
    "indice": "equity",
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
    coluna: int          # coluna da grade, 1-based

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

    def ordem_da_grade(self) -> list[Ativo]:
        """Transpõe a lista, de ordem de coluna para ordem de leitura por linha.

        O painel.toml agrupa os ativos por coluna, uma categoria em cada, porque
        é assim que a grade se lê. O matplotlib numera os subplots por linha, e
        os preenche em sequência: não há como pular uma célula no meio.

        Daí a checagem no fim. Enquanto as colunas curtas forem as últimas, as
        células vazias caem no fim da grade e a numeração sequencial acerta. Se
        uma coluna curta vier antes de uma cheia, o buraco cairia no meio e todos
        os ativos seguintes deslizariam uma célula — silenciosamente, e o painel
        sairia com o ativo errado sob cada rótulo de categoria.
        """
        linhas, colunas = self.grade
        por_coluna: dict[int, list[Ativo]] = {c: [] for c in range(1, colunas + 1)}
        for ativo in self.ativos:
            por_coluna[ativo.coluna].append(ativo)

        celulas: list[Ativo | None] = []
        for linha in range(linhas):
            for coluna in range(1, colunas + 1):
                fila = por_coluna[coluna]
                celulas.append(fila[linha] if linha < len(fila) else None)

        preenchidas = [c for c in celulas if c is not None]
        ultima = max((i for i, c in enumerate(celulas) if c is not None), default=-1)
        if any(c is None for c in celulas[:ultima]):
            curtas = [c for c in range(1, colunas + 1)
                      if 0 < len(por_coluna[c]) < len(por_coluna[colunas])]
            raise RuntimeError(
                "A grade ficaria com célula vazia no meio, e o painel sairia com "
                "os ativos deslocados. Colunas curtas precisam ser as últimas; "
                f"revisar as colunas {curtas or 'do painel.toml'}."
            )
        return preenchidas

    def para_ticker_info(self, ativos: list[Ativo] | None = None) -> list[TickerInfo]:
        """Converte para o formato que ``daily.monitor`` espera."""
        return [
            TickerInfo(
                ticker=a.ticker,
                name=a.rotulo,
                display=a.rotulo_grade,
                type=a.tipo_render,
            )
            for a in (self.ativos if ativos is None else ativos)
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

    linhas, colunas = painel.get("grade", [5, 4])

    ativos = []
    for i, e in enumerate(entradas):
        faltando = {"ticker", "rotulo", "rotulo_grade", "tipo", "coluna"} - set(e)
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
        if not 1 <= e["coluna"] <= colunas:
            raise RuntimeError(
                f"Coluna {e['coluna']} em {e['ticker']} fora da grade, que tem "
                f"{colunas} colunas."
            )
        ativos.append(Ativo(e["ticker"], e["rotulo"], e["rotulo_grade"],
                            e["tipo"], e["coluna"]))

    duplicados = {t for t in (a.ticker for a in ativos)
                  if [a.ticker for a in ativos].count(t) > 1}
    if duplicados:
        raise RuntimeError(f"Tickers repetidos no painel: {', '.join(sorted(duplicados))}")

    if linhas * colunas < len(ativos):
        raise RuntimeError(
            f"Grade {linhas}x{colunas} comporta {linhas * colunas} tiles, "
            f"mas o painel tem {len(ativos)} ativos."
        )

    for coluna in range(1, colunas + 1):
        altura = sum(1 for a in ativos if a.coluna == coluna)
        if altura > linhas:
            raise RuntimeError(
                f"Coluna {coluna} tem {altura} ativos, mas a grade só tem "
                f"{linhas} linhas."
            )

    return Config(
        ativos=ativos,
        grade=(linhas, colunas),
        limiar_estabilidade=painel.get("limiar_estabilidade", 0.25),
        limiar_estabilidade_taxa=painel.get("limiar_estabilidade_taxa", 0.01),
    )
