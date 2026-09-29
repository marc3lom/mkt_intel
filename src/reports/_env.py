"""Segredos locais: a variável de ambiente, senão o etc/.env da raiz.

O ambiente vem primeiro para que testes e quem roda de fora possam injetar um
valor sem tocar arquivo. O .env é lido na hora, a cada chamada: é pequeno, e
quem acabou de criá-lo não precisa reiniciar o kernel.

Nada aqui escreve segredo em disco nem em log.
"""

from __future__ import annotations

import os
from pathlib import Path

from reports import _paths


def read_env_file(path: Path) -> dict[str, str]:
    """Lê `CHAVE=valor`, uma por linha; `#` comenta. Tolera BOM, espaços e aspas.

    É como o Bloco de Notas deixa o arquivo, e é nele que o colega o edita.
    """
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def get_secret(name: str) -> str | None:
    """O valor de `name`: do ambiente, senão do etc/.env; `None` se vazio ou ausente."""
    return os.environ.get(name) or read_env_file(_paths.ENV_FILE).get(name) or None
