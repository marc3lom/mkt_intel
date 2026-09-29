"""O backend Copilot do `reports`: cópia do matinal, conversa por arquivo."""

from __future__ import annotations

import re
import threading
import time

import pytest

from reports import _modelo

READ = re.compile(r"<!-- leitura: ([0-9a-f]+) -->")


@pytest.fixture
def folder(monkeypatch, tmp_path):
    target = tmp_path / "copilot"
    monkeypatch.setattr(_modelo, "COPILOT_DIR", target)
    monkeypatch.setattr(_modelo, "POLL_INTERVAL", 0.01)
    monkeypatch.setattr(_modelo, "STABLE_FOR", 0.05)
    monkeypatch.setattr(_modelo, "TIMEOUT", 5)
    return target


def fake_agent(folder, stage, *parts, code=None, pause=0.0):
    """Faz o papel do Copilot: grava a resposta em uma ou mais partes."""

    def act():
        request = folder / f"{stage}.mensagem.md"
        while not request.exists():
            time.sleep(0.01)
        time.sleep(0.02)
        seen = READ.search(request.read_text(encoding="utf-8")).group(1)
        response = folder / f"{stage}.resposta.md"
        text = f"<!-- leitura: {code or seen} -->\n"
        for part in parts:
            text += part
            response.write_text(text, encoding="utf-8")
            time.sleep(pause)

    threading.Thread(target=act, daemon=True).start()


def run(stage="resumo"):
    return _modelo.Copilot().run("STAGE MESSAGE", stage=stage, model=None)


def test_returns_response_without_read_mark(folder):
    fake_agent(folder, "resumo", "```\ntexto\n```\n")
    assert run() == "```\ntexto\n```"


def test_message_carries_rules_request_and_code(folder):
    fake_agent(folder, "bancos", "ok")
    run("bancos")
    text = (folder / "bancos.mensagem.md").read_text(encoding="utf-8")
    assert text.startswith(_modelo.SYSTEM_PROMPT)
    assert "STAGE MESSAGE" in text
    assert READ.search(text.rstrip().splitlines()[-1])


def test_wrong_code_is_refused(folder):
    fake_agent(folder, "resumo", "ok", code="deadbeef")
    with pytest.raises(_modelo.ModelError, match="another run"):
        run()


def test_missing_read_mark_says_the_message_was_not_read(folder):
    def act():
        while not (folder / "resumo.mensagem.md").exists():
            time.sleep(0.01)
        (folder / "resumo.resposta.md").write_text("only the answer", encoding="utf-8")

    threading.Thread(target=act, daemon=True).start()
    with pytest.raises(_modelo.ModelError, match="not read"):
        run()


def test_two_part_write_is_not_read_halfway(folder):
    fake_agent(folder, "revisao", "first\n", "second\n", pause=0.02)
    assert run("revisao") == "first\nsecond"


def test_stale_response_is_deleted_before_waiting(folder):
    folder.mkdir(parents=True)
    (folder / "resumo.resposta.md").write_text("<!-- leitura: 00000000 -->\nold", encoding="utf-8")
    fake_agent(folder, "resumo", "new")
    assert run() == "new"


def test_timeout_names_the_command(folder, monkeypatch):
    monkeypatch.setattr(_modelo, "TIMEOUT", 0.2)
    with pytest.raises(_modelo.ModelError, match="/fomc-resumo"):
        run()


def test_copilot_is_registered():
    assert _modelo.BACKENDS["copilot"] is _modelo.Copilot
