"""A documentação e o código não podem divergir em silêncio.

Documentação envelhece sem avisar, e quem a lê não tem como saber que
envelheceu. O que dá para aferir por máquina — que comando existe, que passo
existe, que horas a janela tem, que pasta o código usa — é aferido aqui, na
suíte de sempre. O resto é prosa, e prosa é responsabilidade de quem escreve.
"""

import re
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
MANUAL = RAIZ / "docs" / "plantao"
# Os dois arquivos de agente entram aqui pelo mesmo motivo que o README: são
# lidos como verdade sobre este repositório, e ninguém os confere. Eram os
# únicos documentos fora da aferição, e foi neles que sobreviveram uma contagem
# de testes velha, uma norma de língua que o código contradizia e uma afirmação
# sobre qual prompt cita qual seção do guia.
DOCUMENTOS = sorted(MANUAL.glob("*.md")) + [
    RAIZ / "README.md",
    RAIZ / "AGENTS.md",
    RAIZ / "CLAUDE.md",
]

# O guia entra na aferição da janela porque o modelo o lê em toda etapa: uma
# janela errada ali não confunde o leitor, confunde a triagem.
GUIA = RAIZ / "prompts" / "00_guia_de_estilo.md"

# Pares de horas que NÃO são a janela do plantão, com o motivo de cada um. Sem
# esta lista o teste ficaria vermelho num documento correto; com ela, cada par
# novo obriga alguém a dizer o que é.
HORAS_QUE_NAO_SAO_A_JANELA = {
    "3h e 6h": "releases europeus e britânicos, em hora de Nova York",
}

# Um intervalo de horas em qualquer das quatro redações que os documentos usam:
# "entre 7h00 e 9h00", "7h–9h", "7h00 às 9h00", "07h00 a 09h00".
#
# Os minutos entram na captura, e não como `(?:...)` descartado: sem eles a
# aferição comparava só a hora, e uma janela que abrisse às 7h30 deixaria todo
# "7h00 às 9h00" da prosa passar por certo. Onde o documento escreve só a hora
# — "7h–9h" —, a leitura é de hora cheia, que é o que o leitor entende.
RE_INTERVALO = re.compile(
    r"(\d{1,2})\s*h(\d{2})?\s*(?:às|as|até|a|e|–|-)\s*(\d{1,2})\s*h(\d{2})?",
    re.IGNORECASE,
)

# Caminho escrito entre crases: `saida/`, `arquivo/AAAA/MM/`, `config/painel.toml`.
RE_CAMINHO = re.compile(r"`([\w.-]+)/[\w./-]*`")

# Uma ligação de Markdown: `[o que se lê](para onde vai)`.
RE_LIGACAO = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# Um título de Markdown, e a cerca que abre ou fecha um bloco de código — dentro
# dela um `#` é conteúdo, não título.
RE_TITULO = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
RE_CERCA = re.compile(r"^\s*(?:```|~~~)")

# O que parece pasta e é molde. Mesma ideia da lista de horas: sem ela o teste
# ficaria vermelho num documento correto, e com ela um molde novo obriga alguém
# a dizer que é molde.
CAMINHOS_QUE_SAO_MOLDE = {
    "AAAA": "molde de data em `arquivo/AAAA/MM/AAAAMMDD.md`",
}

# Executáveis que o manual ensina e que não saem deste repositório: vêm de uma
# dependência, e o `uv run` os alcança pelo ambiente. Mesma ideia das listas
# acima — sem ela o teste chamaria de fantasma um comando que existe.
EXECUTAVEIS_DE_TERCEIROS = {
    "nbstripout": "filtro de notebook, do grupo `dev`; instalado uma vez por clone",
    "pytest": "o portão de verificação, do grupo `dev`; é o comando que os "
              "arquivos de agente mandam rodar antes de dizer que algo está pronto",
}

# As bandeiras que o manual deliberadamente não ensina, com o motivo. Todas
# apontam para outro lugar as pastas que o plantão usa por padrão, e mexer nelas
# é ensaio ou teste — não é o plantão.
BANDEIRAS_FORA_DO_MANUAL = {
    "--saida": "as saídas do dia vão para `saida/`; apontar outra é reprocessar",
    "--fontes": "os PDFs da manhã ficam em `fontes/`, na pasta do produto",
    "--arquivo": "o comentário do dia anterior sai de `arquivo/`, onde o "
                 "`enviado` o grava",
    "--config": "a lista de ativos do painel é única — `config/painel.toml`",
    "--template": "o documento sai do template da mesa; outro é ensaio de "
                  "formatação",
}


def _texto(caminhos) -> str:
    return "\n".join(c.read_text(encoding="utf-8") for c in caminhos)


def test_todo_subcomando_do_terminal_esta_documentado():
    from comentario_matinal.cli import SUBCOMANDOS

    texto = _texto(DOCUMENTOS)
    faltando = sorted(c for c in SUBCOMANDOS if f"matinal {c}" not in texto)
    assert not faltando, (
        f"Os subcomandos {faltando} existem e a documentação não os menciona. "
        "Quem aprender o plantão por ela não saberá que existem."
    )


def test_todo_comando_documentado_existe():
    """O erro mais provável depois de uma mudança: a documentação segue mostrando
    o que já não há."""
    from comentario_matinal.cli import SUBCOMANDOS

    citados = set(re.findall(r"uv run matinal (\w+)", _texto(DOCUMENTOS)))
    fantasmas = sorted(citados - set(SUBCOMANDOS))
    assert not fantasmas, (
        f"A documentação manda rodar {fantasmas}, que não existe(m). "
        f"Os subcomandos são {list(SUBCOMANDOS)}."
    )


def _executaveis_instalados() -> set[str]:
    """O que `uv run` alcança por instalação deste repositório.

    Sai de `[project.scripts]` do `pyproject.toml`, e não de uma lista escrita
    aqui: entrada nova no `pyproject` fica coberta sem que ninguém precise
    lembrar deste arquivo, e entrada removida derruba na hora a página que
    seguia ensinando o comando.
    """
    from comentario_matinal.config import RAIZ as TOPO

    with (TOPO / "pyproject.toml").open("rb") as arquivo:
        return set(tomllib.load(arquivo)["project"]["scripts"])


def test_todo_executavel_ensinado_pelo_manual_existe():
    """`matinal` não é o único comando do repositório, e o teste acima só o via.

    `uv run publica-wiki` entrou no manual sem que nada provasse que existe: o
    padrão aferido era `uv run matinal (\\w+)`, e um executável novo passava
    inteiro por fora dele. O leitor que digita um comando inexistente não tem
    como saber se errou ele ou o manual.
    """
    citados = set(re.findall(r"uv run ([a-z][\w-]*)", _texto(DOCUMENTOS)))
    reais = _executaveis_instalados()
    fantasmas = sorted(c for c in citados
                       if c not in reais and c not in EXECUTAVEIS_DE_TERCEIROS)
    assert not fantasmas, (
        f"A documentação manda rodar `uv run {fantasmas}`, que não está em "
        f"[project.scripts]. Instalados por este repositório: {sorted(reais)}. "
        "Se algum vier de uma dependência, ele entra em "
        "EXECUTAVEIS_DE_TERCEIROS com o motivo."
    )


def _ancora(titulo: str) -> str:
    """O título como o GitHub o transforma em âncora.

    A regra: tira a marcação inline, passa a minúsculas, descarta o que não for
    letra, número, espaço ou hífen, e troca **cada** espaço por um hífen.

    O "cada" é o ponto todo. A regra do GitHub **não colapsa espaços**: em
    "Passo 8 — Conferência" o travessão é descartado e as duas espaços ao redor
    dele sobram, virando `passo-8--conferência`, com hífen duplo. Uma versão
    desta função que colapsasse — `re.sub(r"[\\s-]+", "-", ...)`, que é o que se
    escreve sem pensar — aceitaria como boa a âncora `passo-8-conferência`, que
    não resolve no GitHub. Um teste que aprova link quebrado é pior do que teste
    nenhum, porque cala quem iria conferir à mão.
    """
    texto = re.sub(r"[`*~]", "", titulo.strip().lower())
    texto = re.sub(r"[^\w\s-]", "", texto)
    return re.sub(r"\s", "-", texto)


def _ancoras(caminho: Path) -> set[str]:
    ancoras = set()
    dentro_de_cerca = False
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if RE_CERCA.match(linha):
            dentro_de_cerca = not dentro_de_cerca
            continue
        if dentro_de_cerca:
            continue
        if titulo := RE_TITULO.match(linha):
            ancoras.add(_ancora(titulo.group(1)))
    return ancoras


def test_toda_ancora_do_manual_resolve():
    """Renomear um título quebra os links que apontavam para ele, em silêncio.

    O manual é uma teia de ligações entre páginas, e nenhuma delas avisa quando
    o destino muda de nome: o Markdown do GitHub leva a lugar nenhum, sem erro —
    renomear um título do runbook basta. O publicador do wiki também não apanha:
    ele copia a âncora
    de propósito, porque recalculá-la arriscaria justamente a colapsagem descrita
    em `_ancora`. Quem afere é este teste.
    """
    quebradas = []
    for caminho in DOCUMENTOS:
        for numero, linha in enumerate(
                caminho.read_text(encoding="utf-8").splitlines(), 1):
            for destino in RE_LIGACAO.findall(linha):
                if "://" in destino:
                    continue
                arquivo, separador, ancora = destino.partition("#")
                if not separador:
                    continue
                # Sem arquivo, a âncora é da própria página.
                alvo = (caminho.parent / arquivo) if arquivo else caminho
                # O caminho a partir da raiz, e não só o nome: há dois
                # `README.md` nesta lista, e o do manual é justamente o índice.
                onde = f"{caminho.relative_to(RAIZ).as_posix()}:{numero} → {destino}"
                if not alvo.is_file():
                    quebradas.append(f"{onde} (o arquivo não existe)")
                elif ancora not in _ancoras(alvo):
                    quebradas.append(f"{onde} (nenhum título gera essa âncora)")

    assert not quebradas, (
        f"Ligações que não resolvem: {quebradas}. O destino mudou de nome, ou "
        "de lugar, e o link ficou apontando para o vazio — que é o que o leitor "
        "encontra ao clicar."
    )


def test_o_manual_decide_sobre_toda_bandeira_do_comando(monkeypatch, capsys):
    """Bandeira nova obriga a decidir se o manual a ensina, ou por que não.

    O teste de subcomandos não alcança bandeira, e é por bandeira que passa uma
    parte do processo — `--temas-numeros` é como a decisão editorial entra no
    fluxo. Em 17/08 ela foi acrescentada e o runbook seguiu mandando escrever os
    temas à mão por uma hora, com o problema conhecido. Este teste é o que teria
    acusado.

    A lista sai do `--help`, e não da introspecção do argparse: é o que o autor
    de fato lê quando procura o que existe.
    """
    from comentario_matinal import cli

    monkeypatch.setattr("sys.argv", ["matinal", "--help"])
    with pytest.raises(SystemExit):
        cli.main()

    bandeiras = set(re.findall(r"--[a-z][a-z-]+", capsys.readouterr().out))
    texto = _texto(DOCUMENTOS)
    faltando = sorted(b for b in bandeiras - {"--help"}
                      if b not in BANDEIRAS_FORA_DO_MANUAL and b not in texto)
    assert not faltando, (
        f"As bandeiras {faltando} existem e o manual não as menciona. Se alguma "
        "não for para o plantonista, ela entra em BANDEIRAS_FORA_DO_MANUAL com o "
        "motivo escrito ao lado."
    )


def test_a_janela_citada_na_prosa_bate_com_o_codigo():
    """Ela aparece escrita de quatro formas diferentes, e nenhuma é a do código.

    Por isso o teste afere as HORAS, e não a redação: obrigar uma única forma
    endureceria a prosa sem ganho algum. Muda-se `janela.ABERTURA` e toda menção
    fica vermelha, qualquer que seja como foi escrita.
    """
    from comentario_matinal.janela import ABERTURA, FECHAMENTO

    esperado = (ABERTURA.hour, ABERTURA.minute, FECHAMENTO.hour, FECHAMENTO.minute)
    erradas = []
    for caminho in [*DOCUMENTOS, GUIA]:
        for numero, linha in enumerate(
                caminho.read_text(encoding="utf-8").splitlines(), 1):
            for m in RE_INTERVALO.finditer(linha):
                if m.group(0) in HORAS_QUE_NAO_SAO_A_JANELA:
                    continue
                escrito = (int(m.group(1)), int(m.group(2) or 0),
                           int(m.group(3)), int(m.group(4) or 0))
                if escrito != esperado:
                    erradas.append(f"{caminho.name}:{numero} {m.group(0)!r}")

    assert not erradas, (
        f"A janela do código é {ABERTURA:%Hh%M}–{FECHAMENTO:%Hh%M} e a prosa diz "
        f"outra coisa em: {erradas}. Se algum desses não for a janela, ele entra "
        "em HORAS_QUE_NAO_SAO_A_JANELA com o motivo."
    )


def _pastas_conhecidas() -> set[str]:
    """As pastas que a documentação pode citar sem que o teste as chame de invento.

    O disco não é o invariante. `saida/` e `fontes/` estão no `.gitignore` e só
    passam a existir depois da primeira coleta — um clone recém-feito não as
    tem. E é exatamente quem acabou de clonar, seguindo `02-instalacao.md` e
    rodando a suíte para conferir a instalação, quem um teste vermelho aqui
    mais confundiria: intermitente por construção, porque o próprio passo de
    instalação manda rodar `uv run matinal` de ensaio, e é esse comando que
    cria `saida/`. Vermelho antes dele, verde depois.

    O que vale é o que `config.py` declara como pasta padrão — essas existem
    por contrato, tenham sido criadas ou não — somado ao que de fato está na
    raiz, para as pastas que não vêm de constante alguma (`docs/`, `src/`,
    `tests/`...).
    """
    from comentario_matinal.config import (
        ARQUIVO_PADRAO,
        CONFIG_PADRAO,
        FONTES_PADRAO,
        PROMPTS,
        SAIDA_PADRAO,
        TEMPLATE_PADRAO,
    )

    declaradas = {
        SAIDA_PADRAO.name,
        FONTES_PADRAO.name,
        ARQUIVO_PADRAO.name,
        PROMPTS.name,
        CONFIG_PADRAO.parent.name,
        TEMPLATE_PADRAO.parent.name,
    }
    do_disco = {p.name for p in RAIZ.iterdir() if p.is_dir()}
    return declaradas | do_disco


def test_toda_pasta_citada_existe():
    """Documentação que nomeia pasta inexistente manda o leitor ao lugar errado,
    e ele não tem como saber que o errado é o texto."""
    reais = _pastas_conhecidas()
    citadas = set(RE_CAMINHO.findall(_texto(DOCUMENTOS)))
    inventadas = sorted(c for c in citadas
                        if c not in reais and c not in CAMINHOS_QUE_SAO_MOLDE)
    assert not inventadas, (
        f"A documentação cita {inventadas}, que não existe(m) na raiz do "
        "repositório. Se algum for molde, e não pasta, ele entra em "
        "CAMINHOS_QUE_SAO_MOLDE com o motivo."
    )


def test_o_readme_aponta_para_o_manual():
    """O README é a porta do repositório; o runbook saiu dele."""
    assert "docs/plantao/" in (RAIZ / "README.md").read_text(encoding="utf-8"), (
        "O README não aponta para o manual, e quem chega pelo repositório não "
        "acha o runbook."
    )


# Uma citação de seção do guia, como os documentos a escrevem: "§4", "§7.3",
# "§9.1–§9.5". O travessão da faixa não é lido como intervalo: cada número é
# conferido por si, que é o que torna a aferição barata e exata.
RE_SECAO = re.compile(r"§\s*(\d+(?:\.\d+)?)")

# Os títulos do guia: "## 7. ATRIBUIÇÃO" e "### 7.3 A fonte não viaja com o
# comentário". O número é o que se cita; o título, não.
RE_SECAO_DO_GUIA = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)[.\s]")

# Uma contagem de testes na prosa: "167 testes".
RE_CONTAGEM = re.compile(r"(\d+)\s+testes\b")


def test_toda_secao_do_guia_citada_pela_documentacao_existe():
    """Citar §7.3 é mandar o leitor a um lugar; o lugar tem de estar lá.

    O guia é a fonte única das convenções editoriais, e os documentos o resumem
    por número — "no máximo três atribuições nominais (§7.2)". Um resumo que
    aponta para uma seção inexistente é pior que resumo nenhum: manda conferir
    no original e não deixa conferir.

    A deriva prevista não é erro de digitação, é renumeração. Quando o guia
    ganhar uma seção no meio e as seguintes andarem, nada hoje acusaria os
    ponteiros que ficaram para trás — este teste acusa.
    """
    do_guia = {m.group(1) for m in
               (RE_SECAO_DO_GUIA.match(linha)
                for linha in GUIA.read_text(encoding="utf-8").splitlines())
               if m}
    assert do_guia, "Nenhum título numerado no guia — o formato dele mudou."

    citadas = sorted(
        (doc.name, numero)
        for doc in DOCUMENTOS
        for numero in {m.group(1) for m in
                       RE_SECAO.finditer(doc.read_text(encoding="utf-8"))}
        if numero not in do_guia
    )
    assert not citadas, (
        f"Seções citadas que não existem no guia: {citadas}. Ou o número está "
        "errado, ou o guia foi renumerado e os resumos ficaram apontando para o "
        "lugar antigo."
    )


def test_a_contagem_de_testes_citada_bate_com_a_suite():
    """O número que convida a rodar a suíte não pode ser o de outra suíte.

    Os arquivos de agente anunciam quantos testes existem, e é assim que quem
    chega sabe que o portão é barato de rodar. O número envelhece a cada teste
    novo — envelheceu de 166 para 167 no dia em que a parada do Passo 3 ganhou o
    seu —, e envelhece em silêncio, porque nada o lê.

    A coleta roda num processo à parte, e só coleta: não executa teste nenhum, e
    portanto não há recursão. Sem conseguir coletar, o teste se declara pulado em
    vez de acusar o documento por um problema que é de ambiente.

    A contagem é a desta suíte — a pasta deste arquivo —, não a do repositório:
    teste novo no outro pacote não envelhece este documento.
    """
    import subprocess
    import sys

    citadas = [(doc.name, int(m.group(1)))
               for doc in DOCUMENTOS
               for m in RE_CONTAGEM.finditer(doc.read_text(encoding="utf-8"))]
    if not citadas:
        pytest.skip("nenhum documento anuncia uma contagem de testes")

    try:
        saida = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider", str(Path(__file__).parent)],
            capture_output=True, cwd=RAIZ, check=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip(f"não consegui coletar a suíte: {e}")

    achado = re.search(r"(\d+) tests? collected", saida)
    assert achado, f"A coleta não disse quantos testes achou:\n{saida[-400:]}"
    total = int(achado.group(1))

    erradas = [(nome, n) for nome, n in citadas if n != total]
    assert not erradas, (
        f"A suíte tem {total} testes e a documentação anuncia {erradas}. Teste "
        "novo obriga a atualizar o número, ou a tirá-lo do texto — número que "
        "ninguém mantém é pior que nenhum, porque parece conferido."
    )
