"""Os notebooks são a interface do informe: importam o pacote instalado e
acham pasta por `reports._paths`, nunca pelo diretório em que foram abertos."""

import json

import pytest

from reports import _paths

NOTEBOOKS = sorted((_paths.ROOT / "notebooks" / "informes_eventos").rglob("*.ipynb"))


def _code(path) -> list[str]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_all_notebooks_are_here():
    assert [p.name for p in NOTEBOOKS] == [
        "fomc_analysis.ipynb",
        "fomc_analysis_copilot.ipynb",
        "market_reaction_grid.ipynb",
        "market_reaction_grid.ipynb",
        "payroll_analysis.ipynb",
        "payroll_report.ipynb",
    ]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_path_hack_and_every_cell_compiles(path):
    for i, source in enumerate(_code(path)):
        assert "sys.path" not in source, f"cell {i}"
        assert "project_root" not in source, f"cell {i}"
        assert "Path.cwd()" not in source, f"cell {i}"
        # `%matplotlib inline` e afins não são Python.
        clean = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith(("%", "!"))
        )
        compile(clean, f"{path.name} cell {i}", "exec")


# --- o notebook do FOMC com o Copilot ------------------------------------------

FOMC = _paths.ROOT / "notebooks" / "informes_eventos" / "fomc"
COPILOT = FOMC / "fomc_analysis_copilot.ipynb"


def test_copilot_notebook_pins_the_backend():
    """Detecção automática mudaria de backend conforme a máquina; aqui é sempre o Copilot."""
    assert 'os.environ["INFORMES_EVENTOS_BACKEND"] = "copilot"' in _code(COPILOT)[0]


def test_copilot_notebook_teaches_the_three_commands():
    text = COPILOT.read_text(encoding="utf-8")
    for stage in ("resumo", "bancos", "revisao"):
        assert f"/fomc-{stage}" in text, stage


def test_copilot_notebook_runs_the_same_stages_as_the_original():
    """A cópia é fachada do mesmo drafting; nenhuma etapa pode faltar nela."""
    original = "\n".join(_code(FOMC / "fomc_analysis.ipynb"))
    copy = "\n".join(_code(COPILOT))
    for call in ("draft_summary(", "draft_bank_comments(", "review_report(", "generate_fomc_report("):
        assert original.count(call) == copy.count(call), call


def test_copilot_notebook_does_not_name_the_local_backend():
    """Ele vai ao branch do BC, que não menciona o backend local."""
    assert "claude" not in COPILOT.read_text(encoding="utf-8").lower()
