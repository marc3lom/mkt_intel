"""O template do FOMC mora no repositório e não carrega informe algum."""

import re
import zipfile

from reports import _paths
from reports.fomc.core import word_report


def _template():
    return _paths.TEMPLATES / word_report.TEMPLATE_NAME


def test_template_is_in_the_repository():
    assert _template().is_file()


def test_loaded_template_has_no_body_text():
    doc = word_report._load_template()
    assert all(not p.text.strip() for p in doc.paragraphs)
    assert not doc.tables


def test_every_image_belongs_to_header_or_footer():
    """Imagem que só o corpo usava é pedaço do informe de origem."""
    with zipfile.ZipFile(_template()) as z:
        media = {n.removeprefix("word/") for n in z.namelist() if n.startswith("word/media/")}
        rels = "".join(
            z.read(n).decode("utf-8")
            for n in z.namelist()
            if re.match(r"word/_rels/(header|footer)\d*\.xml\.rels$", n)
        )
    orphans = sorted(m for m in media if m not in rels)
    assert orphans == [], f"imagens fora do cabeçalho/rodapé: {orphans}"


def test_no_personal_paths_in_code_or_notebooks():
    """O OneDrive do autor não existe na máquina de mais ninguém."""
    roots = [_paths.ROOT / "src" / "reports", _paths.ROOT / "notebooks" / "informes_eventos"]
    offenders = sorted(
        str(f.relative_to(_paths.ROOT))
        for root in roots
        for f in [*root.rglob("*.py"), *root.rglob("*.ipynb")]
        if re.search(r"OneDrive|Users[\\/]+mmart", f.read_text(encoding="utf-8"))
    )
    assert offenders == []
