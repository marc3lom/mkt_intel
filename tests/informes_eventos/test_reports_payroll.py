"""Testes de caracterização de reports.payroll.

Fixam o comportamento atual antes de o pacote migrar para o repositório
mkt_intel. Nenhum toca Bloomberg, FRED ou BLS.
"""

import pandas as pd
import pytest
from docx import Document

from reports.payroll.core import bls_scraper, data_loader
from reports.payroll.core.calculations import (
    calculate_moving_averages,
    format_date_ptbr,
    format_release_summary,
    get_trend_assessment,
)
from reports.payroll.core.word_report import generate_payroll_report

RELEASE = {
    "Unemployment": {"actual": 4.3, "survey": 4.2, "prior": 4.2, "period": "2026-08"},
    "NFP": {"actual": 22.0, "survey": 75.0, "prior": 79.0, "period": "2026-08"},
}


class TestCalculateMovingAverages:
    def test_default_windows(self):
        """Janelas padrão de 3 e 6 meses, com NaN até a janela encher."""
        df = pd.DataFrame({"NFP": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]})
        result = calculate_moving_averages(df)
        assert result["NFP_MA3m"].isna().sum() == 2
        assert result["NFP_MA3m"].tolist()[2:] == pytest.approx([200.0, 300.0, 400.0, 500.0])
        assert result["NFP_MA6m"].iloc[-1] == pytest.approx(350.0)


class TestFormatDatePtbr:
    @pytest.mark.parametrize(
        ("fmt", "expected"),
        [("%b-%y", "mar-26"), ("%B de %Y", "marco de 2026"), ("%d/%m/%Y", "15/03/2026")],
    )
    def test_tokens(self, fmt, expected):
        """Meses em pt-BR sem depender do locale (e "marco" sem cedilha, como hoje)."""
        assert format_date_ptbr("2026-03-15", fmt) == expected


class TestGetTrendAssessment:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            ([1.0, 2.0], "Dados insuficientes"),
            ([100.0, 100.0, 100.0], "Estavel"),
            ([100.0, 100.0, 100.0, 200.0, 200.0, 200.0], "Acelerando"),
            ([200.0, 200.0, 200.0, 100.0, 100.0, 100.0], "Desacelerando"),
        ],
    )
    def test_trend(self, values, expected):
        """Média de 3 meses contra a de 6, com banda de 10%."""
        assert get_trend_assessment(pd.DataFrame({"NFP": values})) == expected


class TestFormatReleaseSummary:
    def test_fixed_order_and_units(self):
        """A ordem é a da planilha (NFP antes do desemprego), não a do dicionário."""
        df = format_release_summary(RELEASE)
        assert list(df.columns) == [
            "Evento",
            "Periodo",
            "Pesquisa",
            "Atual",
            "Anterior",
            "Revisao",
        ]
        assert df.to_dict("records") == [
            {
                "Evento": "Nonfarm Payrolls",
                "Periodo": "Aug",
                "Pesquisa": "75k",
                "Atual": "22k",
                "Anterior": "79k",
                "Revisao": "",
            },
            {
                "Evento": "Unemployment Rate",
                "Periodo": "Aug",
                "Pesquisa": "4.2%",
                "Atual": "4.3%",
                "Anterior": "4.2%",
                "Revisao": "",
            },
        ]


class TestGetLatestRelease:
    def test_numeric_fields_arrive_as_numbers(self, monkeypatch):
        """No formato longo do xbbg 1.x a coluna `value` vem como texto; os campos
        numéricos têm de sair como número, ou `format_release_summary` quebra."""
        long = pd.DataFrame(
            [
                ("NFP TCH Index", "PX_LAST", "22.0"),
                ("NFP TCH Index", "PREV_CLOSE_VAL", "79.0"),
                ("NFP TCH Index", "BN_SURVEY_MEDIAN", "75.0"),
                ("NFP TCH Index", "ECO_RELEASE_DT", "2026-09-04"),
                ("NFP TCH Index", "OBSERVATION_PERIOD", "2026-08"),
            ],
            columns=["ticker", "field", "value"],
        )

        class FakeBlp:
            async def abdp(self, **kwargs):
                return long

        monkeypatch.setattr(data_loader, "_get_bloomberg_client", FakeBlp)
        nfp = data_loader.get_latest_release()["NFP"]
        assert (nfp["actual"], nfp["prior"], nfp["survey"]) == (22.0, 79.0, 75.0)
        assert nfp["period"] == "2026-08"
        assert format_release_summary({"NFP": nfp})["Atual"].tolist() == ["22k"]


class TestParseBlsResponse:
    @staticmethod
    def _series(series_id, values):
        """`values` em ordem cronológica, a partir de jan/2025; a API devolve do mais novo."""
        months = pd.period_range("2025-01", periods=len(values), freq="M")
        data = [
            {"year": str(m.year), "period": f"M{m.month:02d}", "value": str(v)}
            for m, v in zip(months, values)
        ]
        return {"seriesID": series_id, "data": data[::-1]}

    def test_changes_are_level_differences(self):
        """Mês corrente, mês anterior e doze meses, em diferença de nível."""
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    self._series("CES0000000001", [100.0 + i for i in range(13)] + [120.0]),
                    self._series("CES2000000001", [50.0, 52.0, 51.0]),
                ]
            },
        }
        df = bls_scraper.parse_bls_response(payload)
        assert pd.isna(df.loc[1, "prior_year"])  # menos de 13 meses: sem variação anual
        df.loc[1, "prior_year"] = None
        assert df.astype(object).where(df.notna(), None).to_dict("records") == [
            {
                "industry": "Total nonfarm",
                "level": 0,
                "prior_year": 120.0 - 101.0,
                "prior_month": 1.0,
                "current_month": 120.0 - 112.0,
            },
            {
                "industry": "Construction",
                "level": 2,
                "prior_year": None,
                "prior_month": 2.0,
                "current_month": -1.0,
            },
        ]

    def test_api_failure_raises(self):
        with pytest.raises(RuntimeError, match="threshold"):
            bls_scraper.parse_bls_response(
                {"status": "REQUEST_NOT_PROCESSED", "message": ["daily threshold reached"]}
            )

    def test_notebook_sectors_are_all_mapped(self):
        """Todo setor que o gráfico dos notebooks procura tem série."""
        import json

        from reports import _paths

        nb = _paths.ROOT /"notebooks/informes_eventos/payroll/payroll_report.ipynb"
        source = "".join(
            "".join(c["source"]) for c in json.loads(nb.read_text(encoding="utf-8"))["cells"]
        )
        block = source.split("INDUSTRY_ORDER = [", 1)[1].split("]", 1)[0]
        wanted = [s.strip().strip("'\"") for s in block.split(",") if s.strip()]
        assert wanted and set(wanted) <= set(bls_scraper.BLS_SERIES)


class TestGeneratePayrollReport:
    def test_docx_without_charts(self, tmp_path):
        """Sem gráfico algum o relatório ainda sai, com o título do mês."""
        path = generate_payroll_report(
            "2026-09-04", format_release_summary(RELEASE), chart_paths={}, output_dir=tmp_path
        )
        assert path == tmp_path / "Mesa de Investimentos - PAYROLL 20260904.docx"
        texts = [p.text for p in Document(str(path)).paragraphs]
        assert "DADOS DO RELATORIO DE EMPREGO DOS EUA - SETEMBRO/2026" in texts


class TestProjectRootAnchors:
    def test_fred_key_comes_from_the_local_env_file(self, monkeypatch, tmp_path):
        """A chave do FRED vem de `get_secret`, que lê o etc/.env da raiz."""
        from reports import _paths

        monkeypatch.delenv("FRED_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("FRED_API_KEY=abc123\n", encoding="utf-8")
        monkeypatch.setattr(_paths, "ENV_FILE", env_file)
        client = data_loader._get_fred_client()
        assert client.api_key == "abc123"

    def test_missing_fred_key_says_which_file_to_create(self, monkeypatch, tmp_path):
        from reports import _paths

        monkeypatch.delenv("FRED_API_KEY", raising=False)
        monkeypatch.setattr(_paths, "ENV_FILE", tmp_path / "etc" / ".env")
        with pytest.raises(ValueError, match="env.exemplo"):
            data_loader._get_fred_client()

    def test_misnamed_env_file_is_named_in_the_error(self, monkeypatch, tmp_path):
        from reports import _paths

        monkeypatch.delenv("FRED_API_KEY", raising=False)
        env_file = tmp_path / "etc" / ".env"
        env_file.parent.mkdir(parents=True)
        env_file.with_name(".env.txt").write_text("FRED_API_KEY=abc\n", encoding="utf-8")
        monkeypatch.setattr(_paths, "ENV_FILE", env_file)
        with pytest.raises(ValueError, match=r"\.env\.txt"):
            data_loader._get_fred_client()
