"""Etapas de modelo do informe do FOMC: resumo, bancos e revisão.

Cada etapa monta uma mensagem com o guia de estilo, o prompt da etapa e os
insumos do dia em blocos rotulados, chama o backend de `reports._modelo`,
grava a resposta inteira em output/reports/fomc/<data>/ e devolve o último
bloco cercado, que é o que o notebook consome. Nada roda sozinho: cada etapa
é uma célula que o autor executa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from reports import _modelo

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


# --- insumos e mensagem --------------------------------------------------------


@dataclass
class MeetingInputs:
    """Tudo o que as etapas recebem; montado pelo notebook a partir das células anteriores."""

    meeting_date: str
    statement_text: str | None = None
    statement: dict | None = None
    is_sep: bool = False
    sep_medians: pd.DataFrame | None = None
    sep_prior: pd.DataFrame | None = None
    prior_label: str | None = None
    headlines: list[Headline] = field(default_factory=list)
    market: MarketSnapshot | None = None


def block(label: str, body: str | None) -> str:
    """Bloco rotulado; insumo ausente é marcado, nunca omitido, para o prompt reclamar."""
    if body is None or not str(body).strip():
        return f"=== {label} === (ausente)"
    return f"=== {label} ===\n{str(body).strip()}"


_DECISION_PT = {"hold": "manutenção", "cut": "corte", "hike": "alta"}


def _pct(value) -> str:
    return _pt(f"{float(value):.2f}%")


def format_statement(statement: dict) -> str:
    """O parse do statement em uma linha de fatos, em português e com vírgula decimal."""
    parts = [f"decisão: {_DECISION_PT.get(statement.get('decision'), 'não identificada')}"]
    low, high = statement.get("target_rate_low"), statement.get("target_rate_high")
    if low is not None and high is not None:
        parts.append(f"faixa: {_pct(low)}–{_pct(high)}")
    unanimous = statement.get("unanimous")
    if unanimous is True:
        parts.append("unânime: sim")
    elif unanimous is False:
        dissenters = ", ".join(statement.get("dissenters") or []) or "não listados"
        parts.append(f"unânime: não; dissidentes: {dissenters}")
    lines = ["; ".join(parts)]
    for phrase in statement.get("key_phrases") or []:
        lines.append(f"- {phrase}")
    return "\n".join(lines)


def _cell(value) -> str:
    return "—" if value is None or pd.isna(value) else _pt(f"{float(value):.1f}")


def format_sep_table(
    current: pd.DataFrame,
    prior: pd.DataFrame | None,
    prior_label: str | None,
) -> str:
    """Tabela markdown: mediana atual (anterior) por variável e ano, vírgula decimal."""
    years = [c for c in current.columns if c != "Variable"]
    label = prior_label or "Prior projection"
    lines = [
        "| Variável | " + " | ".join(years) + " |",
        "|---|" + "---|" * len(years),
    ]
    for _, row in current.iterrows():
        cells = []
        prior_row = None
        if prior is not None and not prior.empty:
            match = prior[prior["Variable"] == row["Variable"]]
            prior_row = match.iloc[0] if not match.empty else None
        for y in years:
            cur = _cell(row.get(y))
            if prior_row is None:
                cells.append(cur)
            else:
                cells.append(f"{cur} ({_cell(prior_row.get(y))})")
        lines.append(f"| {row['Variable']} | " + " | ".join(cells) + " |")
    lines.append(f"Entre parênteses: mediana da projeção anterior ({label}). — = sem projeção.")
    return "\n".join(lines)


def format_headlines(headlines: list[Headline]) -> str:
    return "\n".join(("*** " if h.bold else "") + h.text for h in headlines)


def _read_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.is_file():
        raise DraftingError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_message(prompt_file: str, blocks: list[tuple[str, str | None]]) -> str:
    """Guia de estilo, prompt da etapa, depois os blocos, nessa ordem, sempre."""
    parts = [_read_prompt(STYLE_GUIDE), _read_prompt(prompt_file)]
    parts += [block(label, body) for label, body in blocks]
    return "\n\n".join(parts) + "\n"


# --- resposta e execução -------------------------------------------------------

_FENCED = re.compile(r"```[^\n]*\n(.*?)\n```", re.DOTALL)


def extract_fenced_block(response: str) -> str:
    """O último bloco cercado da resposta é o que o notebook consome.

    Bloco vazio é erro, não string vazia: a etapa seguinte leria isso como
    saída válida e a falha passaria em silêncio.
    """
    blocks = _FENCED.findall(response)
    if not blocks:
        raise DraftingError("Model response has no fenced block")
    text = blocks[-1].strip()
    if not text:
        raise DraftingError("Model response has an empty fenced block")
    return text


_BANK_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_bank_sections(text: str) -> dict[str, str]:
    """Seções `## Banco` → {banco: parágrafo}, na ordem em que aparecem."""
    result: dict[str, str] = {}
    matches = list(_BANK_HEADING.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        if body:
            result[m.group(1)] = body
    return result


def run_stage(stage: str, message: str, destination: Path) -> str:
    """Chama o backend, valida a resposta, grava a resposta inteira, devolve o bloco.

    Não grava nada quando falha: um .md pela metade seria lido como bom.
    """
    try:
        response = _modelo.run(message, stage=stage)
    except _modelo.ModelError as e:
        raise DraftingError(str(e)) from e
    if response.lstrip().startswith(_modelo.MISSING_INPUT_MARK):
        first = response.strip().splitlines()[0]
        raise DraftingError(f"Stage {stage} refused: {first}")
    text = extract_fenced_block(response)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(response + "\n", encoding="utf-8")
    return text
