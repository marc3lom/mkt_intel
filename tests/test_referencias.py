"""Todo teste que um comentário ou uma célula cita existe no caminho citado.

Os testes mudaram de lugar na reestruturação por produto, e os comentários
que apontavam para eles ficaram para trás; quem segue a pista não acha nada.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CITACAO = re.compile(r"tests/[\w/]+\.py")

# O notebook que o autor pediu para ficar intacto, como estava em 29/09/2026.
INTOCADOS = {"notebooks/comentario_matinal/plantao.ipynb"}


def test_todo_teste_citado_existe():
    fontes = [*RAIZ.glob("src/**/*.py"), *RAIZ.glob("notebooks/**/*.ipynb")]
    quebradas = sorted(
        f"{f.relative_to(RAIZ).as_posix()}: {citado}"
        for f in fontes
        if f.relative_to(RAIZ).as_posix() not in INTOCADOS
        for citado in set(CITACAO.findall(f.read_text(encoding="utf-8")))
        if not (RAIZ / citado).is_file()
    )
    assert quebradas == []
