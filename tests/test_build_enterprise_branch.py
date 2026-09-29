"""Regra de seleção do branch `empresarial`.

O que decide o que vai ao GitHub do BC é puro e mora aqui; a parte que mexe no
git (índice temporário, `commit-tree`, bundle) é conferida contra o repositório
real, num worktree descartável do branch gerado.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_enterprise_branch.py"
_spec = importlib.util.spec_from_file_location("build_enterprise", _SCRIPT)
assert _spec is not None and _spec.loader is not None
build_enterprise = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_enterprise)


def test_selection_keeps_only_what_runs():
    tracked = [
        ".claude/settings.json",
        ".gitattributes",
        ".gitignore",
        ".python-version",
        ".github/prompts/matinal-triagem.prompt.md",
        ".superpowers/x.md",
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "README_empresarial.md",
        "arquivo/comentario_matinal/2026/09/20260922.md",
        "config/comentario_matinal/painel.toml",
        "docs/comentario_matinal/plantao/01-primeiro-dia.md",
        "etc/env.exemplo",
        "exemplos/comentario_matinal/aprovados/.gitkeep",
        "notebooks/comentario_matinal/imagens.ipynb",
        "notebooks/comentario_matinal/plantao.ipynb",
        "notebooks/comentario_matinal/plantao_copilot.ipynb",
        "notebooks/informes_eventos/fomc/fomc_analysis.ipynb",
        "prompts/comentario_matinal/00_guia_de_estilo.md",
        "prompts/comentario_matinal/project_instructions.md",
        "pyproject.toml",
        "scripts/build_enterprise_branch.py",
        "src/comentario_matinal/_backend_claude.py",
        "src/comentario_matinal/modelo.py",
        "src/comentario_matinal/wiki.py",
        "src/reports/_backend_claude.py",
        "src/reports/_modelo.py",
        "templates/informes_eventos/fomc.dotx",
        "tests/comentario_matinal/test_modelo.py",
        "uv.lock",
    ]
    assert build_enterprise.select_paths(tracked) == [
        ".gitattributes",
        ".github/prompts/matinal-triagem.prompt.md",
        ".python-version",
        "config/comentario_matinal/painel.toml",
        "etc/env.exemplo",
        "notebooks/comentario_matinal/imagens.ipynb",
        "notebooks/comentario_matinal/plantao_copilot.ipynb",
        "notebooks/informes_eventos/fomc/fomc_analysis.ipynb",
        "prompts/comentario_matinal/00_guia_de_estilo.md",
        "pyproject.toml",
        "src/comentario_matinal/modelo.py",
        "src/reports/_modelo.py",
        "templates/informes_eventos/fomc.dotx",
        "uv.lock",
    ]


def test_gitignore_loses_claude_lines_and_gains_the_branch_rules():
    text = "# --- Editores ---\n.claude/settings.local.json\n.vscode/\n\n\n/input/\n"
    out = build_enterprise.gitignore_for_branch(text)
    assert "claude" not in out.lower()
    assert ".vscode/" in out and "/input/" in out
    assert "/arquivo/" in out.splitlines()
    assert "/etc/.env" in out.splitlines()
    assert "\n\n\n" not in out


def test_pyproject_loses_the_wiki_publisher_only():
    text = (
        '[project.scripts]\nmatinal = "comentario_matinal.cli:main"\n'
        'publica-wiki = "comentario_matinal.wiki:main"\n\n[build-system]\n'
    )
    out = build_enterprise.pyproject_for_branch(text)
    assert "publica-wiki" not in out
    assert 'matinal = "comentario_matinal.cli:main"' in out
    assert "[build-system]" in out


@pytest.mark.parametrize(
    "path, content, expected",
    [
        ("src/x.py", b"# usa o Claude Code", True),
        ("src/x.py", b"# nada aqui", False),
        ("README.md", b"CLAUDE.md", True),
        (".gitignore", b".claude/", True),
        ("templates/x.dotx", b"PK\x03\x04 claude", False),  # binário não é lido
    ],
)
def test_mentions_claude(path, content, expected):
    assert build_enterprise.mentions_claude(path, content) is expected


def test_pyproject_loses_the_personal_email():
    """O repositório do BC não recebe o e-mail pessoal do autor."""
    text = (
        '[project]\nname = "mkt-intel"\n'
        'authors = [{ name = "Marcelo Martinelli", email = "mmartinelli@gmail.com" }]\n'
    )
    out = build_enterprise.pyproject_for_branch(text)
    assert "mmartinelli@gmail.com" not in out
    assert 'authors = [{ name = "Marcelo Martinelli" }]' in out


def test_without_corporate_email_the_branch_is_not_committed(monkeypatch):
    """Sem o e-mail corporativo, o commit sairia com a identidade pessoal."""
    monkeypatch.setattr(build_enterprise, "_config", lambda *args: None)
    with pytest.raises(SystemExit, match="empresarial.email"):
        build_enterprise._identity_env()
