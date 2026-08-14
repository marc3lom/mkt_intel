"""Conversão dos PDFs das fontes do dia para texto.

O insumo das etapas de IA precisa ser o mesmo independentemente do backend: um
modelo lê PDF anexo, outro não, e um terceiro lê de um jeito diferente. Extrair
para texto uma vez, aqui, faz com que trocar o backend não mude o que o modelo
recebe — que é a condição para comparar saídas entre backends.
"""

from __future__ import annotations

import sys
from pathlib import Path


def converte(origem: Path, destino: Path) -> tuple[int, list[str]]:
    """Extrai o texto de todos os PDFs de ``origem`` para um arquivo único.

    Devolve a quantidade de PDFs aproveitados e a lista dos que não renderam
    texto. PDF que não rende texto é quase sempre digitalização sem OCR — o
    arquivo existe, o analista supõe que entrou, e o conteúdo não chegou ao
    modelo. Por isso volta como lista, para virar aviso, e não silêncio.
    """
    from pypdf import PdfReader

    pdfs = sorted(origem.glob("*.pdf")) if origem.is_dir() else []
    if not pdfs:
        return 0, []

    blocos: list[str] = []
    vazios: list[str] = []

    for pdf in pdfs:
        try:
            leitor = PdfReader(str(pdf))
            texto = "\n".join((p.extract_text() or "") for p in leitor.pages).strip()
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
    return len(blocos), vazios
