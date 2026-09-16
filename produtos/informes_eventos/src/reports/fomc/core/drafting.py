"""Etapas de modelo do informe do FOMC: resumo, bancos e revisão.

Cada etapa monta uma mensagem com o guia de estilo, o prompt da etapa e os
insumos do dia em blocos rotulados, chama o backend de `reports._modelo`,
grava a resposta inteira em output/reports/fomc/<data>/ e devolve o último
bloco cercado, que é o que o notebook consome. Nada roda sozinho: cada etapa
é uma célula que o autor executa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Raiz do produto: a pasta com o pyproject.toml. TestProjectRootAnchors prende.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROMPTS_DIR = PROJECT_ROOT / "prompts"

STYLE_GUIDE = "00_guia_de_estilo.md"
PROMPT_SUMMARY = "01_resumo.md"
PROMPT_BANKS = "02_bancos.md"
PROMPT_REVIEW = "03_revisao.md"

HEADLINES_FILE = "headlines.txt"
PRESSER_FILE = "coletiva.txt"
BANKS_DIR = "bancos"

OUT_SUMMARY_DECISION = "resumo_decisao.md"
OUT_SUMMARY_PRESSER = "resumo_coletiva.md"
OUT_BANKS = "bancos.md"
OUT_REVIEW = "revisao.md"


class DraftingError(RuntimeError):
    """Falha numa etapa: insumo ausente, resposta sem bloco, backend."""


@dataclass(frozen=True)
class Headline:
    text: str
    bold: bool


@dataclass(frozen=True)
class BankSource:
    name: str
    text: str


# --- pasta do dia --------------------------------------------------------------


def day_folder(meeting_date: str) -> Path:
    """<raiz>/input/fomc/<AAAAMMDD>: headlines.txt, coletiva.txt, bancos/."""
    return PROJECT_ROOT / "input" / "fomc" / meeting_date


def output_folder(meeting_date: str) -> Path:
    """<raiz>/output/reports/fomc/<AAAAMMDD>, criada se não existir."""
    folder = PROJECT_ROOT / "output" / "reports" / "fomc" / meeting_date
    folder.mkdir(parents=True, exist_ok=True)
    return folder


_STAR_PREFIX = re.compile(r"^(\*+)\s*")


def read_headlines(path: Path) -> list[Headline]:
    """Um headline por linha; `***` no início marca destaque e é removido."""
    if not path.is_file():
        raise DraftingError(f"Headlines file not found: {path}")
    headlines: list[Headline] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _STAR_PREFIX.match(line)
        bold = bool(m and len(m.group(1)) >= 3)
        text = _STAR_PREFIX.sub("", line, count=1).strip()
        if text:
            headlines.append(Headline(text, bold))
    if not headlines:
        raise DraftingError(f"Headlines file is empty: {path}")
    return headlines


def headlines_for_report(headlines: list[Headline]) -> list[dict]:
    """O formato que generate_fomc_report espera."""
    return [{"text": h.text, "bold": h.bold} for h in headlines]


def _pdf_text(path: Path) -> str:
    """Texto de todas as páginas, via pdfplumber. Isolado para os testes dublarem."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages).strip()


def read_bank_pdfs(folder: Path) -> tuple[list[BankSource], list[str]]:
    """Um BankSource por PDF; o nome do banco é o nome do arquivo.

    Devolve também a lista do que foi ignorado: arquivos que não são PDF e
    PDFs sem texto extraível.
    """
    if not folder.is_dir():
        raise DraftingError(f"Bank research folder not found: {folder} (expected 'bancos/')")
    files = sorted(p for p in folder.iterdir() if p.is_file())
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    if not pdfs:
        raise DraftingError(f"No PDF in bank research folder: {folder} ('bancos/')")
    ignored = [p.name for p in files if p.suffix.lower() != ".pdf"]
    sources: list[BankSource] = []
    for pdf in pdfs:
        text = _pdf_text(pdf)
        if not text:
            ignored.append(f"{pdf.name} (no extractable text)")
            continue
        sources.append(BankSource(pdf.stem.replace("_", " "), text))
    return sources, ignored


# --- reação de mercado ----------------------------------------------------------

# Como cada painel expressa variação: taxas em pontos-base (diferença × 100),
# inclinação em pontos-base (já está em bps), índices em %, VIX em pontos.
_CHANGE_KIND = {
    "UST_2Y": "rate_bp",
    "UST_10Y": "rate_bp",
    "OIS_1Y1Y": "rate_bp",
    "SPREAD_2S10S": "bp",
    "NASDAQ": "pct",
    "SPX": "pct",
    "RUSSELL": "pct",
    "DXY": "pct",
    "VIX": "pts",
}


@dataclass(frozen=True)
class PanelSnapshot:
    key: str
    label: str
    at_decision: str
    last: str
    change: str


@dataclass(frozen=True)
class MarketSnapshot:
    panels: list[PanelSnapshot]
    last_time: str  # HH:MM em Brasília


def _pt(number: str) -> str:
    """Notação brasileira: ponto de milhar e vírgula decimal; menos tipográfico."""
    return number.replace(",", "\x00").replace(".", ",").replace("\x00", ".").replace("-", "−")


def _change(kind: str, before: float, after: float) -> str:
    """Variação já em notação brasileira; `_pt` só no número, nunca no sufixo literal."""
    if kind == "rate_bp":
        return f"{_pt(f'{(after - before) * 100:+.1f}')} p.b."
    if kind == "bp":
        return f"{_pt(f'{after - before:+.1f}')} p.b."
    if kind == "pct":
        return f"{_pt(f'{(after / before - 1) * 100:+.1f}')}%"
    return f"{_pt(f'{after - before:+.2f}')} pts"


def market_snapshot(market_data: pd.DataFrame, decision_time: pd.Timestamp) -> MarketSnapshot:
    """Nível na decisão, último nível e variação por painel, já formatados."""
    from reports.fomc.core.word_export import MARKET_REACTION_PANELS

    if market_data is None or market_data.empty:
        raise DraftingError("No market data to summarize")
    panels: list[PanelSnapshot] = []
    for key, label, fmt, _pos in MARKET_REACTION_PANELS:
        if key not in market_data.columns:
            continue
        series = market_data[key].dropna()
        if series.empty:
            continue
        before_series = series[series.index <= decision_time]
        before = float(before_series.iloc[-1]) if not before_series.empty else float(series.iloc[0])
        after = float(series.iloc[-1])
        panels.append(
            PanelSnapshot(
                key=key,
                label=label,
                at_decision=_pt(fmt.format(before)),
                last=_pt(fmt.format(after)),
                change=_change(_CHANGE_KIND.get(key, "pts"), before, after),
            )
        )
    if not panels:
        raise DraftingError("No market panel available to summarize")
    last_time = market_data.dropna(how="all").index[-1].strftime("%H:%M")
    return MarketSnapshot(panels=panels, last_time=last_time)


def format_market(snapshot: MarketSnapshot) -> str:
    """Uma linha por painel, para o bloco REAÇÃO DE MERCADO da mensagem."""
    lines = [f"Último dado: {snapshot.last_time} (Brasília)"]
    for p in snapshot.panels:
        lines.append(f"{p.label}: {p.last} (na decisão {p.at_decision}; {p.change})")
    return "\n".join(lines)
