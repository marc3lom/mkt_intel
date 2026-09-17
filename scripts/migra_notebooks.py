"""Uso único: tira dos notebooks do informes o `sys.path` e o `project_root`.

Roda uma vez na reestruturação e é apagado no fim dela.

Usa `json` puro em vez de `nbformat.write`: a escrita do `nbformat` normaliza o
arquivo inteiro (ids de célula, ordem de chaves, indentação) e produz um diff
enorme mesmo quando só o `source` de algumas células muda. `json.dump` com a
mesma indentação do nbstripout preserva o resto do arquivo byte a byte.
"""

import json
import re
import sys
from pathlib import Path

ALVO = Path(__file__).resolve().parents[1] / "notebooks" / "informes_eventos"

LINHAS_FORA = (
    re.compile(r"^# Adiciona o diret[óo]rio raiz ao path\s*$"),
    re.compile(r"^project_root = Path\.cwd\(\)\.parents\[3\]\s*$"),
    re.compile(r"^if str\(project_root / 'src'\) not in sys\.path:\s*$"),
    re.compile(r"^\s+sys\.path\.insert\(0, str\(project_root / 'src'\)\)\s*$"),
)
IMPORT_NOVO = "from reports._paths import INPUT, OUTPUT"


def _migra(fonte: str, usa_sys_alhures: bool) -> str:
    linhas = [l for l in fonte.split("\n") if not any(r.match(l) for r in LINHAS_FORA)]
    if not usa_sys_alhures:
        linhas = [l for l in linhas if l.strip() != "import sys"]
    texto = "\n".join(linhas)
    texto = texto.replace("project_root / 'output'", "OUTPUT")
    texto = texto.replace("project_root / 'input'", "INPUT")
    return re.sub(r"\n{3,}", "\n\n", texto)


def main() -> int:
    for caminho in sorted(ALVO.rglob("*.ipynb")):
        nb = json.loads(caminho.read_text(encoding="utf-8"))
        codigo = [c for c in nb["cells"] if c["cell_type"] == "code"]
        resto = "\n".join("".join(c["source"]) for c in codigo)
        usa_sys = bool(re.search(r"\bsys\.(?!path\b)", resto))
        for celula in codigo:
            fonte = "".join(celula["source"])
            tinha = "project_root = Path.cwd()" in fonte
            texto = _migra(fonte, usa_sys)
            if tinha:
                texto = texto.replace(
                    "from pathlib import Path", f"from pathlib import Path\n\n{IMPORT_NOVO}", 1)
            celula["source"] = texto.splitlines(keepends=True)
        if "project_root" in "\n".join("".join(c["source"]) for c in codigo):
            print(f"sobrou project_root em {caminho.name}", file=sys.stderr)
            return 1
        # `newline="\n"`: sem isso o Python traduz "\n" para "\r\n" ao
        # escrever em modo texto no Windows, e o notebook original é LF só —
        # o arquivo inteiro apareceria como mudado no diff.
        with caminho.open("w", encoding="utf-8", newline="\n") as fh:
            json.dump(nb, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(f"ok {caminho.relative_to(ALVO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
