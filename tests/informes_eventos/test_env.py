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


def test_example_is_versioned_and_real_file_is_ignored():
    root = _paths.ROOT
    ignored = subprocess.run(["git", "check-ignore", "-q", "etc/.env"], cwd=root)
    example = subprocess.run(["git", "check-ignore", "-q", "etc/env.exemplo"], cwd=root)
    assert ignored.returncode == 0, "etc/.env tem de ficar fora do git"
    assert example.returncode == 1, "etc/env.exemplo tem de ser versionável"
    assert (root / "etc" / "env.exemplo").is_file()
