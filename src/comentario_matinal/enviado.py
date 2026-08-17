"""Arquivamento do comentário enviado e limpeza do dia.

Fecha o plantão: confere que o texto arquivado é o mesmo que foi ao Word, move
os dois arquivos para ``arquivo/AAAA/MM/`` e esvazia ``fontes/`` e ``saida/``.

A conferência existe porque o runbook manda abrir o `.docx` para conferir o
texto antes de exportar o PDF. Corrigido algo ali, o `.md` deixa de ser o que foi
enviado — e é ele que a triagem do dia seguinte lê como comentário do dia
anterior, para julgar ineditismo e apanhar contradição. Arquivar um texto que não
foi enviado não erra hoje; erra amanhã, e de um jeito difícil de rastrear.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from comentario_matinal.documento import trechos_de

# O template aplica este estilo aos parágrafos do comentário. É por ele que os
# marcadores se distinguem do título e do fecho, que o template também traz.
ESTILO_MARCADOR = "List Paragraph"


class DestinoOcupado(RuntimeError):
    """Já existe comentário arquivado para a data."""


@dataclass(frozen=True)
class Divergencia:
    """Um marcador que difere entre o documento enviado e o Markdown."""

    indice: int          # 1-based, como o autor conta
    no_md: str
    no_docx: str


def _normaliza(texto: str) -> str:
    """Espaço em branco não é diferença: o Word e o Markdown quebram diferente."""
    return re.sub(r"\s+", " ", texto).strip()


def _do_markdown(md: Path) -> list[str]:
    """Os marcadores do Markdown, em texto puro.

    A ênfase é descartada de propósito: ``*term premium*`` no Markdown é
    ``term premium`` no Word, e comparar a marcação acusaria diferença onde há
    apenas formatação.
    """
    linhas = md.read_text(encoding="utf-8").splitlines()
    marcadores: list[str] = []
    for linha in linhas:
        if linha.lstrip().startswith("- "):
            marcadores.append(linha.lstrip()[2:])
        elif marcadores and linha.strip():
            # Continuação de marcador quebrado por largura de coluna.
            marcadores[-1] += " " + linha.strip()
    return [_normaliza("".join(t.texto for t in trechos_de(m))) for m in marcadores]


def _do_docx(docx: Path) -> list[str]:
    from docx import Document

    doc = Document(str(docx))
    return [_normaliza(p.text) for p in doc.paragraphs
            if p.style.name == ESTILO_MARCADOR and p.text.strip()]


def divergencias(docx: Path, md: Path) -> list[Divergencia]:
    """Compara marcador a marcador o documento enviado e o Markdown."""
    do_docx, do_md = _do_docx(docx), _do_markdown(md)

    achados = []
    for i in range(max(len(do_docx), len(do_md))):
        a = do_md[i] if i < len(do_md) else ""
        b = do_docx[i] if i < len(do_docx) else ""
        if a != b:
            achados.append(Divergencia(i + 1, a, b))
    return achados


def arquiva(saida: Path, raiz: Path, marca: str, forcar: bool = False) -> list[Path]:
    """Copia o comentário do dia para ``arquivo/AAAA/MM/``.

    O `.md` é obrigatório — é o que fica versionado e o que alimenta o dia
    seguinte. O `.docx` acompanha quando existir; ele é subproduto de envio, não
    entra no git, e vale como registro local do que de fato foi mandado.

    Nada é sobrescrito: rearquivar por engano apagaria em silêncio o comentário
    de um dia já enviado.
    """
    destino = raiz / marca[:4] / marca[4:6]
    pares = [
        (saida / f"comentario_{marca}.md", destino / f"{marca}.md"),
        (saida / f"comentario_{marca}.docx", destino / f"comentario_{marca}.docx"),
    ]

    origem_md = pares[0][0]
    if not origem_md.exists():
        raise FileNotFoundError(
            f"{origem_md} não existe. O comentário revisado sai de "
            "`matinal revisao`; sem ele não há o que arquivar."
        )

    ocupados = [d for o, d in pares if o.exists() and d.exists()]
    if ocupados and not forcar:
        raise DestinoOcupado(
            "já existe comentário arquivado para a data: "
            + ", ".join(str(d) for d in ocupados)
        )

    destino.mkdir(parents=True, exist_ok=True)
    escritos = []
    for origem, alvo in pares:
        if not origem.exists():
            print(f"Aviso: {origem.name} não existe; arquivando sem ele.",
                  file=sys.stderr)
            continue
        shutil.copy2(origem, alvo)
        escritos.append(alvo)
    return escritos


def limpa(pastas: list[Path]) -> int:
    """Esvazia as pastas do dia, preservando as próprias pastas.

    As pastas ficam: `fontes/` é onde o analista larga os PDFs da manhã
    seguinte, e `saida/` é criada pelo comando, mas apagá-la faria o `arquivo/`
    e o `fontes/` parecerem opcionais no runbook. Chamada só depois de o
    arquivamento ter dado certo.
    """
    n = 0
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for item in pasta.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            n += 1
    return n
