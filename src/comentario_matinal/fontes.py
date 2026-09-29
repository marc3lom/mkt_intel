"""Conversão dos PDFs das fontes do dia para texto.

O insumo das etapas de IA precisa ser o mesmo independentemente do backend: um
modelo lê PDF anexo, outro não, e um terceiro lê de um jeito diferente. Extrair
para texto uma vez, aqui, faz com que trocar o backend não mude o que o modelo
recebe — que é a condição para comparar saídas entre backends.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Conversao:
    """O que entrou, o que falhou e o que sequer foi olhado."""

    aproveitados: int = 0
    vazios: list[str] = field(default_factory=list)
    ignorados: list[str] = field(default_factory=list)


# O PDF do comentário enviado ontem, quando o autor o anexa: nome começando por
# "anterior", em qualquer caixa. Ele não é fonte do dia — misturado às fontes, o
# modelo o leria como notícia de hoje e poderia tirar tema dele (§5.2 do guia).
PREFIXO_ANTERIOR = "anterior"


def e_anterior(caminho: Path) -> bool:
    return caminho.name.lower().startswith(PREFIXO_ANTERIOR)


def _texto_do_pdf(pdf: Path) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(str(pdf))
    return "\n".join((p.extract_text() or "") for p in leitor.pages).strip()


def anterior_em_pdf(origem: Path) -> tuple[str, str] | None:
    """O (nome, texto) do PDF do comentário anterior, se houver um com texto.

    Com mais de um, vale o último em ordem de nome — com data no nome, o mais
    recente.
    """
    if not origem.is_dir():
        return None
    candidatos = sorted(p for p in origem.iterdir()
                        if p.is_file() and p.suffix.lower() == ".pdf"
                        and e_anterior(p))
    for pdf in reversed(candidatos):
        try:
            texto = _texto_do_pdf(pdf)
        except Exception:  # noqa: BLE001 — PDF ruim não derruba a etapa
            continue
        if texto:
            return pdf.name, texto
    return None


def converte(origem: Path, destino: Path) -> Conversao:
    """Extrai o texto de todos os PDFs de ``origem`` para um arquivo único.

    Duas formas de um arquivo estar na pasta e não chegar ao modelo, e as duas
    voltam nomeadas para virar aviso, não silêncio:

    ``vazios`` — PDF que não rendeu texto, quase sempre digitalização sem OCR.
    ``ignorados`` — o que não é PDF. O .docx que o analista salvou por hábito, o
    print de tela, o e-mail exportado. O arquivo existe, o analista supõe que
    entrou, e o conteúdo nunca foi lido. Sem aviso isso só apareceria como a
    ausência de um tema na triagem — que é tarde e não se atribui à causa.

    O PDF do comentário anterior (``anterior*.pdf``) não entra: ele vai para o
    campo próprio, por ``anterior_em_pdf``.
    """
    if not origem.is_dir():
        return Conversao()

    pdfs = sorted(p for p in origem.iterdir()
                  if p.is_file() and p.suffix.lower() == ".pdf"
                  and not e_anterior(p))
    # Arquivo oculto não conta: .gitkeep e afins não são fonte que alguém
    # esperava ver no comentário.
    ignorados = sorted(p.name for p in origem.iterdir()
                       if p.is_file() and p.suffix.lower() != ".pdf"
                       and not p.name.startswith("."))
    if not pdfs:
        return Conversao(ignorados=ignorados)

    blocos: list[str] = []
    vazios: list[str] = []

    for pdf in pdfs:
        try:
            texto = _texto_do_pdf(pdf)
        except Exception as e:  # noqa: BLE001 — um PDF ruim não derruba a coleta
            print(f"Aviso: falha ao ler {pdf.name} ({type(e).__name__}: {e})",
                  file=sys.stderr)
            vazios.append(pdf.name)
            continue

        if not texto:
            vazios.append(pdf.name)
            continue

        blocos.append(f"### FONTE: {pdf.name}\n\n{texto}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n\n---\n\n".join(blocos), encoding="utf-8")
    return Conversao(len(blocos), vazios, ignorados)
