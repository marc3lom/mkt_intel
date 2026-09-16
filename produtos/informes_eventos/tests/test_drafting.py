"""As etapas de modelo do informe do FOMC, sem rede, sem Bloomberg e sem `claude`."""

import os
import re
import time

import pandas as pd
import pytest

from reports import _modelo
from reports.fomc.core import drafting
from reports.fomc.core.data_loader import _TZ_BRT
from reports.fomc.core.drafting import (
    BankSource,
    DraftingError,
    Headline,
    MeetingInputs,
    block,
    build_message,
    draft_bank_comments,
    draft_summary,
    extract_fenced_block,
    format_market,
    format_sep_table,
    format_statement,
    headlines_for_report,
    market_snapshot,
    parse_bank_sections,
    pick_summary,
    read_bank_pdfs,
    read_headlines,
    read_presser,
    review_report,
    run_stage,
)


class TestDayFolders:
    def test_day_and_output_folders_anchor_on_project_root(self):
        assert (
            drafting.day_folder("20260916") == drafting.PROJECT_ROOT / "input" / "fomc" / "20260916"
        )
        assert (drafting.PROJECT_ROOT / "pyproject.toml").is_file()

    def test_output_folder_is_created(self, monkeypatch, tmp_path):
        monkeypatch.setattr(drafting, "PROJECT_ROOT", tmp_path)
        out = drafting.output_folder("20260916")
        assert out == tmp_path / "output" / "reports" / "fomc" / "20260916"
        assert out.is_dir()


class TestReadHeadlines:
    def test_triple_star_marks_bold_and_is_removed(self, tmp_path):
        p = tmp_path / "headlines.txt"
        p.write_text("*** Fed holds\n\n* Fed says X\nPlain line\n", encoding="utf-8")
        assert read_headlines(p) == [
            Headline("Fed holds", True),
            Headline("Fed says X", False),
            Headline("Plain line", False),
        ]

    def test_missing_or_empty_file_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="headlines.txt"):
            read_headlines(tmp_path / "headlines.txt")
        (tmp_path / "headlines.txt").write_text("\n\n", encoding="utf-8")
        with pytest.raises(DraftingError, match="empty"):
            read_headlines(tmp_path / "headlines.txt")

    def test_headlines_for_report_shape(self):
        assert headlines_for_report([Headline("a", True)]) == [{"text": "a", "bold": True}]


class TestReadBankPdfs:
    def test_names_from_filenames_and_ignored_files(self, tmp_path, monkeypatch):
        """Nome do banco = arquivo sem extensão, sublinhado vira espaço; não-PDF é ignorado."""
        (tmp_path / "Goldman_Sachs.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "notas.docx").write_bytes(b"x")

        monkeypatch.setattr(drafting, "_pdf_text", lambda p: "texto do research")
        sources, ignored = read_bank_pdfs(tmp_path)
        assert sources == [BankSource("Goldman Sachs", "texto do research")]
        assert ignored == ["notas.docx"]

    def test_pdf_without_text_is_reported_not_returned(self, tmp_path, monkeypatch):
        (tmp_path / "JPM.pdf").write_bytes(b"%PDF-1.4 fake")
        monkeypatch.setattr(drafting, "_pdf_text", lambda p: "")
        sources, ignored = read_bank_pdfs(tmp_path)
        assert sources == []
        assert ignored == ["JPM.pdf (no extractable text)"]

    def test_no_pdf_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="bancos"):
            read_bank_pdfs(tmp_path)
        with pytest.raises(DraftingError, match="bancos"):
            read_bank_pdfs(tmp_path / "nao-existe")


def _intraday() -> pd.DataFrame:
    idx = pd.date_range("2026-09-16 14:00", "2026-09-16 16:00", freq="30min", tz=_TZ_BRT)
    # 5 pontos: 14:00, 14:30, 15:00, 15:30, 16:00
    return pd.DataFrame(
        {
            "SPX": [6000.0, 6000.0, 6000.0, 5970.0, 5940.0],
            "UST_2Y": [4.000, 4.000, 4.000, 4.100, 4.130],
            "UST_10Y": [4.400, 4.400, 4.400, 4.430, 4.440],
            "SPREAD_2S10S": [40.0, 40.0, 40.0, 33.0, 31.0],
            "DXY": [100.0, 100.0, 100.0, 100.3, 100.6],
            "VIX": [15.0, 15.0, 15.0, 16.5, 17.0],
        },
        index=idx,
    )


class TestMarketSnapshot:
    def test_levels_and_changes_by_panel_kind(self):
        """Nível na decisão (último ≤ 15:00), último nível e variação no tipo de cada painel."""
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        snap = market_snapshot(_intraday(), decision)
        by_key = {p.key: p for p in snap.panels}
        assert snap.last_time == "16:00"
        assert by_key["SPX"].at_decision == "6.000" and by_key["SPX"].last == "5.940"
        assert by_key["SPX"].change == "−1,0%"
        assert by_key["UST_2Y"].change == "+13,0 p.b."
        assert by_key["UST_10Y"].change == "+4,0 p.b."
        assert by_key["SPREAD_2S10S"].change == "−9,0 p.b."
        assert by_key["DXY"].change == "+0,6%"
        assert by_key["VIX"].change == "+2,00 pts"
        assert set(by_key) == {"SPX", "UST_2Y", "UST_10Y", "SPREAD_2S10S", "DXY", "VIX"}

    def test_format_market_is_one_line_per_panel_with_comma_decimals(self):
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        text = format_market(market_snapshot(_intraday(), decision))
        assert text.splitlines()[0] == "Último dado: 16:00 (Brasília)"
        assert "UST 2 Anos (%): 4,130 (na decisão 4,000; +13,0 p.b.)" in text
        assert "4.130" not in text

    def test_empty_frame_raises(self):
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        with pytest.raises(DraftingError, match="market"):
            market_snapshot(pd.DataFrame(), decision)

    def test_all_panels_starting_after_decision_raises(self):
        """Sem tick antes da decisão em painel nenhum, o erro de painel ausente dispara."""
        decision = pd.Timestamp("2026-09-16 13:00", tz=_TZ_BRT)  # antes de todos os ticks
        with pytest.raises(DraftingError, match="panel"):
            market_snapshot(_intraday(), decision)

    def test_panel_missing_before_tick_is_skipped_others_unaffected(self):
        """Painel sem tick antes da decisão some do snapshot — não pega o 1º tick pós."""
        data = _intraday()
        # VIX só passa a existir depois da decisão (15:00).
        data.loc[data.index <= pd.Timestamp("2026-09-16 14:30", tz=_TZ_BRT), "VIX"] = float("nan")
        decision = pd.Timestamp("2026-09-16 14:00", tz=_TZ_BRT)
        snap = market_snapshot(data, decision)
        by_key = {p.key: p for p in snap.panels}
        assert "VIX" not in by_key
        assert "SPX" in by_key


@pytest.fixture
def prompts(tmp_path, monkeypatch):
    """Guia e prompts sintéticos, para a montagem não depender dos reais."""
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "00_guia_de_estilo.md").write_text("GUIA", encoding="utf-8")
    (d / "01_resumo.md").write_text("PROMPT RESUMO", encoding="utf-8")
    (d / "02_bancos.md").write_text("PROMPT BANCOS", encoding="utf-8")
    (d / "03_revisao.md").write_text("PROMPT REVISAO", encoding="utf-8")
    monkeypatch.setattr(drafting, "PROMPTS_DIR", d)
    return d


@pytest.fixture
def model(monkeypatch):
    """Dublê do backend: devolve a resposta escolhida e guarda a mensagem recebida."""
    state = {"messages": []}

    def install(response: str):
        class Fake:
            name = "fake"

            def run(self, message, *, stage, model):
                state["messages"].append((stage, message))
                return response

        monkeypatch.setitem(_modelo.BACKENDS, "fake", Fake)
        monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "fake")
        return state

    return install


class TestMeetingInputs:
    def test_defaults_are_independent_per_instance(self):
        """`field(default_factory=list)`: uma instância não compartilha a lista da outra."""
        a = MeetingInputs(meeting_date="20260916")
        b = MeetingInputs(meeting_date="20260917")
        a.headlines.append(Headline("x", False))
        assert a.headlines == [Headline("x", False)]
        assert b.headlines == []
        assert a.is_sep is False
        assert a.statement is None
        assert a.market is None


class TestBlocks:
    def test_block_marks_missing(self):
        assert block("STATEMENT", "texto") == "=== STATEMENT ===\ntexto"
        assert block("STATEMENT", None) == "=== STATEMENT === (ausente)"
        assert block("STATEMENT", "  ") == "=== STATEMENT === (ausente)"

    def test_format_statement_in_portuguese_with_comma(self):
        s = {
            "decision": "hold",
            "target_rate_low": 3.5,
            "target_rate_high": 3.75,
            "unanimous": False,
            "dissenters": ["Stephen Miran"],
            "key_phrases": ["Inflation remains elevated"],
        }
        text = format_statement(s)
        assert "decisão: manutenção" in text
        assert "faixa: 3,50%–3,75%" in text
        assert "unânime: não; dissidentes: Stephen Miran" in text
        assert "Inflation remains elevated" in text

    def test_format_sep_table_with_prior_and_missing_year(self):
        cur = pd.DataFrame(
            {"Variable": ["Change in real GDP"], "2026": [1.8], "2029": [2.0], "Longer run": [1.8]}
        )
        prior = pd.DataFrame(
            {
                "Variable": ["Change in real GDP"],
                "2026": [1.4],
                "2029": [float("nan")],
                "Longer run": [1.8],
            }
        )
        text = format_sep_table(cur, prior, "June projection")
        assert text.splitlines()[0] == "| Variável | 2026 | 2029 | Longer run |"
        assert "| Change in real GDP | 1,8 (1,4) | 2,0 (—) | 1,8 (1,8) |" in text
        assert "June projection" in text

    def test_build_message_order_guide_prompt_blocks(self, prompts):
        msg = build_message("01_resumo.md", [("A", "1"), ("B", None)])
        assert msg.index("GUIA") < msg.index("PROMPT RESUMO") < msg.index("=== A ===")
        assert "=== B === (ausente)" in msg


class TestResponses:
    def test_last_fenced_block(self):
        r = "auditoria\n```\nprimeiro\n```\nmais\n```markdown\nsegundo\nlinha\n```\n"
        assert extract_fenced_block(r) == "segundo\nlinha"

    def test_no_block_raises(self):
        with pytest.raises(DraftingError, match="fenced"):
            extract_fenced_block("sem bloco")

    def test_fenced_block_with_digits_and_hyphen_in_tag(self):
        r = "auditoria\n```md-2\ntexto final\n```\n"
        assert extract_fenced_block(r) == "texto final"

    def test_empty_fenced_block_raises(self):
        with pytest.raises(DraftingError, match="empty"):
            extract_fenced_block("auditoria\n```\n\n```\n")

    def test_inline_fence_in_audit_does_not_fool_the_anchor(self):
        """Um ``` no meio de uma linha da auditoria não conta como fronteira de bloco."""
        r = "## Bloco 1\n[SUPORTADA] o texto diz ```3,50%```\nfim\n```\ntexto final\n```\n"
        assert extract_fenced_block(r) == "texto final"

    def test_bank_sections_in_order(self):
        text = "## Goldman Sachs\nParágrafo GS.\n\n## JPM\nParágrafo JPM.\n"
        assert parse_bank_sections(text) == {
            "Goldman Sachs": "Parágrafo GS.",
            "JPM": "Parágrafo JPM.",
        }


class TestRunStage:
    def test_writes_full_response_and_returns_block(self, model, tmp_path):
        model("audit\n```\ntexto final\n```")
        dest = tmp_path / "out" / "resumo_decisao.md"
        assert run_stage("resumo", "mensagem", dest) == "texto final"
        assert dest.read_text(encoding="utf-8").startswith("audit")

    def test_missing_input_mark_raises_and_writes_nothing(self, model, tmp_path):
        model(f"{_modelo.MISSING_INPUT_MARK}: headlines\n```\nx\n```")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError, match="headlines"):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_missing_input_mark_after_heading_line_is_still_detected(self, model, tmp_path):
        """A marca não precisa abrir a resposta — só estar perto do início."""
        model(f"## Auditoria\n{_modelo.MISSING_INPUT_MARK}: headlines\n```\nx\n```")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError, match="headlines"):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_no_fenced_block_raises_and_writes_nothing(self, model, tmp_path):
        model("só auditoria")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_empty_fenced_block_raises_and_writes_nothing(self, model, tmp_path):
        model("audit\n```\n\n```")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError, match="empty"):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_model_error_becomes_drafting_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "nao-existe")
        with pytest.raises(DraftingError, match="nao-existe"):
            run_stage("resumo", "m", tmp_path / "x.md")


class TestPromptFiles:
    @pytest.mark.parametrize(
        "name", ["00_guia_de_estilo.md", "01_resumo.md", "02_bancos.md", "03_revisao.md"]
    )
    def test_prompt_exists_and_has_version_header(self, name):
        path = drafting.PROMPTS_DIR / name
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("# ")
        assert "Versão" in text.splitlines()[2]

    def test_stage_prompts_demand_fenced_block(self):
        for name in ["01_resumo.md", "02_bancos.md", "03_revisao.md"]:
            text = (drafting.PROMPTS_DIR / name).read_text(encoding="utf-8")
            assert "bloco cercado" in text, name


def _inputs(is_sep=True) -> MeetingInputs:
    cur = pd.DataFrame({"Variable": ["PCE inflation"], "2026": [3.6]})
    prior = pd.DataFrame({"Variable": ["PCE inflation"], "2026": [2.7]})
    return MeetingInputs(
        meeting_date="20260916",
        statement_text="STATEMENT TEXT",
        statement={
            "decision": "hold",
            "target_rate_low": 3.5,
            "target_rate_high": 3.75,
            "unanimous": True,
            "dissenters": [],
            "key_phrases": [],
        },
        is_sep=is_sep,
        sep_medians=cur if is_sep else None,
        sep_prior=prior if is_sep else None,
        prior_label="June projection" if is_sep else None,
        headlines=[Headline("Fed holds", True)],
        market=None,
    )


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(drafting, "PROJECT_ROOT", tmp_path)
    return tmp_path / "output" / "reports" / "fomc" / "20260916"


class TestDraftSummary:
    def test_decision_stage_message_and_output(self, prompts, model, out):
        state = model("## Auditoria\nok\n```\nParágrafo 1.\n\nParágrafo 2.\n```")
        text = draft_summary(_inputs())
        assert text == "Parágrafo 1.\n\nParágrafo 2."
        assert (out / "resumo_decisao.md").is_file()
        stage, msg = state["messages"][0]
        assert stage == "resumo"
        assert "=== MOMENTO ===\ndecisão" in msg
        assert "=== STATEMENT ===\nSTATEMENT TEXT" in msg
        assert "=== DECISÃO (parse) ===" in msg
        assert "=== SEP: MEDIANAS ATUAIS vs ANTERIORES (June projection) ===" in msg
        assert "| PCE inflation | 3,6 (2,7) |" in msg
        assert "=== HEADLINES BLOOMBERG ===\n*** Fed holds" in msg
        assert "=== REAÇÃO DE MERCADO === (ausente)" in msg
        assert "RESUMO DA DECISÃO" not in msg

    def test_no_sep_meeting_has_no_sep_block(self, prompts, model, out):
        state = model("```\nx\n```")
        draft_summary(_inputs(is_sep=False))
        assert "=== SEP" not in state["messages"][0][1]

    def test_presser_stage_requires_previous_and_presser(self, prompts, model, out):
        model("```\nx\n```")
        with pytest.raises(DraftingError, match="previous"):
            draft_summary(_inputs(), stage="presser", presser_headlines=[Headline("a", False)])
        with pytest.raises(DraftingError, match="coletiva"):
            draft_summary(_inputs(), stage="presser", previous="texto")

    def test_presser_stage_message_and_output(self, prompts, model, out):
        state = model("```\nnovo\n```")
        text = draft_summary(
            _inputs(),
            stage="presser",
            previous="RESUMO ANTERIOR",
            presser_headlines=[Headline("Warsh says", False)],
        )
        assert text == "novo"
        assert (out / "resumo_coletiva.md").is_file()
        msg = state["messages"][0][1]
        assert "=== MOMENTO ===\ncoletiva" in msg
        assert "=== RESUMO DA DECISÃO ===\nRESUMO ANTERIOR" in msg
        assert "=== HEADLINES DA COLETIVA ===\nWarsh says" in msg

    def test_unknown_stage_raises(self, prompts, model, out):
        with pytest.raises(DraftingError, match="stage"):
            draft_summary(_inputs(), stage="outro")

    def test_decision_stage_without_headlines_refuses_before_model(self, prompts, model, out):
        state = model("```\nx\n```")
        inputs = _inputs()
        inputs.headlines = []
        with pytest.raises(DraftingError, match="headlines.txt"):
            draft_summary(inputs)
        assert state["messages"] == []


class TestReadPresser:
    def test_none_when_missing_list_when_present(self, tmp_path):
        assert read_presser(tmp_path) is None
        (tmp_path / "coletiva.txt").write_text("*** A\nB\n", encoding="utf-8")
        assert read_presser(tmp_path) == [Headline("A", True), Headline("B", False)]


class TestDraftBankComments:
    def test_one_block_per_source_and_dict_out(self, prompts, model, out):
        state = model("## Auditoria\n```\n## Goldman Sachs\nGS diz.\n\n## JPM\nJPM diz.\n```")
        result = draft_bank_comments(
            _inputs(), [BankSource("Goldman Sachs", "texto gs"), BankSource("JPM", "texto jpm")]
        )
        assert result == {"Goldman Sachs": "GS diz.", "JPM": "JPM diz."}
        assert (out / "bancos.md").is_file()
        msg = state["messages"][0][1]
        assert state["messages"][0][0] == "bancos"
        assert "=== RESEARCH: Goldman Sachs ===\ntexto gs" in msg
        assert msg.index("RESEARCH: Goldman Sachs") < msg.index("RESEARCH: JPM")

    def test_no_sources_raises_before_model(self, prompts, model, out):
        state = model("```\n## X\ny\n```")
        with pytest.raises(DraftingError, match="research"):
            draft_bank_comments(_inputs(), [])
        assert state["messages"] == []

    def test_bank_missing_from_response_raises_naming_it(self, prompts, model, out):
        model("## Auditoria\n```\n## Goldman Sachs\nGS diz.\n```")
        with pytest.raises(DraftingError, match="JPM"):
            draft_bank_comments(
                _inputs(),
                [BankSource("Goldman Sachs", "texto gs"), BankSource("JPM", "texto jpm")],
            )
        assert (out / "bancos.md").is_file()

    def test_no_section_at_all_raises(self, prompts, model, out):
        model("## Auditoria\n```\nsem seções aqui\n```")
        with pytest.raises(DraftingError, match="no '## Bank' section"):
            draft_bank_comments(_inputs(), [BankSource("Goldman Sachs", "texto gs")])


class TestReviewReport:
    def test_message_has_text_banks_and_facts(self, prompts, model, out):
        state = model("## Bloco 1\n[SUPORTADA] x\n```\ntexto corrigido\n```")
        text = review_report(
            _inputs(), "TEXTO", {"JPM": "JPM diz."}, presser_headlines=[Headline("W", False)]
        )
        assert text == "texto corrigido"
        assert (out / "revisao.md").is_file()
        stage, msg = state["messages"][0]
        assert stage == "revisao"
        assert "=== TEXTO PARA REVISÃO ===\nTEXTO" in msg
        assert "=== COMENTÁRIOS DOS BANCOS ===\n## JPM\nJPM diz." in msg
        assert "=== HEADLINES DA COLETIVA ===\nW" in msg
        assert "=== DECISÃO (parse) ===" in msg

    def test_empty_summary_raises(self, prompts, model, out):
        with pytest.raises(DraftingError, match="summary"):
            review_report(_inputs(), "  ")


class TestPickSummary:
    def test_auto_prefers_review_then_presser_then_decision(self, tmp_path):
        """Escritas na ordem real: decisão, coletiva, revisão — a última é sempre a mais nova."""
        (tmp_path / "resumo_decisao.md").write_text("texto\n```\nDECISAO\n```\n", encoding="utf-8")
        (tmp_path / "resumo_coletiva.md").write_text(
            "texto\n```\nCOLETIVA\n```\n", encoding="utf-8"
        )
        (tmp_path / "revisao.md").write_text("texto\n```\nREVISAO\n```\n", encoding="utf-8")
        text, path = pick_summary(tmp_path, "auto")
        assert text == "REVISAO"
        assert path == tmp_path / "revisao.md"

    def test_explicit_source_reads_only_its_file(self, tmp_path):
        (tmp_path / "revisao.md").write_text("```\nREVISAO\n```\n", encoding="utf-8")
        (tmp_path / "resumo_decisao.md").write_text("```\nDECISAO\n```\n", encoding="utf-8")
        text, path = pick_summary(tmp_path, "decisao")
        assert text == "DECISAO"
        assert path == tmp_path / "resumo_decisao.md"

    def test_unknown_source_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="SUMMARY_SOURCE"):
            pick_summary(tmp_path, "bogus")

    def test_missing_file_raises_mentioning_folder(self, tmp_path):
        with pytest.raises(DraftingError, match=re.escape(str(tmp_path))):
            pick_summary(tmp_path, "decisao")

    def test_auto_raises_when_lower_priority_file_is_newer(self, tmp_path):
        """resumo_decisao.md mais novo que revisao.md indica revisão desatualizada."""
        revisao = tmp_path / "revisao.md"
        decisao = tmp_path / "resumo_decisao.md"
        revisao.write_text("```\nREVISAO\n```\n", encoding="utf-8")
        decisao.write_text("```\nDECISAO\n```\n", encoding="utf-8")
        now = time.time()
        os.utime(revisao, (now, now))
        os.utime(decisao, (now + 10, now + 10))
        with pytest.raises(DraftingError, match="revisao.md") as exc:
            pick_summary(tmp_path, "auto")
        assert "resumo_decisao.md" in str(exc.value)

    def test_auto_passes_with_normal_order(self, tmp_path):
        """Arquivo escolhido mais novo que os de prioridade menor: sem alerta."""
        revisao = tmp_path / "revisao.md"
        decisao = tmp_path / "resumo_decisao.md"
        decisao.write_text("```\nDECISAO\n```\n", encoding="utf-8")
        now = time.time()
        os.utime(decisao, (now, now))
        revisao.write_text("```\nREVISAO\n```\n", encoding="utf-8")
        os.utime(revisao, (now + 10, now + 10))
        text, path = pick_summary(tmp_path, "auto")
        assert text == "REVISAO"
        assert path == revisao

    def test_explicit_source_never_checks_staleness(self, tmp_path):
        revisao = tmp_path / "revisao.md"
        decisao = tmp_path / "resumo_decisao.md"
        revisao.write_text("```\nREVISAO\n```\n", encoding="utf-8")
        decisao.write_text("```\nDECISAO\n```\n", encoding="utf-8")
        now = time.time()
        os.utime(revisao, (now, now))
        os.utime(decisao, (now + 10, now + 10))
        text, path = pick_summary(tmp_path, "revisao")
        assert text == "REVISAO"
        assert path == revisao


class TestReviewSource:
    def test_explicit_coletiva_and_decisao_pass_through(self, tmp_path):
        assert drafting.review_source(tmp_path, "coletiva") == "coletiva"
        assert drafting.review_source(tmp_path, "decisao") == "decisao"

    def test_auto_prefers_coletiva_when_present(self, tmp_path):
        (tmp_path / "resumo_coletiva.md").write_text("x", encoding="utf-8")
        assert drafting.review_source(tmp_path, "auto") == "coletiva"

    def test_auto_falls_back_to_decisao_when_absent(self, tmp_path):
        assert drafting.review_source(tmp_path, "auto") == "decisao"

    def test_revisao_behaves_like_auto(self, tmp_path):
        assert drafting.review_source(tmp_path, "revisao") == "decisao"
        (tmp_path / "resumo_coletiva.md").write_text("x", encoding="utf-8")
        assert drafting.review_source(tmp_path, "revisao") == "coletiva"

    def test_unknown_source_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="SUMMARY_SOURCE"):
            drafting.review_source(tmp_path, "bogus")
