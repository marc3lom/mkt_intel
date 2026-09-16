"""As etapas de modelo do informe do FOMC, sem rede, sem Bloomberg e sem `claude`."""

import pandas as pd
import pytest

from reports.fomc.core import drafting
from reports.fomc.core.data_loader import _TZ_BRT
from reports.fomc.core.drafting import (
    BankSource,
    DraftingError,
    Headline,
    format_market,
    headlines_for_report,
    market_snapshot,
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
