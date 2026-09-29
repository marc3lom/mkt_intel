"""A âncora de caminhos do `reports` é uma só, e é aferida aqui.

Contar níveis de `__file__` em cada módulo quebra em silêncio quando uma pasta
muda de lugar: o caminho continua válido, só aponta para onde não há nada.
"""

import re
from pathlib import Path

from reports import _paths

PROMPT_FILES = ("00_guia_de_estilo.md", "01_resumo.md", "02_bancos.md", "03_revisao.md")
PACKAGE = Path(_paths.__file__).resolve().parent


def test_root_is_the_repository_top():
    assert (_paths.ROOT / "pyproject.toml").is_file()
    assert (_paths.ROOT / ".git").exists()


def test_prompts_exist():
    for name in PROMPT_FILES:
        assert (_paths.PROMPTS / name).is_file(), name


def test_working_paths_stay_inside_the_repository():
    for path in (_paths.INPUT, _paths.OUTPUT, _paths.FED_DOCS):
        assert path.is_relative_to(_paths.ROOT), path


def test_only_paths_module_reads_dunder_file():
    """Nenhum outro módulo acha pasta por conta própria."""
    offenders = sorted(
        str(f.relative_to(PACKAGE))
        for f in PACKAGE.rglob("*.py")
        if f.name != "_paths.py" and re.search(r"\b__file__\b", f.read_text(encoding="utf-8"))
    )
    assert offenders == []


def test_no_default_depends_on_cwd():
    """`Path("output/...")` cai onde o notebook foi aberto, não na raiz."""
    pattern = re.compile(r"""Path\(\s*["'](?:input|output)/""")
    offenders = sorted(
        str(f.relative_to(PACKAGE))
        for f in PACKAGE.rglob("*.py")
        if pattern.search(f.read_text(encoding="utf-8"))
    )
    assert offenders == []


def test_final_layout():
    assert _paths.INPUT == _paths.ROOT / "input" / "informes_eventos"
    assert _paths.OUTPUT == _paths.ROOT / "output" / "informes_eventos"
    assert _paths.FED_DOCS == _paths.INPUT / "fed"
    assert _paths.ENV_FILE == _paths.ROOT / "etc" / ".env"
    assert not hasattr(_paths, "_PRODUCT")


def test_no_data_folder_inside_the_package():
    assert not any(p.name in {"input", "output"} for p in PACKAGE.rglob("*") if p.is_dir())
