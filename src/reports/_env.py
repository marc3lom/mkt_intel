"""Segredos locais: a variável de ambiente, senão o etc/.env da raiz.

O ambiente vem primeiro para que testes e quem roda de fora possam injetar um
valor sem tocar arquivo. O .env é lido na hora, a cada chamada: é pequeno, e
quem acabou de criá-lo não precisa reiniciar o kernel.

Nada aqui escreve segredo em disco nem em log.
"""

from __future__ import annotations

import codecs
import os
from pathlib import Path

from reports import _paths


def _decode(raw: bytes) -> str:
    """UTF-8, com ou sem BOM, ou UTF-16 com BOM — o "Unicode" do Bloco de Notas."""
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def _value(raw: str) -> str:
    """O valor sem espaços, sem aspas e sem comentário depois dele."""
    value = raw.strip()
    if value[:1] in ("'", '"'):
        end = value.find(value[0], 1)
        if end > 0:
            return value[1:end]
    # Fora das aspas, `#` precedido de espaço abre comentário.
    for i, ch in enumerate(value):
        if ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
    return value


def read_env_file(path: Path) -> dict[str, str]:
    """Lê `CHAVE=valor`, uma por linha; `#` comenta.

    Tolera o que o Bloco de Notas deixa no arquivo, que é onde o colega o edita:
    BOM, UTF-16, espaços em volta do `=`, aspas, comentário na mesma linha.
    """
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in _decode(path.read_bytes()).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        values[key] = _value(value)
    return values


def misnamed_env_file() -> Path | None:
    """O `.env.txt` que o Bloco de Notas grava com a extensão escondida, se existir.

    O arquivo existe, o colega vê "`.env`" no Explorer e jura que criou o certo;
    sem apontar o nome real, o erro de chave ausente não se explica.
    """
    if _paths.ENV_FILE.is_file():
        return None
    wrong = _paths.ENV_FILE.with_name(_paths.ENV_FILE.name + ".txt")
    return wrong if wrong.is_file() else None


def get_secret(name: str) -> str | None:
    """O valor de `name`: do ambiente, senão do etc/.env; `None` se vazio ou ausente."""
    return os.environ.get(name) or read_env_file(_paths.ENV_FILE).get(name) or None
