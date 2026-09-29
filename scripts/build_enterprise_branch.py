"""Regenera o branch ``empresarial`` a partir da ``main``.

O ``empresarial`` é a versão do repositório que vai ao GitHub do BC: só o que os
notebooks precisam para rodar numa máquina que tem VS Code, Python, uv, git e o
GitHub Copilot, e mais nada. A regra de seleção é esta, e é o único lugar onde
ela vive:

- ``src/``, ``notebooks/``, ``prompts/``, ``templates/``, ``config/``,
  ``.github/prompts/`` e ``etc/``, inteiros, menos: os módulos ``_backend_*.py``
  (o backend local, que depende de uma CLI que as máquinas do BC não têm), o
  ``wiki.py`` (publica no GitHub pessoal do autor), o ``plantao.ipynb`` (a
  fachada do backend local; o do branch é o ``plantao_copilot.ipynb``) e o
  ``project_instructions.md`` (o caminho alternativo por um Project, que lá não
  existe);
- ``pyproject.toml`` sem a linha do ``publica-wiki``, ``uv.lock``,
  ``.python-version`` e ``.gitattributes``, para o ``uv sync`` e o filtro dos
  notebooks;
- ``.gitignore`` sem as linhas do backend local e com ``/arquivo/`` e
  ``/etc/.env``: o arquivo de comentários enviados e os segredos são de cada
  máquina;
- ``README_empresarial.md``, publicado como ``README.md``.

Nenhum arquivo de texto que entra pode mencionar o backend local: se algum
mencionar, a geração aborta antes de escrever a árvore, e o arquivo acusado se
corrige na ``main``.

Tudo é lido do commit da base, nunca da árvore de trabalho — mudança não
commitada não vaza para o branch. O índice é temporário, então nem o índice nem
a árvore de trabalho deste clone são tocados.

Cada execução acrescenta **um commit** em cima da ponta atual do
``empresarial`` (ou cria o branch órfão, se ele não existir). Não reescreve o
histórico: o push ao repositório do BC é sempre fast-forward, sem ``--force``.
Se nada mudou, não commita. A mensagem não leva trailer de coautoria nem menção
a ferramenta. O e-mail de autor vem de ``git config empresarial.email``,
configuração local do clone:

    git config empresarial.email <e-mail corporativo>

Uso::

    uv run python scripts/build_enterprise_branch.py              # commita
    uv run python scripts/build_enterprise_branch.py --dry-run    # só mostra
    uv run python scripts/build_enterprise_branch.py --bundle     # e grava o bundle
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

__all__ = [
    "gitignore_for_branch",
    "mentions_claude",
    "pyproject_for_branch",
    "select_paths",
    "strip_claude_lines",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
BRANCH = "empresarial"
README_SOURCE = "README_empresarial.md"
BUNDLE = REPO_ROOT / "output" / "empresarial.bundle"

INCLUDED_DIRS = (
    "src/",
    "notebooks/",
    "prompts/",
    "templates/",
    "config/",
    ".github/prompts/",
    "etc/",
)
ROOT_FILES = ("pyproject.toml", "uv.lock", ".python-version", ".gitattributes")
EXCLUDED = frozenset(
    {
        "notebooks/comentario_matinal/plantao.ipynb",
        "prompts/comentario_matinal/project_instructions.md",
        "src/comentario_matinal/wiki.py",
    }
)
# Só nos arquivos de texto a busca por menção ao backend local faz sentido: num
# binário (.dotx, .png) a sequência de bytes pode aparecer por acaso.
TEXT_SUFFIXES = (
    ".py",
    ".ipynb",
    ".md",
    ".toml",
    ".lock",
    ".txt",
    ".exemplo",
    ".gitignore",
    ".gitattributes",
    ".python-version",
)

BRANCH_IGNORE = """
# --- Deste branch --------------------------------------------------------------
# O arquivo de comentários enviados é de cada máquina e nunca vai ao repositório.
/arquivo/
# Segredos locais (a chave do FRED): cada um administra o seu.
/etc/.env
"""


def _git(
    *args: str,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
) -> bytes:
    """Roda um comando git na raiz do repo; levanta se falhar."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        input=stdin,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout


def select_paths(tracked: list[str]) -> list[str]:
    """Os caminhos da base que vão ao branch, ordenados.

    O ``.gitignore`` e o README entram à parte, transformados, e por isso não
    estão aqui.
    """

    def keep(path: str) -> bool:
        if path in EXCLUDED or Path(path).name.startswith("_backend_"):
            return False
        return path in ROOT_FILES or path.startswith(INCLUDED_DIRS)

    return sorted(p for p in tracked if keep(p))


def strip_claude_lines(text: str) -> str:
    """Tira as linhas que citam o backend local e colapsa brancos repetidos."""
    kept: list[str] = []
    for line in text.splitlines():
        if "claude" in line.lower():
            continue
        if not line.strip() and kept and not kept[-1].strip():
            continue
        kept.append(line)
    return "\n".join(kept).strip("\n") + "\n"


def gitignore_for_branch(text: str) -> str:
    return strip_claude_lines(text).rstrip("\n") + "\n" + BRANCH_IGNORE


_AUTHOR_EMAIL = re.compile(r',\s*email\s*=\s*"[^"]*"')


def pyproject_for_branch(text: str) -> str:
    """Tira o publicador do manual e o e-mail pessoal dos autores.

    O publicador escreve no GitHub pessoal do autor, e o e-mail pessoal não
    deve chegar ao repositório do BC — pela mesma razão que os commits do
    branch saem com o e-mail corporativo.
    """
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("publica-wiki ="):
            continue
        if line.startswith("authors ="):
            line = _AUTHOR_EMAIL.sub("", line)
        lines.append(line)
    return "".join(lines)


def mentions_claude(path: str, content: bytes) -> bool:
    if not path.endswith(TEXT_SUFFIXES):
        return False
    return b"claude" in content.lower()


def _ls_tree(ref: str) -> dict[str, tuple[str, str]]:
    """Mapeia caminho -> (modo, blob) de todos os arquivos de ``ref``."""
    out = _git("ls-tree", "-r", "-z", ref).decode("utf-8")
    entries: dict[str, tuple[str, str]] = {}
    for record in filter(None, out.split("\0")):
        meta, path = record.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind == "blob":
            entries[path] = (mode, sha)
    return entries


def _hash(content: bytes) -> str:
    """Grava ``content`` como blob e devolve o hash."""
    return _git("hash-object", "-w", "--stdin", stdin=content).decode().strip()


def _branch_tip() -> str | None:
    """Ponta atual do branch, ou ``None`` se ele ainda não existe."""
    try:
        sha = _git("rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}")
        return sha.decode().strip()
    except RuntimeError:
        return None


def _config(*args: str) -> str | None:
    """Lê uma chave do git config; ``None`` se ela não existe."""
    try:
        return _git("config", *args).decode().strip()
    except RuntimeError:
        return None


def _identity_env() -> dict[str, str]:
    """Ambiente com o e-mail do autor para os commits do branch.

    O repositório do BC não deve receber o e-mail pessoal que assina a
    ``main``. O e-mail vem de ``git config empresarial.email`` — config local
    do clone, nunca versionada — e vale para autor e committer. Sem a chave, o
    commit sairia com a identidade pessoal do clone, e por isso não sai.
    """
    email = _config("empresarial.email")
    if not email:
        raise SystemExit(
            "empresarial.email is not set; run `git config empresarial.email <corporate "
            "e-mail>` first — without it the commit would carry the personal identity"
        )
    return {**os.environ, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_EMAIL": email}


def _bundle() -> None:
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    _git("bundle", "create", str(BUNDLE), BRANCH)
    print(f"bundle: {BUNDLE}")


def build(base: str, dry_run: bool, bundle: bool) -> int:
    """Monta a árvore do branch a partir de ``base`` e commita se mudou."""
    base_sha = _git("rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
    entries = _ls_tree(base_sha)
    if README_SOURCE not in entries:
        raise SystemExit(f"{README_SOURCE} is not in {base}; the branch needs its README")

    # (caminho no branch, modo, blob, conteúdo) de tudo o que entra.
    files: list[tuple[str, str, str, bytes]] = []
    for path in select_paths(list(entries)):
        mode, sha = entries[path]
        content = _git("cat-file", "blob", sha)
        if path == "pyproject.toml":
            content = pyproject_for_branch(content.decode("utf-8")).encode("utf-8")
            sha = _hash(content)
        files.append((path, mode, sha, content))

    mode, sha = entries[README_SOURCE]
    files.append(("README.md", mode, sha, _git("cat-file", "blob", sha)))
    if ".gitignore" in entries:
        raw = _git("cat-file", "blob", entries[".gitignore"][1]).decode("utf-8")
        content = gitignore_for_branch(raw).encode("utf-8")
        files.append((".gitignore", "100644", _hash(content), content))

    offenders = sorted(path for path, _, _, content in files if mentions_claude(path, content))
    if offenders:
        for path in offenders:
            print(f"ERROR: mentions the local backend: {path}", file=sys.stderr)
        raise SystemExit(f"{len(offenders)} file(s) mention the local backend; branch not updated")

    lines = [f"{mode} {sha}\t{path}" for path, mode, sha, _ in sorted(files)]
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git("read-tree", "--empty", env=env)
        _git(
            "update-index",
            "--index-info",
            stdin=("\n".join(lines) + "\n").encode("utf-8"),
            env=env,
        )
        tree = _git("write-tree", env=env).decode().strip()

    tip = _branch_tip()
    print(f"{len(lines)} files from {base} ({base_sha[:7]})")
    if tip and _git("rev-parse", f"{tip}^{{tree}}").decode().strip() == tree:
        print(f"{BRANCH} is already up to date; nothing to commit")
        if bundle and not dry_run:
            _bundle()
        return 0
    if tip:
        print(_git("diff-tree", "-r", "--name-status", tip, tree).decode())

    if dry_run:
        print("dry run: branch not updated")
        return 0

    message = (
        f"Sincroniza com a origem ({base_sha[:7]})\n\n"
        f"{len(lines)} arquivos: o necessário para rodar os notebooks.\n"
    )
    parents = ["-p", tip] if tip else []
    # O commit-tree ignora o commit.gpgSign que o `git commit` respeita; sem
    # isto o branch sairia sem assinatura numa máquina que assina tudo.
    sign = ["-S"] if _config("--bool", "commit.gpgsign") == "true" else []
    commit = (
        _git(
            "commit-tree",
            tree,
            *parents,
            *sign,
            stdin=message.encode("utf-8"),
            env=_identity_env(),
        )
        .decode()
        .strip()
    )
    # O valor antigo protege contra corrida: vazio exige que o branch não
    # exista; senão, que ainda aponte para a ponta lida acima.
    _git("update-ref", f"refs/heads/{BRANCH}", commit, tip or "")
    print(f"{BRANCH} -> {commit[:7]}")
    if bundle:
        _bundle()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="main", help="ref de origem")
    parser.add_argument(
        "--dry-run", action="store_true", help="mostra o que mudaria sem atualizar o branch"
    )
    parser.add_argument(
        "--bundle", action="store_true", help=f"grava o branch em {BUNDLE.relative_to(REPO_ROOT)}"
    )
    args = parser.parse_args()
    return build(args.base, args.dry_run, args.bundle)


if __name__ == "__main__":
    sys.exit(main())
