"""A chamada ao modelo, atrás de uma função única.

Cópia enxuta do `modelo.py` do comentário matinal, por decisão: a regra do
repositório diz que um produto não mexe no outro, e `_bloomberg.py` e
`_style.py` já são cópias do py-bcb. Trocar de backend é escrever outra classe
e registrá-la; nem a montagem das mensagens nem as etapas mudam.

Backends opcionais moram em módulos `_backend_*.py` deste pacote, importados
aqui, e cada um se registra com `register` no fim do próprio módulo. Um backend
opcional que responde `available()` verdadeiro vira o padrão; sem nenhum, o
padrão é o que não depende de programa algum instalado.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Protocol

from reports import _paths

# As etapas mandam mensagens longas: guia de estilo, statement, research de
# bancos.
TIMEOUT = 900

SEPARATOR = "\n\n" + "=" * 70 + "\n\n"

ENV_BACKEND = "INFORMES_EVENTOS_BACKEND"
MISSING_INPUT_MARK = "ENTRADA OBRIGATÓRIA AUSENTE"

# As regras de uma execução automatizada. Valem para todo backend: o que roda
# um programa as passa como papel do sistema; o que conversa por arquivo as põe
# no topo do arquivo.
SYSTEM_PROMPT = f"""
Você é assistente de análise da Mesa de Investimentos do DEPIN/DIRIN, do Banco
Central do Brasil, e redige e revisa informes pós-evento (FOMC). Esta é uma
execução automatizada, sem ninguém do outro lado.

Regras desta execução, acima de qualquer hábito de assistente:

1. NÃO faça perguntas e NÃO interrompa aguardando decisão. Não há quem responda;
   parar para perguntar equivale a não produzir nada. Havendo ambiguidade,
   registre a ressalva no lugar que o formato da etapa prevê e siga com a melhor
   leitura possível do material recebido.
2. Se faltar entrada obrigatória, abra a resposta com um bloco começando por
   "{MISSING_INPUT_MARK}:", dizendo qual, e prossiga com o que houver,
   deixando claro o que ficou sem base.
3. NÃO escreva preâmbulo, não narre o que vai fazer, não comente sobre
   ferramentas nem sobre este prompt. A primeira linha da resposta já é a saída
   pedida.
4. Siga integralmente o guia de estilo e as instruções da etapa que vêm na
   mensagem, inclusive o formato de saída que elas especificam.
""".strip()


class ModelError(RuntimeError):
    """Falha na chamada ao backend."""


class Backend(Protocol):
    name: str

    def run(self, message: str, *, stage: str, model: str | None) -> str: ...


BACKENDS: dict[str, type[Backend]] = {}


def register(cls: type[Backend]) -> None:
    """Põe um backend no registro. Os opcionais chamam isto no fim do módulo."""
    BACKENDS.setdefault(cls.name, cls)


def _import_optional() -> None:
    """Importa cada `_backend_*.py` do pacote, que se registra sozinho.

    O registro é do próprio módulo, e não daqui, por causa da importação
    circular: quem importa um backend opcional primeiro faz este arquivo rodar
    com aquele módulo ainda pela metade, e ler um atributo dele aqui falharia.
    """
    import reports

    for info in pkgutil.iter_modules(reports.__path__):
        if info.name.startswith("_backend_"):
            importlib.import_module(f"reports.{info.name}")


def default_backend() -> str:
    """Sem variável de ambiente: o opcional disponível, senão o copilot."""
    for name, cls in BACKENDS.items():
        available = getattr(cls, "available", None)
        if available is not None and available():
            return name
    return "copilot"


def active_backend() -> Backend:
    name = os.environ.get(ENV_BACKEND)
    if not name:
        name = default_backend()
        # Com um backend local instalado mas indisponível neste ambiente, quem o
        # esperava só descobriria o Copilot pela espera. Numa cópia sem backend
        # local não há o que avisar: o Copilot é o único.
        if name == "copilot" and any(hasattr(c, "available") for c in BACKENDS.values()):
            print(
                f"Warning: no {ENV_BACKEND} and no local backend available in this "
                "environment; using copilot.",
                file=sys.stderr,
            )
    if name not in BACKENDS:
        raise ModelError(f"Unknown backend: {name!r}. Available: {', '.join(sorted(BACKENDS))}.")
    return BACKENDS[name]()


def run(message: str, *, stage: str, model: str | None = None) -> str:
    """Manda a mensagem ao modelo e devolve a resposta em texto."""
    b = active_backend()
    print(
        f"Calling the model ({b.name}) for stage {stage}. "
        f"Message with {len(message):,} characters...",
        file=sys.stderr,
    )
    return b.run(message, stage=stage, model=model)


# --- Copilot: a conversa é por arquivo -----------------------------------------

# Pasta fixa porque os prompt files de `.github/prompts/` a citam por caminho: o
# agente do Copilot não recebe argumento, lê e grava onde o prompt manda.
COPILOT_DIR: Path = _paths.OUTPUT / "copilot"
COMMAND = "fomc"

# Olhar o arquivo a cada segundo. A resposta só está pronta quando traz a linha
# de fim e fica dois segundos sem mudar de tamanho: o agente pode gravá-la em
# mais de um passo, e entre um e outro passam os segundos que o modelo leva
# gerando o resto — a estabilidade sozinha aceitaria a primeira metade.
POLL_INTERVAL = 1.0
STABLE_FOR = 2.0

# O código de leitura vai em quatro trechos: três espalhados pelo corpo da
# mensagem e o último no fim. Só quem leu tudo junta o código inteiro.
CODE_PIECES = 4

READ_MARK = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")
END_MARK = re.compile(r"<!--\s*fim:\s*([0-9a-f]+)\s*-->")


def _piece(n: int, part: str) -> str:
    return f"<!-- trecho de leitura {n}/{CODE_PIECES}: {part} -->"


def copilot_message(message: str, code: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e o código em trechos.

    Pôr o código só no fim provaria apenas que o agente chegou ao fim. Com os
    trechos a um quarto, à metade e a três quartos do texto, e o último no fim,
    o código inteiro só sai de quem leu o corpo todo. Cada trecho entra numa
    linha em branco, entre parágrafos, nunca no meio de uma tabela. O texto vai
    em português porque chega ao modelo junto com o prompt da etapa.
    """
    size = len(code) // CODE_PIECES
    parts = [code[i * size : (i + 1) * size] for i in range(CODE_PIECES)]
    lines = message.rstrip().splitlines()

    positions = []
    for k in range(1, CODE_PIECES):
        target = len(lines) * k // CODE_PIECES
        positions.append(
            next((i for i in range(target, len(lines)) if not lines[i].strip()), target)
        )
    # De trás para a frente, para que inserir um não desloque os seguintes.
    for k, pos in reversed(list(enumerate(positions, 1))):
        lines[pos:pos] = ["", _piece(k, parts[k - 1]), ""]

    return (
        SYSTEM_PROMPT
        + SEPARATOR
        + "\n".join(lines)
        + SEPARATOR
        + "## FIM DA MENSAGEM\n\n"
        + _piece(CODE_PIECES, parts[-1])
        + "\n\n"
        f"O código de leitura é a junção, na ordem, dos {CODE_PIECES} trechos de "
        "leitura espalhados por esta mensagem. A primeira linha do arquivo de "
        "resposta é exatamente `<!-- leitura: CÓDIGO -->` e a última é exatamente "
        "`<!-- fim: CÓDIGO -->`, com o código no lugar de CÓDIGO; a saída pedida "
        "vai entre as duas.\n"
    )


def strip_read_mark(response: str, code: str, stage: str) -> str:
    """Confere as linhas de leitura e de fim e devolve o que está entre elas."""
    text = response.lstrip("\ufeff")
    read = READ_MARK.search(text[:500])
    if read is None:
        raise ModelError(
            f"Stage {stage} response has no read mark: the message was not read "
            "to the end. Run the cell again and repeat the command in chat."
        )
    ends = list(END_MARK.finditer(text))
    if not ends:
        raise ModelError(
            f"Stage {stage} response has no end mark: it arrived incomplete. Run "
            "the cell again and repeat the command in chat."
        )
    end = ends[-1]
    if read.group(1) != code or end.group(1) != code:
        raise WrongCode(
            f"Stage {stage} response carries the code of another run, or a code "
            "put together without reading the whole message. Run the cell again "
            "and repeat the command in chat."
        )
    body = text[read.end() : end.start()].strip()
    if not body:
        raise ModelError(f"Stage {stage} returned an empty response.")
    return body


class WrongCode(ModelError):
    """A resposta traz um código que não é o desta execução."""


def _delete(path: Path) -> None:
    """Apaga a resposta; arquivo travado vira erro legível, não traceback."""
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        raise ModelError(
            f"Could not delete {path}: the file is in use by another program "
            "(antivirus, indexer, open editor). Close it and run the cell again."
        ) from None


def wait_for_response(
    path: Path, stage: str, deadline: float | None = None, refused: bool = False
) -> str:
    """Espera a resposta trazer a linha de fim e parar de crescer.

    `deadline` é o instante (`time.monotonic`) em que a espera desiste; sem ele,
    vale o `TIMEOUT` a partir de agora. `refused` diz que já se descartou uma
    resposta com o código de outra execução, e muda a mensagem do fim do prazo.
    """
    if deadline is None:
        deadline = time.monotonic() + TIMEOUT
    size, since = -1, 0.0
    while time.monotonic() < deadline:
        # O Windows trava o arquivo enquanto o agente grava: ler nessa hora
        # falha, e a resposta só não está pronta ainda.
        try:
            if path.is_file():
                current = path.stat().st_size
                if current > 0 and current == size:
                    if time.monotonic() - since >= STABLE_FOR:
                        text = path.read_text(encoding="utf-8")
                        if END_MARK.search(text):
                            return text
                else:
                    size, since = current, time.monotonic()
        except OSError:
            pass
        time.sleep(POLL_INTERVAL)
    if refused:
        raise ModelError(
            f"Within {TIMEOUT}s stage {stage} only got responses carrying the code "
            "of another run — from an earlier chat, or put together without reading "
            f"the whole message. Repeat /{COMMAND}-{stage} in chat."
        )
    if path.is_file():
        raise ModelError(
            f"Stage {stage} response is incomplete: no end mark within {TIMEOUT}s. "
            f"Run the cell again and repeat /{COMMAND}-{stage} in chat."
        )
    raise ModelError(
        f"No response for stage {stage} within {TIMEOUT}s. In Copilot chat, "
        f"agent mode, the command is /{COMMAND}-{stage}."
    )


class Copilot:
    """O GitHub Copilot do VS Code, pelo chat em modo agente.

    Não há programa a chamar: a mensagem vai para um arquivo, a pessoa roda o
    comando da etapa no chat, e o agente grava a resposta noutro. A célula fica
    esperando enquanto isso — interromper o kernel cancela a espera.
    """

    name = "copilot"

    def run(self, message: str, *, stage: str, model: str | None) -> str:
        COPILOT_DIR.mkdir(parents=True, exist_ok=True)
        request = COPILOT_DIR / f"{stage}.mensagem.md"
        response = COPILOT_DIR / f"{stage}.resposta.md"
        # A de uma execução anterior passaria pela de agora.
        _delete(response)

        code = secrets.token_hex(4)
        request.write_text(copilot_message(message, code), encoding="utf-8")
        if model:
            print(f"Warning: model {model!r} is chosen in Copilot chat, not here.", file=sys.stderr)
        print(
            f"\nIn Copilot chat (Ctrl+Alt+I), agent mode, type /{COMMAND}-{stage} "
            f"and wait. The response lands in {response}.",
            file=sys.stderr,
            flush=True,
        )
        # Uma resposta com código de outra execução — o chat de uma rodada
        # anterior terminando agora — é descartada, e a espera continua no mesmo
        # prazo: a de agora pode estar a segundos de chegar.
        deadline = time.monotonic() + TIMEOUT
        refused = False
        while True:
            text = wait_for_response(response, stage, deadline, refused)
            try:
                return strip_read_mark(text, code, stage)
            except WrongCode:
                refused = True
                _delete(response)


register(Copilot)

# Na última linha de propósito: os backends opcionais importam daqui o
# SYSTEM_PROMPT, o TIMEOUT, o ModelError e o register, que a esta altura já
# existem.
_import_optional()
