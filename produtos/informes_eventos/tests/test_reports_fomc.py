"""Testes de caracterização de reports.fomc.

Fixam o comportamento atual antes de o pacote migrar para o repositório
disseminacao; lá, os mesmos testes provam que a mudança de casa não mudou nada.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from reports.fomc.core import data_loader, word_export
from reports.fomc.core.calculations import calculate_surprise, classify_change_direction
from reports.fomc.core.data_loader import _TZ_BRT, _TZ_ET, is_sep_meeting
from reports.fomc.core.pdf_parser import _parse_rate_fraction, _parse_statement_text
from reports.fomc.core.word_export import (
    MARKET_REACTION_PANELS,
    _to_naive_brt,
    create_market_reaction_grid,
)

STATEMENT = (
    "Inflation remains somewhat elevated. The Committee decided to maintain the target "
    "range for the federal funds rate at 4-1/4 to 4-1/2 percent. Voting against the "
    "action were: Michelle Bowman, Christopher Waller."
)


class TestClassifyChangeDirection:
    @pytest.mark.parametrize(
        ("variable", "change", "expected"),
        [
            ("PCE inflation", 0.2, "hawkish"),
            ("PCE inflation", -0.2, "dovish"),
            ("Unemployment rate", 0.1, "dovish"),
            ("Unemployment rate", -0.1, "hawkish"),
            ("Change in real GDP", 0.0005, "neutral"),
            ("Indicador desconhecido", 0.25, "hawkish"),
        ],
    )
    def test_direction(self, variable, change, expected):
        """Desemprego inverte o sinal; indicador fora do mapa sobe como hawkish."""
        assert classify_change_direction(variable, change) == expected


class TestCalculateSurprise:
    def test_rate_surprise_in_bps(self):
        """Surpresa de taxa sai também em pontos-base inteiros."""
        result = calculate_surprise(4.5, 4.25, "rate")
        assert result["surprise"] == 0.25
        assert result["surprise_bps"] == 25
        assert result["direction"] == "forte"

    def test_unemployment_is_inverted(self):
        """Desemprego abaixo do esperado é leitura forte, e não tem bps."""
        result = calculate_surprise(4.1, 4.3, "unemployment")
        assert abs(result["surprise"] - (-0.2)) < 1e-9
        assert result["surprise_bps"] is None
        assert result["direction"] == "forte"

    def test_no_surprise_is_neutral(self):
        """Atual igual à pesquisa é neutro."""
        assert calculate_surprise(2.0, 2.0, "inflation")["direction"] == "neutro"

    @pytest.mark.xfail(
        strict=True,
        reason="int() trunca 0.9999… para 0: surpresa de 1bp sai como 0bp (defeito conhecido)",
    )
    def test_one_bp_surprise(self):
        """Quando o defeito for corrigido, este xfail estrito quebra e deve ser retirado."""
        assert calculate_surprise(4.26, 4.25, "rate")["surprise_bps"] == 1


class TestIsSepMeeting:
    def test_sep_months(self):
        """Março, junho, setembro e dezembro têm SEP; janeiro não."""
        assert is_sep_meeting("20260318") is True
        assert is_sep_meeting("20260128") is False


class TestParseRateFraction:
    @pytest.mark.parametrize(("text", "expected"), [("4-1/4", 4.25), ("3-1/2", 3.5), ("4", 4.0)])
    def test_fraction(self, text, expected):
        """Frações do statement viram decimal."""
        assert _parse_rate_fraction(text) == expected


class TestParseStatementText:
    def test_extracts_range_decision_and_dissent(self):
        """Faixa, decisão, dissidentes e frase-chave saem do texto do statement."""
        result = _parse_statement_text(STATEMENT)
        assert result["target_rate_low"] == 4.25
        assert result["target_rate_high"] == 4.5
        assert result["decision"] == "hold"
        assert result["unanimous"] is False
        assert result["dissenters"] == ["Michelle Bowman", "Christopher Waller"]
        assert result["key_phrases"] == ["Inflation remains somewhat elevated"]


class TestToNaiveBrt:
    def test_winter_and_summer_offsets(self):
        """ET→BRT: +2h no inverno de Nova York, +1h no verão; sai sem fuso."""
        winter = _to_naive_brt(pd.Timestamp("2026-01-28 14:00", tz=_TZ_ET))
        summer = _to_naive_brt(pd.Timestamp("2026-07-29 14:00", tz=_TZ_ET))
        assert winter == pd.Timestamp("2026-01-28 16:00")
        assert summer == pd.Timestamp("2026-07-29 15:00")

    def test_naive_passes_through(self):
        """Timestamp sem fuso já é BRT e passa intacto."""
        ts = pd.Timestamp("2026-01-28 16:00")
        assert _to_naive_brt(ts) == ts


def _synthetic_intraday() -> pd.DataFrame:
    index = pd.date_range("2026-01-28 09:00", "2026-01-28 20:00", freq="5min", tz=_TZ_BRT)
    columns = [key for key, *_ in MARKET_REACTION_PANELS]
    return pd.DataFrame(
        {col: [100.0 + i * 0.01 for i in range(len(index))] for col in columns},
        index=index,
    )


class TestCreateMarketReactionGrid:
    @pytest.mark.parametrize("style", ["word", "bloomberg"])
    def test_writes_png(self, tmp_path, style):
        """O grid 3x3 sai em PNG nos dois estilos, com dados sintéticos."""
        out = tmp_path / f"grid_{style}.png"
        fig = create_market_reaction_grid(
            _synthetic_intraday(),
            event_times={"decisao": pd.Timestamp("2026-01-28 16:00", tz=_TZ_BRT)},
            output_path=out,
            style=style,
        )
        n_axes = len(fig.axes)
        plt.close(fig)
        assert out.stat().st_size > 0
        assert n_axes >= 9

    def test_rejects_unknown_style(self):
        """Estilo fora de MARKET_REACTION_STYLES é erro."""
        with pytest.raises(ValueError):
            create_market_reaction_grid(_synthetic_intraday(), style="excel")


class TestProjectRootAnchors:
    """input/, output/ e etc/ se ancoram na raiz do projeto — a que tem o pyproject.toml.

    A migração só é neutra se a raiz do produto novo repetir esse arranjo.
    """

    def test_word_export_root_has_pyproject(self):
        """output/reports/fomc nasce na raiz do projeto."""
        assert (word_export._get_project_root() / "pyproject.toml").is_file()

    def test_grid1_anchor_is_project_root(self):
        """O grid1.xlsx é procurado em <raiz>/input/."""
        assert (Path(data_loader.__file__).parents[4] / "pyproject.toml").is_file()

    def test_module_path_is_fomc_package(self):
        """Os documentos do Fed moram em <pacote fomc>/input/."""
        assert data_loader._get_module_path().name == "fomc"
