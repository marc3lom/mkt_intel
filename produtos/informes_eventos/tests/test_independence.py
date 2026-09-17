"""Os pacotes do repositório não se importam, e nenhum importa o py-bcb.

Com os dois num `src/` só, a fronteira deixa de ser uma pasta e passa a ser
este arquivo. Os imports ficam dentro de funções, então nada quebraria no
import do pacote: quebraria na primeira chamada, no dia do informe.
"""

import re
from pathlib import Path

import comentario_matinal
import reports
from reports import _paths

REPORTS = Path(reports.__file__).resolve().parent
MATINAL = Path(comentario_matinal.__file__).resolve().parent
# Os notebooks do informes ainda moram dentro do pacote.
REPORTS_NOTEBOOKS = REPORTS
MATINAL_NOTEBOOKS = _paths.ROOT / "produtos" / "comentario_matinal" / "notebooks"


def _offenders(files: list[Path], module: str) -> list[str]:
    pattern = re.compile(rf"\b(from|import)\s+{module}\b")
    return sorted(str(f) for f in files if pattern.search(f.read_text(encoding="utf-8")))


def _sources(package: Path, notebooks: Path) -> list[Path]:
    files = [*package.rglob("*.py"), *notebooks.rglob("*.ipynb")]
    assert files
    return files


class TestNoPyBcbImports:
    def test_modules_and_notebooks(self):
        """Import de `classes` só resolve com o py-bcb no sys.path — e aqui ele não está."""
        assert _offenders(_sources(REPORTS, REPORTS_NOTEBOOKS), "classes") == []


class TestPackagesDoNotImportEachOther:
    def test_reports_does_not_import_comentario_matinal(self):
        """O backend do modelo é cópia, não import."""
        assert _offenders(_sources(REPORTS, REPORTS_NOTEBOOKS), "comentario_matinal") == []

    def test_comentario_matinal_does_not_import_reports(self):
        assert _offenders(_sources(MATINAL, MATINAL_NOTEBOOKS), "reports") == []
