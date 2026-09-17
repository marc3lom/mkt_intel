"""Fixtures globais dos testes: nenhum teste alcança o `claude` de verdade.

A autouse instala, para todo teste, um backend registrado cujo `run` recusa
sempre. Um teste que precisa de resposta controlada instala o próprio dublê
(via `monkeypatch.setitem(_modelo.BACKENDS, ...)` + `INFORMES_EVENTOS_BACKEND`)
depois desta fixture rodar, e essa instalação vence — o `monkeypatch` é o mesmo
objeto ao longo do teste, então o `setenv`/`delenv` do teste simplesmente
sobrescreve o que a autouse fez.
"""

import pytest

from reports import _modelo


class _RefusingBackend:
    """Dublê padrão: nenhum teste chega ao `claude` sem instalar o seu próprio."""

    name = "refusing"

    def run(self, message: str, *, stage: str, model: str | None) -> str:
        raise _modelo.ModelError("Tests must install a fake backend")


@pytest.fixture(autouse=True)
def _no_real_model_backend(monkeypatch):
    monkeypatch.setitem(_modelo.BACKENDS, _RefusingBackend.name, _RefusingBackend)
    monkeypatch.setenv(_modelo.ENV_BACKEND, _RefusingBackend.name)
