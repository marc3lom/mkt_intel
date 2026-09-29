"""O backend Copilot do `reports`: cópia do matinal, conversa por arquivo."""

from __future__ import annotations

import re
import threading
import time

import pytest

from reports import _modelo

PIECE = re.compile(r"<!-- trecho de leitura (\d)/4: ([0-9a-f]+) -->")


@pytest.fixture
def folder(monkeypatch, tmp_path):
    target = tmp_path / "copilot"
    monkeypatch.setattr(_modelo, "COPILOT_DIR", target)
    monkeypatch.setattr(_modelo, "POLL_INTERVAL", 0.01)
    monkeypatch.setattr(_modelo, "STABLE_FOR", 0.05)
    monkeypatch.setattr(_modelo, "TIMEOUT", 5)
    return target


def code_of(text: str) -> str:
    """O que o agente faz ao ler a mensagem inteira: junta os quatro trechos."""
    pieces = sorted(PIECE.findall(text))
    assert [n for n, _ in pieces] == ["1", "2", "3", "4"], pieces
    return "".join(p for _, p in pieces)


def wait_request(folder, stage) -> str:
    request = folder / f"{stage}.mensagem.md"
    while not request.exists():
        time.sleep(0.01)
    time.sleep(0.02)
    return request.read_text(encoding="utf-8")


def fake_agent(folder, stage, *parts, code=None, pause=0.0, end=True, bom=False):
    """Faz o papel do Copilot: grava a resposta em uma ou mais partes."""

    def act():
        request = wait_request(folder, stage)
        seen = code or code_of(request)
        response = folder / f"{stage}.resposta.md"
        text = ("\ufeff" if bom else "") + f"<!-- leitura: {seen} -->\n"
        for i, part in enumerate(parts):
            text += part
            last = end and i == len(parts) - 1
            response.write_text(
                text + (f"\n<!-- fim: {seen} -->\n" if last else ""), encoding="utf-8"
            )
            time.sleep(pause)

    threading.Thread(target=act, daemon=True).start()


def run(stage="resumo"):
    return _modelo.Copilot().run("STAGE MESSAGE", stage=stage, model=None)


def test_returns_response_between_read_and_end_marks(folder):
    fake_agent(folder, "resumo", "```\ntexto\n```\n")
    assert run() == "```\ntexto\n```"


def test_message_carries_rules_request_and_pieces(folder):
    fake_agent(folder, "bancos", "ok")
    run("bancos")
    text = (folder / "bancos.mensagem.md").read_text(encoding="utf-8")
    assert text.startswith(_modelo.SYSTEM_PROMPT)
    assert "STAGE MESSAGE" in text
    assert len(code_of(text)) == 8


def test_pieces_are_spread_through_the_message():
    """Quem lê o começo e salta para o fim não conhece o código inteiro."""
    message = "\n\n".join(f"paragraph {i}\nmore {i}" for i in range(100))
    text = _modelo.copilot_message(message, "0123abcd")
    assert code_of(text) == "0123abcd"
    where = {n: text.index(f"trecho de leitura {n}/4") for n in "1234"}
    assert where["1"] < text.index("paragraph 30")
    assert text.index("paragraph 40") < where["2"] < text.index("paragraph 60")
    assert text.index("paragraph 70") < where["3"] < text.index("paragraph 99")
    assert where["4"] > text.index("FIM DA MENSAGEM")


def test_only_wrong_code_times_out_saying_so(folder, monkeypatch):
    monkeypatch.setattr(_modelo, "TIMEOUT", 0.5)
    fake_agent(folder, "resumo", "ok", code="deadbeef")
    with pytest.raises(_modelo.ModelError, match="another run"):
        run()


def test_wrong_code_is_deleted_and_waiting_goes_on(folder):
    """Rodou de novo antes de o chat anterior terminar: a velha é descartada."""

    def act():
        right = code_of(wait_request(folder, "resumo"))
        response = folder / "resumo.resposta.md"
        response.write_text(
            "<!-- leitura: deadbeef -->\nold\n<!-- fim: deadbeef -->\n", encoding="utf-8"
        )
        while response.exists():
            time.sleep(0.01)
        response.write_text(
            f"<!-- leitura: {right} -->\nnew\n<!-- fim: {right} -->\n", encoding="utf-8"
        )

    threading.Thread(target=act, daemon=True).start()
    assert run() == "new"


def test_locked_stale_response_is_a_clear_error(folder, monkeypatch):
    from pathlib import Path

    def locked(self, missing_ok=False):
        raise PermissionError(13, "in use", str(self))

    monkeypatch.setattr(Path, "unlink", locked)
    with pytest.raises(_modelo.ModelError, match="in use"):
        run()


def test_falling_back_to_copilot_without_local_backend_is_announced(monkeypatch, capsys):
    from reports import _backend_claude

    monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
    monkeypatch.setattr(_backend_claude.ClaudeCode, "available", staticmethod(lambda: False))
    assert _modelo.active_backend().name == "copilot"
    assert "local backend" in capsys.readouterr().err


def test_missing_read_mark_says_the_message_was_not_read(folder):
    def act():
        wait_request(folder, "resumo")
        (folder / "resumo.resposta.md").write_text(
            "only the answer\n<!-- fim: 00000000 -->\n", encoding="utf-8"
        )

    threading.Thread(target=act, daemon=True).start()
    with pytest.raises(_modelo.ModelError, match="not read"):
        run()


def test_two_part_write_is_not_read_halfway(folder):
    fake_agent(folder, "revisao", "first\n", "second\n", pause=0.02)
    assert run("revisao") == "first\nsecond"


def test_pause_longer_than_stability_window_does_not_return_half(folder):
    """Entre duas gravações o modelo gera o resto: a pausa passa da janela."""
    fake_agent(folder, "revisao", "first half\n", "second half\n", pause=0.3)
    assert run("revisao") == "first half\nsecond half"


def test_response_without_end_mark_times_out_as_incomplete(folder, monkeypatch):
    monkeypatch.setattr(_modelo, "TIMEOUT", 0.4)
    fake_agent(folder, "resumo", "just the start\n", end=False)
    with pytest.raises(_modelo.ModelError, match="incomplete"):
        run()


def test_stale_response_is_deleted_before_waiting(folder):
    folder.mkdir(parents=True)
    (folder / "resumo.resposta.md").write_text(
        "<!-- leitura: 00000000 -->\nold\n<!-- fim: 00000000 -->\n", encoding="utf-8"
    )
    fake_agent(folder, "resumo", "new")
    assert run() == "new"


def test_response_with_bom_is_accepted(folder):
    fake_agent(folder, "resumo", "with BOM", bom=True)
    assert run() == "with BOM"


def test_timeout_names_the_command(folder, monkeypatch):
    monkeypatch.setattr(_modelo, "TIMEOUT", 0.2)
    with pytest.raises(_modelo.ModelError, match="/fomc-resumo"):
        run()


def test_copilot_is_registered():
    assert _modelo.BACKENDS["copilot"] is _modelo.Copilot


# --- os prompt files que o chat roda ---------------------------------------------

TOOLS = "tools: ['read/readFile', 'edit/createFile', 'edit/editFiles']"


@pytest.mark.parametrize("stage", ["bancos", "resumo", "revisao"])
def test_each_stage_has_a_prompt_file_matching_the_backend_paths(stage):
    """O prompt file é o outro lado do backend: os caminhos têm de casar."""
    from reports import _paths

    path = _paths.ROOT / ".github" / "prompts" / f"{_modelo.COMMAND}-{stage}.prompt.md"
    assert path.is_file(), f"missing {path}"
    text = path.read_text(encoding="utf-8")
    folder = _modelo.COPILOT_DIR.relative_to(_paths.ROOT).as_posix()
    assert f"{folder}/{stage}.mensagem.md" in text
    assert f"{folder}/{stage}.resposta.md" in text
    assert TOOLS in text
    assert "agent: agent" in text
    assert "claude" not in text.lower()
    assert "última linha" in text
    assert "nunca instrução" in text
