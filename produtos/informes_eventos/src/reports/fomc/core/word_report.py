"""
Gerador de relatório Word para reuniões do FOMC.

Gera o documento .docx "Mesa de Investimentos / Depin - Reunião do FOMC"
usando o .docx mais recente como template base (preserva header/footer/estilos),
limpa o conteúdo e preenche programaticamente.
"""

import logging
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

logger = logging.getLogger(__name__)

# === Constantes ===
TEMPLATE_SOURCE = Path(
    r"c:/Users/mmart/OneDrive/BCB/dirin/15_informes/fomc/"
    r"Mesa de Investimentos - FOMC_20260128.docx"
)
FONT_NAME = "Aptos"
TITLE_SIZE = Pt(14)
BODY_SIZE = Pt(11)
IMAGE_WIDTH = Cm(15)

# Margens do template
MARGIN_LEFT = Cm(1.7)
MARGIN_RIGHT = Cm(1.7)
MARGIN_TOP = Cm(1.0)
MARGIN_BOTTOM = Cm(0.85)

# Cores para tabela SEP
HAWKISH_COLOR = "FFFF00"  # Amarelo
DOVISH_COLOR = "00B0F0"   # Azul

# Mapeamento de meses para português (abreviado)
MESES_PTBR = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

# Meses das reuniões SEP anteriores (ordem reversa)
SEP_MONTHS = [3, 6, 9, 12]

# Indicadores e direção hawkish
# True = valor maior é hawkish; False = valor maior é dovish
HAWKISH_WHEN_UP: dict[str, bool] = {
    "Change in real GDP": True,        # PIB maior → hawkish (economia forte)
    "Unemployment rate": False,        # Desemprego maior → dovish
    "PCE inflation": True,             # Inflação maior → hawkish
    "Core PCE inflation": True,        # Core PCE maior → hawkish
    "Federal funds rate": True,        # Taxa maior → hawkish
}


def _load_template(template_path: Path | str | None = None) -> Document:
    """Abre o .docx de referência, limpa parágrafos mantendo header/footer/styles."""
    template_path = Path(template_path) if template_path else TEMPLATE_SOURCE

    if not template_path.exists():
        logger.warning(
            f"Template não encontrado: {template_path}. Criando documento em branco."
        )
        return _create_blank_document()

    logger.info(f"Carregando template: {template_path}")
    doc = Document(str(template_path))

    # Limpa todos os parágrafos do body (mantém headers/footers)
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:p") or child.tag == qn("w:tbl"):
            body.remove(child)

    # Ajustar margens
    for section in doc.sections:
        section.left_margin = MARGIN_LEFT
        section.right_margin = MARGIN_RIGHT
        section.top_margin = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM

    return doc


def _create_blank_document() -> Document:
    """Cria documento em branco com margens e fonte padrão."""
    doc = Document()
    for section in doc.sections:
        section.left_margin = MARGIN_LEFT
        section.right_margin = MARGIN_RIGHT
        section.top_margin = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM

    style = doc.styles["Normal"]
    font = style.font
    font.name = FONT_NAME
    font.size = BODY_SIZE
    return doc


def _set_run_font(run, size=None, bold=False, italic=False, name=None):
    """Aplica fonte a um run."""
    run.font.name = name or FONT_NAME
    if size:
        run.font.size = size
    run.bold = bold
    run.italic = italic


def _add_title(doc: Document, meeting_date: str) -> None:
    """Adiciona título centrado: 'Mesa de Investimentos / Depin' + data."""
    dt = pd.to_datetime(meeting_date, format="%Y%m%d")
    date_str = f"{dt.day:02d}/{dt.month:02d}/{dt.year}"

    # Linha 1: Mesa de Investimentos / Depin
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run("Mesa de Investimentos / Depin")
    _set_run_font(run, size=TITLE_SIZE, bold=True)

    # Linha 2: Reunião do FOMC – DD/MM/YYYY
    para2 = doc.add_paragraph()
    para2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = para2.add_run(f"Reunião do FOMC – {date_str}")
    _set_run_font(run2, size=TITLE_SIZE, bold=True)

    # Espaçamento
    doc.add_paragraph()


def _add_summary(doc: Document, summary_text: str) -> None:
    """Adiciona parágrafos de resumo justificados."""
    for paragraph_text in summary_text.strip().split("\n\n"):
        paragraph_text = paragraph_text.strip()
        if not paragraph_text:
            continue
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = para.add_run(paragraph_text)
        _set_run_font(run, size=BODY_SIZE)


def _add_headlines(doc: Document, headlines: list[dict]) -> None:
    """Adiciona headlines Bloomberg. Bold = destaque, normal = secundário."""
    for headline in headlines:
        para = doc.add_paragraph()
        text = headline.get("text", "")
        is_bold = headline.get("bold", False)
        run = para.add_run(text)
        _set_run_font(run, size=BODY_SIZE, bold=is_bold)


def _add_numbered_heading(doc: Document, number: int, title: str) -> None:
    """Adiciona heading numerado tipo 'List Paragraph'."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = para.add_run(f"{number}. {title}")
    _set_run_font(run, size=TITLE_SIZE, bold=True)

    # Espaçamento antes
    pf = para.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)


def _add_image(doc: Document, image_path: str | Path, width=None) -> None:
    """Insere imagem centralizada."""
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning(f"Imagem não encontrada: {image_path}")
        para = doc.add_paragraph()
        run = para.add_run(f"[Imagem não encontrada: {image_path.name}]")
        _set_run_font(run, size=BODY_SIZE, italic=True)
        return

    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.add_picture(str(image_path), width=width or IMAGE_WIDTH)


def _apply_cell_shading(cell, hex_color: str) -> None:
    """Aplica cor de fundo a uma célula de tabela."""
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_text(cell, text: str, bold=False, italic=False, size=None, align=None):
    """Define texto de uma célula com formatação."""
    cell.text = ""
    para = cell.paragraphs[0]
    if align:
        para.alignment = align
    run = para.add_run(str(text))
    _set_run_font(run, size=size or BODY_SIZE, bold=bold, italic=italic)


def _add_sep_section(
    doc: Document,
    dot_plot_path: str | Path | None,
    sep_current: pd.DataFrame,
    sep_prior: pd.DataFrame | None,
    prior_meeting_label: str | None,
    current_ct: pd.DataFrame | None = None,
    prior_ct: pd.DataFrame | None = None,
    include_ct: bool = False,
) -> None:
    """Adiciona seção SEP: dot plot screenshot + tabela Word nativa.

    Args:
        doc: Documento Word.
        dot_plot_path: Screenshot do dot plot.
        sep_current: DataFrame com medianas atuais.
        sep_prior: DataFrame com medianas anteriores.
        prior_meeting_label: Label da reunião anterior.
        current_ct: DataFrame com Central Tendency atual.
        prior_ct: DataFrame com Central Tendency anterior.
        include_ct: Se True, inclui colunas de CT na tabela.
    """
    from .calculations import classify_change_direction

    heading_number = 1

    # 1. Dot plot screenshot
    if dot_plot_path:
        _add_numbered_heading(doc, heading_number, "Projeções da Fed Fund (dots)")
        _add_image(doc, dot_plot_path)
        heading_number += 1

    # 2. Tabela SEP nativa
    _add_numbered_heading(doc, heading_number, "Novas Projeções Econômicas")

    if sep_current is None or sep_current.empty:
        para = doc.add_paragraph()
        run = para.add_run("[Dados de projeções não disponíveis]")
        _set_run_font(run, size=BODY_SIZE, italic=True)
        return

    # Extrair anos do DataFrame (colunas numéricas)
    year_cols = [c for c in sep_current.columns if c not in ("Variable",) and str(c).isdigit()]
    longer_run = "Longer run" if "Longer run" in sep_current.columns else None
    median_data_cols = year_cols + ([longer_run] if longer_run else [])

    # Determinar se CT será incluído
    show_ct = include_ct and current_ct is not None and not current_ct.empty
    ct_data_cols = median_data_cols if show_ct else []

    n_median_cols = len(median_data_cols)
    n_ct_cols = len(ct_data_cols)
    n_total_cols = 1 + n_median_cols + n_ct_cols  # Variable + Mediana + CT

    variables = sep_current["Variable"].tolist()

    # Calcular número de linhas: 2 header rows + (current + prior) por variável
    has_prior = sep_prior is not None and not sep_prior.empty
    rows_per_var = 2 if has_prior else 1
    n_rows = 2 + len(variables) * rows_per_var

    table = doc.add_table(rows=n_rows, cols=n_total_cols)
    try:
        table.style = "Table Grid"
    except KeyError:
        pass  # Template sem estilo "Table Grid" — usa estilo padrão

    # Header row 1: Variable | Mediana (merged) | Tendência Central (merged)
    _set_cell_text(
        table.rows[0].cells[0], "Variable",
        bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
    )
    _set_cell_text(
        table.rows[0].cells[1], "Mediana",
        bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
    )
    if n_median_cols > 1:
        for i in range(2, 1 + n_median_cols):
            table.rows[0].cells[1].merge(table.rows[0].cells[i])

    if show_ct:
        ct_start = 1 + n_median_cols
        _set_cell_text(
            table.rows[0].cells[ct_start], "Tendência Central",
            bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
        )
        if n_ct_cols > 1:
            for i in range(ct_start + 1, ct_start + n_ct_cols):
                table.rows[0].cells[ct_start].merge(table.rows[0].cells[i])

    # Header row 2: empty | year1 | year2 | ... | LR | year1 | year2 | ... | LR
    _set_cell_text(table.rows[1].cells[0], "", size=BODY_SIZE)
    for j, col_name in enumerate(median_data_cols):
        display_name = "LR" if col_name == "Longer run" else str(col_name)
        _set_cell_text(
            table.rows[1].cells[1 + j], display_name,
            bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
        )

    if show_ct:
        for j, col_name in enumerate(ct_data_cols):
            display_name = "LR" if col_name == "Longer run" else str(col_name)
            _set_cell_text(
                table.rows[1].cells[1 + n_median_cols + j], display_name,
                bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
            )

    # Shading for header rows
    for j in range(n_total_cols):
        _apply_cell_shading(table.rows[0].cells[j], "D9E2F3")
        _apply_cell_shading(table.rows[1].cells[j], "D9E2F3")

    # Data rows
    row_idx = 2
    prior_label = prior_meeting_label or "Prior projection"

    for _, var_row in sep_current.iterrows():
        variable = var_row["Variable"]

        # Current row (bold)
        _set_cell_text(
            table.rows[row_idx].cells[0], variable,
            bold=True, size=BODY_SIZE,
        )

        # Median columns
        for j, col in enumerate(median_data_cols):
            val = var_row.get(col)
            text = f"{val:.1f}" if pd.notna(val) else "—"
            _set_cell_text(
                table.rows[row_idx].cells[1 + j], text,
                bold=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
            )

            # Color-coding: comparar com prior
            if has_prior and pd.notna(val):
                prior_row = sep_prior[sep_prior["Variable"] == variable]
                if not prior_row.empty:
                    prior_val = prior_row[col].values[0] if col in prior_row.columns else None
                    if pd.notna(prior_val):
                        change = val - prior_val
                        if abs(change) > 0.001:
                            direction = classify_change_direction(variable, change)
                            if direction == "hawkish":
                                _apply_cell_shading(
                                    table.rows[row_idx].cells[1 + j], HAWKISH_COLOR
                                )
                            elif direction == "dovish":
                                _apply_cell_shading(
                                    table.rows[row_idx].cells[1 + j], DOVISH_COLOR
                                )

        # CT columns
        if show_ct:
            ct_var_row = current_ct[current_ct["Variable"] == variable]
            for j, col in enumerate(ct_data_cols):
                if not ct_var_row.empty and col in ct_var_row.columns:
                    val = ct_var_row[col].values[0]
                    text = str(val) if val is not None and str(val) != "nan" else "—"
                else:
                    text = "—"
                _set_cell_text(
                    table.rows[row_idx].cells[1 + n_median_cols + j], text,
                    bold=True, size=Pt(9), align=WD_ALIGN_PARAGRAPH.CENTER,
                )

        row_idx += 1

        # Prior row (italic)
        if has_prior:
            prior_var_row = sep_prior[sep_prior["Variable"] == variable]
            _set_cell_text(
                table.rows[row_idx].cells[0], f"  {prior_label}",
                italic=True, size=BODY_SIZE,
            )

            # Prior medians
            for j, col in enumerate(median_data_cols):
                if not prior_var_row.empty and col in prior_var_row.columns:
                    pval = prior_var_row[col].values[0]
                    text = f"{pval:.1f}" if pd.notna(pval) else "—"
                else:
                    text = "—"
                _set_cell_text(
                    table.rows[row_idx].cells[1 + j], text,
                    italic=True, size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER,
                )

            # Prior CT
            if show_ct and prior_ct is not None and not prior_ct.empty:
                pct_var_row = prior_ct[prior_ct["Variable"] == variable]
                for j, col in enumerate(ct_data_cols):
                    if not pct_var_row.empty and col in pct_var_row.columns:
                        val = pct_var_row[col].values[0]
                        text = str(val) if val is not None and str(val) != "nan" else "—"
                    else:
                        text = "—"
                    _set_cell_text(
                        table.rows[row_idx].cells[1 + n_median_cols + j], text,
                        italic=True, size=Pt(9), align=WD_ALIGN_PARAGRAPH.CENTER,
                    )
            elif show_ct:
                for j in range(n_ct_cols):
                    _set_cell_text(
                        table.rows[row_idx].cells[1 + n_median_cols + j], "—",
                        italic=True, size=Pt(9), align=WD_ALIGN_PARAGRAPH.CENTER,
                    )

            row_idx += 1

    # Legenda
    legend = doc.add_paragraph()
    legend.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = legend.paragraph_format
    pf.space_before = Pt(6)

    run_label = legend.add_run("LEGENDA: ")
    _set_run_font(run_label, size=Pt(9), bold=True)

    run_hawk = legend.add_run(" Hawkish ")
    _set_run_font(run_hawk, size=Pt(9), bold=True)
    rpr = run_hawk._r.get_or_add_rPr()
    highlight = OxmlElement("w:highlight")
    highlight.set(qn("w:val"), "yellow")
    rpr.append(highlight)

    run_space = legend.add_run("  ")
    _set_run_font(run_space, size=Pt(9))

    run_dove = legend.add_run(" Dovish ")
    _set_run_font(run_dove, size=Pt(9), bold=True)
    rpr2 = run_dove._r.get_or_add_rPr()
    highlight2 = OxmlElement("w:highlight")
    highlight2.set(qn("w:val"), "cyan")
    rpr2.append(highlight2)


def _add_presser_section(doc: Document, presser_headlines: list[dict]) -> None:
    """Adiciona destaques da coletiva do Powell."""
    if not presser_headlines:
        return
    _add_numbered_heading(doc, 0, "Destaques da Coletiva")  # número ajustado no generate
    _add_headlines(doc, presser_headlines)


def _add_market_reaction(doc: Document, screenshot_path: str | Path) -> None:
    """Insere screenshot de reação de mercado."""
    _add_image(doc, screenshot_path)


def _add_bank_comments(doc: Document, comments: dict[str, str]) -> None:
    """Adiciona comentários dos bancos. Nome em bold + texto normal."""
    for bank_name, comment_text in comments.items():
        para = doc.add_paragraph()

        # Nome do banco em bold
        run_name = para.add_run(f"{bank_name}: ")
        _set_run_font(run_name, size=BODY_SIZE, bold=True)

        # Processar texto com **bold** inline
        _add_text_with_bold(para, comment_text)


def _add_text_with_bold(para, text: str) -> None:
    """Adiciona texto ao parágrafo processando marcadores **bold**."""
    import re

    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            _set_run_font(run, size=BODY_SIZE, bold=True)
        else:
            run = para.add_run(part)
            _set_run_font(run, size=BODY_SIZE)


def _add_footer_text(doc: Document, mesa_comment: str = "") -> None:
    """Adiciona rodapé 'Mesa de Investimentos'."""
    doc.add_paragraph()  # espaçamento

    if mesa_comment:
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = para.add_run(mesa_comment)
        _set_run_font(run, size=BODY_SIZE)
        doc.add_paragraph()

    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = para.add_run("Mesa de Investimentos")
    _set_run_font(run, size=BODY_SIZE, bold=True)


def generate_fomc_report(
    meeting_date: str,
    summary_text: str,
    headlines: list[dict],
    market_reaction_path: str | Path,
    bank_comments: dict[str, str],
    # Opcionais (só SEP):
    dot_plot_path: str | Path | None = None,
    sep_current: pd.DataFrame | None = None,
    sep_prior: pd.DataFrame | None = None,
    prior_meeting_label: str | None = None,
    presser_headlines: list[dict] | None = None,
    # Novos parâmetros CT:
    current_ct: pd.DataFrame | None = None,
    prior_ct: pd.DataFrame | None = None,
    include_ct: bool = False,
    mesa_comment: str = "",
    template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Gera o relatório Word completo do FOMC.

    Args:
        meeting_date: Data da reunião (YYYYMMDD).
        summary_text: Texto de resumo em pt-BR.
        headlines: Lista de headlines Bloomberg.
            Cada item: {"text": "*FED...", "bold": True/False}
        market_reaction_path: Caminho para screenshot de reação de mercado.
        bank_comments: Dict banco → comentário.
        dot_plot_path: Screenshot do dot plot (só SEP).
        sep_current: DataFrame com projeções atuais (só SEP).
        sep_prior: DataFrame com projeções anteriores (só SEP).
        prior_meeting_label: Label da reunião anterior (ex: "September projection").
        presser_headlines: Headlines da coletiva do Powell (opcional).
        current_ct: DataFrame com Central Tendency atual (só SEP).
        prior_ct: DataFrame com Central Tendency anterior (só SEP).
        include_ct: Se True, inclui colunas de CT na tabela SEP.
        mesa_comment: Comentário da Mesa de Investimentos.
        template_path: Caminho para template .docx (usa padrão se None).
        output_path: Caminho de saída (gera automaticamente se None).

    Returns:
        Path do arquivo .docx gerado.
    """
    doc = _load_template(template_path)

    is_sep = sep_current is not None and not sep_current.empty

    # === CAPA ===
    _add_title(doc, meeting_date)
    _add_summary(doc, summary_text)

    if headlines:
        doc.add_paragraph()
        _add_headlines(doc, headlines)

    # === SEÇÕES SEP (se aplicável) ===
    section_number = 1

    if is_sep:
        doc.add_page_break()
        _add_sep_section(
            doc,
            dot_plot_path=dot_plot_path,
            sep_current=sep_current,
            sep_prior=sep_prior,
            prior_meeting_label=prior_meeting_label,
            current_ct=current_ct,
            prior_ct=prior_ct,
            include_ct=include_ct,
        )

        # Destaques da coletiva
        if presser_headlines:
            doc.add_paragraph()
            next_num = 3 if dot_plot_path else 2
            _add_numbered_heading(doc, next_num, "Destaques da Coletiva")
            _add_headlines(doc, presser_headlines)

    # === REAÇÃO DE MERCADO ===
    doc.add_page_break()
    _add_numbered_heading(doc, section_number, "Reação do Mercado")
    section_number += 1
    _add_market_reaction(doc, market_reaction_path)

    # === COMENTÁRIOS DOS BANCOS ===
    if bank_comments:
        doc.add_page_break()
        _add_numbered_heading(doc, section_number, "Comentários dos Bancos")
        section_number += 1
        _add_bank_comments(doc, bank_comments)

    # === RODAPÉ ===
    _add_footer_text(doc, mesa_comment)

    # === SALVAR ===
    if output_path is None:
        output_dir = Path("output/reports/fomc")
        output_dir.mkdir(parents=True, exist_ok=True)
        date_clean = meeting_date.replace("-", "")
        output_path = output_dir / f"Mesa de Investimentos - FOMC_{date_clean}.docx"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    doc.save(str(output_path))
    logger.info(f"Relatório salvo em: {output_path}")

    return output_path
