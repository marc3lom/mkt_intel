"""A documentação e o código não podem divergir em silêncio.

Documentação envelhece sem avisar, e quem a lê não tem como saber que
envelheceu. O que dá para aferir por máquina — que comando existe, que passo
existe, que horas a janela tem, que pasta o código usa — é aferido aqui, na
suíte de sempre. O resto é prosa, e prosa é responsabilidade de quem escreve.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
MANUAL = RAIZ / "docs" / "plantao"
DOCUMENTOS = sorted(MANUAL.glob("*.md")) + [RAIZ / "README.md"]

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
RE_INTERVALO = re.compile(
    r"(\d{1,2})\s*h(?:\d{2})?\s*(?:às|as|até|a|e|–|-)\s*(\d{1,2})\s*h(?:\d{2})?",
    re.IGNORECASE,
)

# Caminho escrito entre crases: `saida/`, `arquivo/AAAA/MM/`, `config/painel.toml`.
RE_CAMINHO = re.compile(r"`([\w.-]+)/[\w./-]*`")

# O que parece pasta e é molde. Mesma ideia da lista de horas: sem ela o teste
# ficaria vermelho num documento correto, e com ela um molde novo obriga alguém
# a dizer que é molde.
CAMINHOS_QUE_SAO_MOLDE = {
    "AAAA": "molde de data em `arquivo/AAAA/MM/AAAAMMDD.md`",
}

# As bandeiras que o manual deliberadamente não ensina, com o motivo. Todas
# apontam para outro lugar as pastas que o plantão usa por padrão, e mexer nelas
# é ensaio ou teste — não é o plantão.
BANDEIRAS_FORA_DO_MANUAL = {
    "--saida": "as saídas do dia vão para `saida/`; apontar outra é reprocessar",
    "--fontes": "os PDFs da manhã ficam em `fontes/`, na raiz",
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

    esperado = (ABERTURA.hour, FECHAMENTO.hour)
    erradas = []
    for caminho in [*DOCUMENTOS, GUIA]:
        for numero, linha in enumerate(
                caminho.read_text(encoding="utf-8").splitlines(), 1):
            for m in RE_INTERVALO.finditer(linha):
                if m.group(0) in HORAS_QUE_NAO_SAO_A_JANELA:
                    continue
                if (int(m.group(1)), int(m.group(2))) != esperado:
                    erradas.append(f"{caminho.name}:{numero} {m.group(0)!r}")

    assert not erradas, (
        f"A janela do código é {esperado[0]}h–{esperado[1]}h e a prosa diz outra "
        f"coisa em: {erradas}. Se algum desses não for a janela, ele entra em "
        "HORAS_QUE_NAO_SAO_A_JANELA com o motivo."
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
