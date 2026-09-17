"""Os notebooks são a interface do informe: importam o pacote instalado e
acham pasta por `reports._paths`, nunca pelo diretório em que foram abertos."""

import json

import pytest

from reports import _paths

NOTEBOOKS = sorted((_paths.ROOT / "notebooks" / "informes_eventos").rglob("*.ipynb"))


def _code(path) -> list[str]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_all_five_are_here():
    assert [p.name for p in NOTEBOOKS] == [
        "fomc_analysis.ipynb",
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
