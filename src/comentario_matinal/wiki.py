"""Publica o manual do plantão no Wiki do GitHub.

A fonte é `docs/plantao/`, que a suíte afere. O que sai daqui é cópia, e cada
página diz isso e de qual commit veio: não há como aferir por teste uma cópia
que mora noutro repositório git, então a honestidade fica no próprio texto,
onde o leitor a encontra sem procurar.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from comentario_matinal.config import MANUAL, RAIZ

# O endereço de verdade. Fica num nome de módulo, e não dentro de main(), para
# que um teste possa trocá-lo por um `git init --bare` descartável sem tocar
# em linha de comando alguma — nenhuma bandeira nova, nenhuma superfície a
# mais para quem só quer publicar.
URL_WIKI = "git@github.com:marc3lom/mkt_intelligence.wiki.git"

# O clone do wiki fica ao lado do repositório, nunca dentro: é outro repositório
# git. `RAIZ` é o topo deste; o clone vai para a pasta que o contém.
DESTINO_PADRAO = RAIZ.parent / "mkt_intelligence.wiki"

FAIXA = (
    "> Gerado a partir de `docs/plantao/{origem}` no commit `{sha}`.\n"
    "> Não editar aqui — a edição se perde na próxima publicação.\n\n"
)

_LIGACAO = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


# `01-primeiro-dia.md` vira `Primeiro-dia.md`; o índice vira a capa do wiki.
def _nome_no_wiki(caminho: Path) -> str:
    if caminho.name == "README.md":
        return "Home.md"
    miolo = caminho.stem.split("-", 1)[1]
    return miolo.capitalize() + ".md"


def _sha() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, check=True,
                          cwd=RAIZ).stdout.decode().strip()


def _reescreve_links(texto: str, paginas: dict[str, str]) -> str:
    """Troca `02-instalacao.md` por `Instalacao`, o nome que a página tem no wiki.

    A âncora depois de `#`, quando existe, atravessa sem ser tocada. Recalculá-la
    a partir do título exigiria reproduzir a regra do GitHub para transformar
    título em âncora — que não colapsa espaços repetidos: um travessão cercado
    de espaços ("Passo 8 — Conferência") vira `passo-8--conferência`, com hífen
    duplo, porque o travessão some e as duas espaços ao redor dele sobram, cada
    uma virando o seu próprio hífen. Recalcular arrisca fazer essa colapsagem
    por engano e produzir um link que parece certo e não resolve. A âncora que
    já está escrita foi gerada pelo próprio GitHub; ela atravessa por cópia.

    Link para fora do manual (`../../README.md`, URL externa, âncora da própria
    página) não é desta função — passa como está. Link para um `.md` do manual
    que não bate com página alguma das seis é erro, não aviso: no wiki ele
    nasceria como página vazia, criada sem querer no primeiro clique.
    """

    def _troca(encontrado: re.Match[str]) -> str:
        rotulo, destino = encontrado.group(1), encontrado.group(2)
        if "://" in destino or destino.startswith(("../", "/", "#")):
            return encontrado.group(0)
        arquivo, _, ancora = destino.partition("#")
        if not arquivo.endswith(".md"):
            return encontrado.group(0)
        if arquivo not in paginas:
            raise ValueError(
                f"link para {arquivo!r}, que não é página do manual "
                f"(conhecidas: {sorted(paginas)})"
            )
        novo_destino = paginas[arquivo] + (f"#{ancora}" if ancora else "")
        return f"[{rotulo}]({novo_destino})"

    return _LIGACAO.sub(_troca, texto)


def monta(destino: Path, sha: str) -> list[Path]:
    """Escreve as páginas no clone do wiki e devolve o que gravou."""
    fontes = sorted(MANUAL.glob("*.md"))
    paginas = {fonte.name: Path(_nome_no_wiki(fonte)).stem for fonte in fontes}

    escritas = []
    for fonte in fontes:
        conteudo = _reescreve_links(fonte.read_text(encoding="utf-8"), paginas)
        faixa = FAIXA.format(origem=fonte.name, sha=sha)
        alvo = destino / _nome_no_wiki(fonte)
        alvo.write_text(faixa + conteudo, encoding="utf-8")
        escritas.append(alvo)
    return escritas


def _clona_ou_atualiza(destino: Path) -> None:
    """Clona `URL_WIKI` em `destino`, ou atualiza se já for um clone dali.

    Antes de a primeira página do wiki nascer pela interface do GitHub, o
    repositório não existe e o clone responde "repository not found" — ver a
    seção do Wiki em `docs/plantao/02-instalacao.md`.
    """
    if (destino / ".git").is_dir():
        subprocess.run(["git", "pull", "--ff-only"], cwd=destino, check=True)
        return
    destino.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "clone", URL_WIKI, str(destino)],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError as erro:
        raise RuntimeError(
            "Não consegui clonar o Wiki. Se `mkt_intelligence.wiki.git` ainda "
            "não existe, crie a primeira página pela aba Wiki no GitHub — ver "
            "a seção do Wiki em docs/plantao/02-instalacao.md."
        ) from erro


def _comita(destino: Path, sha: str) -> bool:
    """Comita o que `monta` gravou. Devolve False quando não há nada novo."""
    subprocess.run(["git", "add", "-A"], cwd=destino, check=True)
    resultado = subprocess.run(
        ["git", "commit", "-m", f"Manual do plantão em {sha}"],
        cwd=destino, capture_output=True,
    )
    return resultado.returncode == 0


def main() -> int:
    """Clona ou atualiza o wiki, monta as páginas, comita e empurra.

    `--sem-push` para quando quiser conferir antes: monta, comita no clone e
    para, imprimindo o comando que falta.
    """
    analisador = argparse.ArgumentParser(
        description="Publica o manual do plantão (docs/plantao/) no Wiki do GitHub."
    )
    analisador.add_argument(
        "--sem-push", action="store_true",
        help="monta e comita no clone local; não empurra, e imprime o comando que falta",
    )
    analisador.add_argument(
        "--destino", type=Path,
        default=DESTINO_PADRAO,
        help="pasta do clone do wiki (padrão: ao lado deste repositório)",
    )
    args = analisador.parse_args()

    sha = _sha()
    _clona_ou_atualiza(args.destino)
    escritas = monta(args.destino, sha)

    if not _comita(args.destino, sha):
        print("Nada mudou desde a última publicação — nenhum commit novo.")
        return 0

    if args.sem_push:
        print(f"{len(escritas)} página(s) montada(s) e comitada(s) em {args.destino}.")
        print(f"Falta: git -C {args.destino} push -u origin HEAD")
        return 0

    subprocess.run(["git", "push", "-u", "origin", "HEAD"],
                   cwd=args.destino, check=True)
    print(f"{len(escritas)} página(s) publicada(s) no Wiki.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
