"""Leitura de segredos da Environment do 1Password (sem tocar o 1Password)."""

from __future__ import annotations

import asyncio
import logging

import pytest

from reports import _onepassword_env as onepassword_env


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Cada teste começa sem FRED_API_KEY no ambiente e com o cache vazio."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("OP_SERVICE_ACCOUNT_TOKEN", raising=False)
    onepassword_env.environment_variables.cache_clear()
    yield
    onepassword_env.environment_variables.cache_clear()


def fake_environment(monkeypatch, variables=None, error=None):
    """Substitui a busca na Environment, e devolve o contador de chamadas."""
    calls = []

    async def fake():
        calls.append(1)
        if error is not None:
            raise error
        return dict(variables or {})

    monkeypatch.setattr(onepassword_env, "_fetch_variables", fake)
    return calls


def test_process_environment_wins_and_skips_1password(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "from-env")
    calls = fake_environment(monkeypatch, {"FRED_API_KEY": "from-1password"})

    assert onepassword_env.get_secret("FRED_API_KEY") == "from-env"
    assert calls == []


def test_sdk_failure_returns_none_and_logs(monkeypatch, caplog):
    fake_environment(monkeypatch, error=RuntimeError("desktop app is locked"))

    with caplog.at_level(logging.WARNING, logger=onepassword_env.__name__):
        assert onepassword_env.get_secret("FRED_API_KEY") is None

    assert "desktop app is locked" in caplog.text


def test_hung_prompt_times_out(monkeypatch):
    """Prompt biométrico sem resposta não pode pendurar o notebook."""
    monkeypatch.setattr(onepassword_env, "TIMEOUT_SECONDS", 0.2)

    async def hang():
        await asyncio.sleep(30)

    monkeypatch.setattr(onepassword_env, "_fetch_variables", hang)

    assert onepassword_env.get_secret("FRED_API_KEY") is None


def test_failure_is_not_cached(monkeypatch):
    """Uma falha passageira (app travado) não pode valer pelo resto do processo."""
    fake_environment(monkeypatch, error=RuntimeError("locked"))
    assert onepassword_env.get_secret("FRED_API_KEY") is None

    fake_environment(monkeypatch, {"FRED_API_KEY": "unlocked"})
    assert onepassword_env.get_secret("FRED_API_KEY") == "unlocked"


def test_works_inside_a_running_event_loop(monkeypatch):
    """O caso do Jupyter: já existe um loop rodando quando o segredo é pedido."""
    fake_environment(monkeypatch, {"FRED_API_KEY": "x"})

    async def notebook_cell():
        return onepassword_env.get_secret("FRED_API_KEY")

    assert asyncio.run(notebook_cell()) == "x"


@pytest.mark.parametrize("token", ["ops_fake-token", None])
def test_auth_uses_service_account_token_when_set(monkeypatch, token):
    import onepassword

    if token:
        monkeypatch.setenv("OP_SERVICE_ACCOUNT_TOKEN", token)
    seen = {}

    class FakeEnvironments:
        async def get_variables(self, environment_id):
            seen["environment_id"] = environment_id

            class Response:
                variables = []

            return Response()

    class FakeClient:
        environments = FakeEnvironments()

        @classmethod
        async def authenticate(cls, auth, integration_name, integration_version):
            seen["auth"] = auth
            return cls()

    monkeypatch.setattr(onepassword, "Client", FakeClient)

    asyncio.run(onepassword_env._fetch_variables())

    if token:
        assert seen["auth"] == token
    else:
        assert isinstance(seen["auth"], onepassword.DesktopAuth)
    assert seen["environment_id"] == onepassword_env.ENVIRONMENT_ID
