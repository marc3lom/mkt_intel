"""Segredos locais: a variável de ambiente, senão o etc/.env da raiz."""

import subprocess

import pytest

from reports import _env, _paths


@pytest.fixture(autouse=True)
def no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.setattr(_paths, "ENV_FILE", tmp_path / "etc" / ".env")


def write_env(text: str, bom: bool = False):
    _paths.ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = ("﻿" if bom else "") + text
    _paths.ENV_FILE.write_bytes(data.encode("utf-8"))


def test_environment_wins(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "from-env")
    write_env("FRED_API_KEY=from-file\n")
    assert _env.get_secret("FRED_API_KEY") == "from-env"


def test_file_when_no_environment():
    write_env("# comentário\nFRED_API_KEY=abc123\n")
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_notepad_style_file_is_read():
    """BOM, espaços em volta do `=` e aspas: é como o Bloco de Notas deixa."""
    write_env('FRED_API_KEY = "abc123"\r\n', bom=True)
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_missing_file_and_variable_is_none():
    assert _env.get_secret("FRED_API_KEY") is None


def test_empty_value_is_none():
    write_env("FRED_API_KEY=\n")
    assert _env.get_secret("FRED_API_KEY") is None


def test_notepad_unicode_file_is_read():
    """O "Unicode" do Bloco de Notas é UTF-16 com BOM."""
    _paths.ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    _paths.ENV_FILE.write_bytes("FRED_API_KEY=abc123\r\n".encode("utf-16"))
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_inline_comment_is_not_part_of_the_value():
    write_env("FRED_API_KEY=abc123   # minha chave do FRED\n")
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_hash_inside_quotes_is_kept():
    write_env('FRED_API_KEY="ab#c"  # comentário\n')
    assert _env.get_secret("FRED_API_KEY") == "ab#c"


def test_misnamed_env_file_is_found():
    """Com a extensão escondida no Explorer, o Bloco de Notas salva `.env.txt`."""
    _paths.ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    wrong = _paths.ENV_FILE.with_name(".env.txt")
    wrong.write_text("FRED_API_KEY=abc123\n", encoding="utf-8")
    assert _env.misnamed_env_file() == wrong
    assert _env.get_secret("FRED_API_KEY") is None


def test_example_is_versioned_and_real_file_is_ignored():
    root = _paths.ROOT
    ignored = subprocess.run(["git", "check-ignore", "-q", "etc/.env"], cwd=root)
    example = subprocess.run(["git", "check-ignore", "-q", "etc/env.exemplo"], cwd=root)
    assert ignored.returncode == 0, "etc/.env tem de ficar fora do git"
    assert example.returncode == 1, "etc/env.exemplo tem de ser versionável"
    assert (root / "etc" / "env.exemplo").is_file()
