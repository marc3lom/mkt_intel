"""Testes de caracterização de reports.payroll.

Fixam o comportamento atual antes de o pacote migrar para o repositório
mkt_intelligence. Nenhum toca Bloomberg, FRED ou BLS.
"""

from pathlib import Path

import pandas as pd
import pytest
from docx import Document

from reports.payroll.core import data_loader
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
    def test_env_path_is_project_etc(self):
        """A chave do FRED é lida de <raiz do projeto>/etc/.env."""
        env = Path(data_loader._env_path).resolve()
        assert env.parent.name == "etc"
        assert (env.parent.parent / "pyproject.toml").is_file()
