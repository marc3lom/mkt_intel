"""Segredos da Environment do 1Password, lidos pelo SDK Python.

Precedência de `get_secret`: a variável já presente no ambiente do processo,
depois a Environment. O ambiente vem primeiro para que testes e CI possam
injetar um valor sem tocar o 1Password.

Autenticação: `OP_SERVICE_ACCOUNT_TOKEN`, se estiver definido; senão o app
desktop, que precisa estar aberto e destravado. A Environment e a conta são
endereços, não segredos, e podem ser trocadas por `OP_ENVIRONMENT_ID` e
`OP_ACCOUNT_NAME`.

Nada aqui escreve segredo em disco nem em log.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from functools import cache

logger = logging.getLogger(__name__)

ENVIRONMENT_ID = os.environ.get("OP_ENVIRONMENT_ID", "vdsbvcx7ijygd2gl3novvn5dhe")
ACCOUNT_NAME = os.environ.get("OP_ACCOUNT_NAME", "my.1password.com")
TIMEOUT_SECONDS: float = 120

_INTEGRATION_NAME = "mkt_intelligence"
_INTEGRATION_VERSION = "1"


async def _fetch_variables() -> dict[str, str]:
    """Autentica e devolve as variáveis da Environment como dicionário."""
    from onepassword import Client, DesktopAuth

    token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
    auth = token or DesktopAuth(account_name=ACCOUNT_NAME)
    client = await Client.authenticate(
        auth=auth,
        integration_name=_INTEGRATION_NAME,
        integration_version=_INTEGRATION_VERSION,
    )
    response = await client.environments.get_variables(ENVIRONMENT_ID)
    return {variable.name: variable.value for variable in response.variables}


@cache
def environment_variables() -> dict[str, str]:
    """Variáveis da Environment, buscadas uma única vez por processo.

    A corrotina roda numa thread própria, com event loop próprio: dentro do
    Jupyter já existe um loop rodando, e `asyncio.run()` direto levantaria.

    A thread é daemon e a espera tem teto. Um prompt biométrico sem resposta
    não pode pendurar o notebook, e uma thread presa não pode segurar a saída
    do interpretador.

    Raises:
        TimeoutError: se o 1Password não responder dentro do prazo.
        Exception: o que o SDK levantar (app fechado, sessão expirada,
            Environment inexistente). Falha não fica em cache: a próxima
            chamada tenta de novo.
    """
    result: dict[str, dict[str, str]] = {}
    failure: list[Exception] = []

    def run() -> None:
        try:
            result["ok"] = asyncio.run(_fetch_variables())
        except Exception as exc:
            failure.append(exc)

    worker = threading.Thread(target=run, name="onepassword-env", daemon=True)
    worker.start()
    worker.join(TIMEOUT_SECONDS)

    if worker.is_alive():
        raise TimeoutError(f"1Password did not answer within {TIMEOUT_SECONDS} s")
    if failure:
        raise failure[0]
    return result["ok"]


def get_secret(name: str) -> str | None:
    """Valor de `name`: do ambiente do processo, ou da Environment do 1Password.

    Devolve `None` em toda falha — variável ausente, app fechado, prompt sem
    resposta —, para que quem chama emita uma mensagem única e útil em vez de
    repassar o erro do SDK. A causa vai para o log, sem o valor.
    """
    value = os.environ.get(name)
    if value:
        return value
    try:
        return environment_variables().get(name) or None
    except Exception as exc:
        logger.warning(
            "1Password Environment unavailable while reading %s: %s: %s",
            name,
            type(exc).__name__,
            exc,
        )
        return None
