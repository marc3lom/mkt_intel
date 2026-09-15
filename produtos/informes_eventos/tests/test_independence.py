"""Os informes não dependem do py-bcb: nenhum módulo nem notebook importa `classes`."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORTS_CLASSES = re.compile(r"\b(from|import)\s+classes\b")


class TestNoPyBcbImports:
    def test_modules_and_notebooks(self):
        """Import de `classes` só resolve com o py-bcb no sys.path — e aqui ele não está.

        Os imports ficam dentro de funções, então nada quebra no import do pacote:
        quebraria na primeira chamada à Bloomberg, com o terminal aberto, no dia do informe.
        """
        files = [*ROOT.glob("src/**/*.py"), *ROOT.glob("src/**/*.ipynb")]
        offenders = sorted(
            str(f.relative_to(ROOT))
            for f in files
            if IMPORTS_CLASSES.search(f.read_text(encoding="utf-8"))
        )
        assert files
        assert offenders == []
