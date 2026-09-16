"""As etapas de modelo do informe do FOMC, sem rede, sem Bloomberg e sem `claude`."""

import pytest

from reports.fomc.core import drafting
from reports.fomc.core.drafting import (
    BankSource,
    DraftingError,
    Headline,
    headlines_for_report,
    read_bank_pdfs,
    read_headlines,
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
