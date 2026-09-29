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
    name = os.environ.get(ENV_BACKEND) or default_backend()
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

# Olhar o arquivo a cada segundo, e só aceitá-lo depois de dois segundos sem
# mudar de tamanho: o agente pode gravar a resposta em mais de um passo.
POLL_INTERVAL = 1.0
STABLE_FOR = 2.0

READ_MARK = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")


def copilot_message(message: str, code: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e, no fim, o código.

    O código vai na última linha: só quem leu o arquivo inteiro o conhece. O
    texto vai em português porque chega ao modelo junto com o prompt da etapa.
    """
    return (
        SYSTEM_PROMPT + SEPARATOR + message.rstrip() + SEPARATOR + "## FIM DA MENSAGEM\n\n"
        "A primeira linha do arquivo de resposta é exatamente "
        f"`<!-- leitura: {code} -->`; a saída pedida começa na linha seguinte.\n"
    )


def strip_read_mark(response: str, code: str, stage: str) -> str:
    """Confere o código de leitura e o tira da resposta."""
    text = response.lstrip("﻿")
    found = READ_MARK.search(text[:500])
    if found is None:
        raise ModelError(
            f"Stage {stage} response has no read mark: the message was not read "
            "to the end. Run the cell again and repeat the command in chat."
        )
    if found.group(1) != code:
        raise ModelError(
            f"Stage {stage} response carries the code of another run. Run the "
            "cell again and repeat the command in chat."
        )
    body = (text[: found.start()] + text[found.end() :]).strip()
    if not body:
        raise ModelError(f"Stage {stage} returned an empty response.")
    return body


def wait_for_response(path: Path, stage: str) -> str:
    """Espera o arquivo de resposta aparecer e parar de crescer."""
    deadline = time.monotonic() + TIMEOUT
    size, since = -1, 0.0
    while time.monotonic() < deadline:
        if path.is_file():
            current = path.stat().st_size
            if current > 0 and current == size:
                if time.monotonic() - since >= STABLE_FOR:
                    return path.read_text(encoding="utf-8")
            else:
                size, since = current, time.monotonic()
        time.sleep(POLL_INTERVAL)
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
        response.unlink(missing_ok=True)

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
        return strip_read_mark(wait_for_response(response, stage), code, stage)


register(Copilot)

# Na última linha de propósito: os backends opcionais importam daqui o
# SYSTEM_PROMPT, o TIMEOUT, o ModelError e o register, que a esta altura já
# existem.
_import_optional()
