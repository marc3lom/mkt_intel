"""O backend do modelo: cópia do matinal, sem chamar o `claude` de verdade."""

import subprocess

import pytest

from reports import _backend_claude, _modelo


class FakeBackend:
    name = "fake"
    calls: list[tuple[str, str]] = []

    def run(self, message, *, stage, model):
        FakeBackend.calls.append((stage, message))
        return "resposta"


@pytest.fixture
def fake_backend(monkeypatch):
    FakeBackend.calls = []
    monkeypatch.setitem(_modelo.BACKENDS, "fake", FakeBackend)
    monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "fake")
    return FakeBackend


class TestRegistry:
    def test_env_var_selects_backend(self, fake_backend):
        """A variável de ambiente escolhe o backend registrado."""
        assert _modelo.run("oi", stage="resumo") == "resposta"
        assert fake_backend.calls == [("resumo", "oi")]

    def test_unknown_backend_raises(self, monkeypatch):
        monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "nao-existe")
        with pytest.raises(_modelo.ModelError, match="nao-existe"):
            _modelo.active_backend()

    def test_default_is_the_local_backend_when_available(self, monkeypatch):
        monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
        monkeypatch.setattr(_backend_claude.ClaudeCode, "available", staticmethod(lambda: True))
        assert _modelo.active_backend().name == "claude-code"

    def test_default_is_copilot_without_a_local_backend(self, monkeypatch):
        monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
        monkeypatch.setattr(_backend_claude.ClaudeCode, "available", staticmethod(lambda: False))
        assert _modelo.default_backend() == "copilot"

    def test_registry_module_does_not_name_the_local_backend(self):
        from pathlib import Path

        assert "claude" not in Path(_modelo.__file__).read_text(encoding="utf-8").lower()


class TestClaudeCode:
    def test_missing_executable_raises(self, monkeypatch):
        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: None)
        with pytest.raises(_modelo.ModelError, match="PATH"):
            _backend_claude.ClaudeCode().run("m", stage="resumo", model=None)

    def test_message_on_stdin_safe_mode_and_no_api_key(self, monkeypatch):
        """Mensagem pela stdin, --safe-mode, ferramentas bloqueadas, chave fora do ambiente."""
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: "C:/claude.exe")
        monkeypatch.setattr(_backend_claude.subprocess, "run", fake_run)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")

        assert _backend_claude.ClaudeCode().run("mensagem", stage="resumo", model=None) == "ok"
        cmd = seen["cmd"]
        assert cmd[:3] == ["C:/claude.exe", "-p", "--safe-mode"]
        assert "--system-prompt" in cmd and _modelo.SYSTEM_PROMPT in cmd
        assert "--disallowed-tools" in cmd
        assert set(_backend_claude.BLOCKED_TOOLS) <= set(cmd)
        assert "--model" not in cmd
        assert seen["kwargs"]["input"] == "mensagem"
        assert "ANTHROPIC_API_KEY" not in seen["kwargs"]["env"]
        assert seen["kwargs"]["timeout"] == _modelo.TIMEOUT

    def test_model_flag_when_asked(self, monkeypatch):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_backend_claude.subprocess, "run", fake_run)
        _backend_claude.ClaudeCode().run("m", stage="resumo", model="claude-sonnet-5")
        assert seen["cmd"][-2:] == ["--model", "claude-sonnet-5"]

    def test_nonzero_exit_reports_stdout_reason(self, monkeypatch):
        """A CLI escreve o motivo no stdout ao falhar; o erro tem de trazê-lo."""

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="Not logged in", stderr="")

        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_backend_claude.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="Not logged in"):
            _backend_claude.ClaudeCode().run("m", stage="resumo", model=None)

    def test_empty_response_raises(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="  \n", stderr="")

        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_backend_claude.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="empty"):
            _backend_claude.ClaudeCode().run("m", stage="resumo", model=None)

    def test_timeout_raises(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        monkeypatch.setattr(_backend_claude.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_backend_claude.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="900"):
            _backend_claude.ClaudeCode().run("m", stage="resumo", model=None)
