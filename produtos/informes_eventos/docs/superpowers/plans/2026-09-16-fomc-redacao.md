# Plano de implementação: redação, bancos e revisão do informe do FOMC

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trazer para dentro do `informes_eventos` a redação do resumo do informe do FOMC, o comentário por banco e a revisão de coerência, como etapas de modelo disparadas por células do notebook, sem tirar do autor a decisão do que entra.

**Architecture:** um backend de modelo copiado do comentário matinal (`src/reports/_modelo.py`) chama `claude -p --safe-mode` com a mensagem pela entrada padrão; um módulo novo (`src/reports/fomc/core/drafting.py`) lê a pasta do dia, monta a mensagem em blocos rotulados a partir do guia de estilo e do prompt da etapa, chama o backend, grava a resposta em `output/reports/fomc/<data>/` e devolve o último bloco cercado; o notebook ganha células que chamam essas funções e o Word passa a entender itálico no resumo.

**Tech Stack:** Python 3.14, uv, pandas 3, pdfplumber, python-docx, pytest, ruff. Nenhuma dependência nova.

**Spec:** `docs/superpowers/specs/2026-09-16-fomc-redacao-design.md`

## Global Constraints

- Tudo roda de dentro de `produtos/informes_eventos/`. Instalar é `uv sync --all-packages` na raiz do repositório. Só uv, nunca `pip install`.
- Portão: `uv run pytest`, sem Bloomberg, sem rede, sem o executável `claude`. Lint: `uv run ruff check .` e `uv run ruff format --check .` limpos.
- Identificadores, mensagens de log e de erro em inglês; docstrings, comentários, prompts, guia, saídas e commits em pt-BR.
- Nunca importar `classes.*` nem `comentario_matinal`. `tests/test_independence.py` prende os dois.
- Todo caminho se ancora na raiz do produto, a pasta com o `pyproject.toml`: `input/`, `output/`, `prompts/`.
- Nunca ler, imprimir, comitar ou resumir `input/`, `src/reports/*/input/`, `output/`, `etc/.env`. Testes usam só dados sintéticos em `tmp_path`.
- **Commit só com pedido do autor.** Cada tarefa termina com o diff pronto e a mensagem proposta; o executor não roda `git commit` nem `git push` por conta própria. Quando o autor pedir: commit direto na `main`, mensagem em português, terceira pessoa do presente, até 72 caracteres, sem prefixo nem ponto final, corpo em prosa com o porquê, trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Ruff: linha de 100, aspas duplas, `select = ["E", "F", "W", "I"]`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/reports/_modelo.py` (novo) | chamar o modelo; backend por variável de ambiente; nada de montagem de mensagem |
| `src/reports/fomc/core/drafting.py` (novo) | pasta do dia, insumos, montagem de mensagens, execução de etapas, leitura das saídas |
| `src/reports/fomc/core/word_report.py` (alterar) | marcação inline `*itálico*`/`**negrito**` no resumo e nos bancos |
| `prompts/00_guia_de_estilo.md`, `01_resumo.md`, `02_bancos.md`, `03_revisao.md` (novos) | fonte de verdade editorial |
| `src/reports/fomc/notebooks/fomc_analysis.ipynb` (alterar) | células das etapas; configuração sem campos de texto |
| `tests/test_modelo.py` (novo) | backend, sem `claude` |
| `tests/test_drafting.py` (novo) | tudo de `drafting.py`, com dublê de backend |
| `tests/test_reports_fomc.py` (alterar) | marcação inline no Word; âncoras de raiz |
| `tests/test_independence.py` (alterar) | proibição de importar `comentario_matinal` |
| `AGENTS.md` (alterar) | a seção nova sobre as etapas de modelo |

---

### Task 1: backend do modelo (`_modelo.py`)

**Files:**
- Create: `src/reports/_modelo.py`
- Test: `tests/test_modelo.py`
- Modify: `tests/test_independence.py`

**Interfaces:**
- Produces: `ModelError(RuntimeError)`; `Backend` (Protocol com `name: str` e `run(message, *, stage, model) -> str`); `ClaudeCode`; `BACKENDS: dict[str, type[Backend]]`; `active_backend() -> Backend`; `run(message: str, *, stage: str, model: str | None = None) -> str`; `SYSTEM_PROMPT`, `BLOCKED_TOOLS`, `TIMEOUT`, `MISSING_INPUT_MARK = "ENTRADA OBRIGATÓRIA AUSENTE"`.

- [ ] **Step 1: Estender o teste de independência**

Em `tests/test_independence.py`, acrescentar ao lado de `IMPORTS_CLASSES`:

```python
IMPORTS_MATINAL = re.compile(r"\b(from|import)\s+comentario_matinal\b")
```

e um teste novo na classe:

```python
    def test_no_import_of_comentario_matinal(self):
        """O backend do modelo é cópia, não import: os produtos não se acoplam."""
        files = [*ROOT.glob("src/**/*.py"), *ROOT.glob("src/**/*.ipynb")]
        offenders = sorted(
            str(f.relative_to(ROOT))
            for f in files
            if IMPORTS_MATINAL.search(f.read_text(encoding="utf-8"))
        )
        assert offenders == []
```

- [ ] **Step 2: Escrever os testes do backend, que falham**

Criar `tests/test_modelo.py`:

```python
"""O backend do modelo: cópia do matinal, sem chamar o `claude` de verdade."""

import subprocess

import pytest

from reports import _modelo


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

    def test_default_is_claude_code(self, monkeypatch):
        monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
        assert _modelo.active_backend().name == "claude-code"


class TestClaudeCode:
    def test_missing_executable_raises(self, monkeypatch):
        monkeypatch.setattr(_modelo.shutil, "which", lambda name: None)
        with pytest.raises(_modelo.ModelError, match="PATH"):
            _modelo.ClaudeCode().run("m", stage="resumo", model=None)

    def test_message_on_stdin_safe_mode_and_no_api_key(self, monkeypatch):
        """Mensagem pela stdin, --safe-mode, ferramentas bloqueadas, chave fora do ambiente."""
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

        monkeypatch.setattr(_modelo.shutil, "which", lambda name: "C:/claude.exe")
        monkeypatch.setattr(_modelo.subprocess, "run", fake_run)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")

        assert _modelo.ClaudeCode().run("mensagem", stage="resumo", model=None) == "ok"
        cmd = seen["cmd"]
        assert cmd[:3] == ["C:/claude.exe", "-p", "--safe-mode"]
        assert "--system-prompt" in cmd and _modelo.SYSTEM_PROMPT in cmd
        assert "--disallowed-tools" in cmd
        assert set(_modelo.BLOCKED_TOOLS) <= set(cmd)
        assert "--model" not in cmd
        assert seen["kwargs"]["input"] == "mensagem"
        assert "ANTHROPIC_API_KEY" not in seen["kwargs"]["env"]
        assert seen["kwargs"]["timeout"] == _modelo.TIMEOUT

    def test_model_flag_when_asked(self, monkeypatch):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr(_modelo.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_modelo.subprocess, "run", fake_run)
        _modelo.ClaudeCode().run("m", stage="resumo", model="claude-sonnet-5")
        assert seen["cmd"][-2:] == ["--model", "claude-sonnet-5"]

    def test_nonzero_exit_reports_stdout_reason(self, monkeypatch):
        """A CLI escreve o motivo no stdout ao falhar; o erro tem de trazê-lo."""

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="Not logged in", stderr="")

        monkeypatch.setattr(_modelo.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_modelo.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="Not logged in"):
            _modelo.ClaudeCode().run("m", stage="resumo", model=None)

    def test_empty_response_raises(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="  \n", stderr="")

        monkeypatch.setattr(_modelo.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_modelo.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="empty"):
            _modelo.ClaudeCode().run("m", stage="resumo", model=None)

    def test_timeout_raises(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        monkeypatch.setattr(_modelo.shutil, "which", lambda name: "claude")
        monkeypatch.setattr(_modelo.subprocess, "run", fake_run)
        with pytest.raises(_modelo.ModelError, match="900"):
            _modelo.ClaudeCode().run("m", stage="resumo", model=None)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo.py tests/test_independence.py -q`
Expected: `ModuleNotFoundError: No module named 'reports._modelo'` nos testes novos; o de independência passa.

- [ ] **Step 4: Escrever `src/reports/_modelo.py`**

```python
"""A chamada ao modelo, atrás de uma função única.

Cópia enxuta do `modelo.py` do comentário matinal, por decisão: a regra do
repositório diz que um produto não mexe no outro, e `_bloomberg.py` e
`_style.py` já são cópias do py-bcb. Trocar de backend é escrever outra classe
e registrá-la em BACKENDS; nem a montagem das mensagens nem as etapas mudam.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Protocol

# As etapas mandam mensagens longas: guia de estilo, statement, research de
# bancos. A mensagem vai pela stdin, nunca por argumento — o limite de linha de
# comando do Windows fica em torno de 32 mil caracteres.
TIMEOUT = 900

# Sem ferramenta alguma. Tudo o que a etapa precisa vai injetado na mensagem;
# acesso a arquivo ou à web só acrescentaria não-determinismo e o risco de o
# modelo introduzir fato que não está nos insumos do dia.
BLOCKED_TOOLS = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "NotebookEdit",
    "Glob",
    "Grep",
    "Task",
    "WebSearch",
    "WebFetch",
]

ENV_BACKEND = "INFORMES_EVENTOS_BACKEND"
MISSING_INPUT_MARK = "ENTRADA OBRIGATÓRIA AUSENTE"

# A CLI do Claude Code roda por padrão como agente de programação: descobre
# CLAUDE.md, carrega skills e narra o que vai fazer. O papel é substituído por
# inteiro.
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


class ClaudeCode:
    """Backend padrão: o Claude Code em modo não interativo."""

    name = "claude-code"

    def run(self, message: str, *, stage: str, model: str | None) -> str:
        executable = shutil.which("claude")
        if not executable:
            raise ModelError(
                "The `claude` executable is not on PATH. Install Claude Code "
                f"or point {ENV_BACKEND} to another backend."
            )

        # --safe-mode pula CLAUDE.md, hooks, skills, plugins, MCP e agentes do
        # ambiente do usuário: a etapa tem de render o mesmo em qualquer
        # máquina. (--bare faria o mesmo, mas restringe a autenticação à chave
        # de API, e aqui a autenticação é a sessão do Claude Code.)
        command = [
            executable,
            "-p",
            "--safe-mode",
            "--system-prompt",
            SYSTEM_PROMPT,
            "--disallowed-tools",
            *BLOCKED_TOOLS,
        ]
        # Sem --model vale a configuração da CLI do usuário: fixar o modelo
        # aqui esconderia uma decisão de custo dentro do código.
        if model:
            command += ["--model", model]

        # Uma chave de API esquecida no ambiente tem precedência sobre a sessão
        # e, sem saldo, derruba a etapa em silêncio. Fora do subprocesso.
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        try:
            r = subprocess.run(
                command,
                input=message,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise ModelError(f"Stage {stage} did not answer within {TIMEOUT}s.") from None

        if r.returncode != 0:
            # Ao falhar, a CLI escreve o motivo no stdout ("Not logged in",
            # "Credit balance is too low") e deixa o stderr vazio.
            reason = " ".join(t for t in ((r.stderr or "").strip(), (r.stdout or "").strip()) if t)
            raise ModelError(f"`claude` exited with code {r.returncode}. {reason[-600:]}")

        output = (r.stdout or "").strip()
        if not output:
            raise ModelError(f"Stage {stage} returned an empty response.")
        return output


BACKENDS: dict[str, type[Backend]] = {
    "claude-code": ClaudeCode,
}


def active_backend() -> Backend:
    name = os.environ.get(ENV_BACKEND, "claude-code")
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
```

- [ ] **Step 5: Rodar os testes e o ruff**

Run: `uv run pytest tests/test_modelo.py tests/test_independence.py -q && uv run ruff check . && uv run ruff format --check .`
Expected: todos passam; ruff limpo. Se o `ruff format` reclamar da lista `BLOCKED_TOOLS` ou do `command`, aplicar `uv run ruff format src/reports/_modelo.py`.

- [ ] **Step 6: Propor commit (não executar sem pedido)**

Mensagem proposta:

```
Copia o backend do modelo do matinal para os informes

Corpo: a regra da raiz diz que um produto não mexe no outro, e o precedente aqui é
_bloomberg.py e _style.py, cópias do py-bcb. O backend chama o claude em modo seguro,
sem ferramentas, com a sessão do Claude Code como autenticação. Nenhum teste chama o
executável: subprocess.run é substituído por dublê.
```

---

### Task 2: marcação inline no Word (itálico e negrito)

**Files:**
- Modify: `src/reports/fomc/core/word_report.py:144-153` (`_add_summary`) e `:494-517` (`_add_bank_comments`, `_add_text_with_bold`)
- Test: `tests/test_reports_fomc.py`

**Interfaces:**
- Produces: `_add_marked_text(para, text: str, size=BODY_SIZE) -> None` em `word_report.py`, substituindo `_add_text_with_bold`.

- [ ] **Step 1: Teste que falha**

Acrescentar em `tests/test_reports_fomc.py`, junto aos imports do topo:

```python
from docx import Document

from reports.fomc.core.word_report import _add_marked_text, _add_summary
```

e a classe:

```python
class TestMarkedText:
    def test_italic_bold_and_plain_runs(self):
        """`*x*` vira itálico, `**y**` negrito, o resto fica normal."""
        doc = Document()
        para = doc.add_paragraph()
        _add_marked_text(para, "leitura *hawkish* e **firme** hoje")
        runs = [(r.text, bool(r.italic), bool(r.bold)) for r in para.runs]
        assert runs == [
            ("leitura ", False, False),
            ("hawkish", True, False),
            (" e ", False, False),
            ("firme", False, True),
            (" hoje", False, False),
        ]

    def test_summary_paragraphs_keep_italics(self):
        """O resumo separa parágrafos por linha em branco e aplica a marcação em cada um."""
        doc = Document()
        _add_summary(doc, "Primeiro *dots*.\n\nSegundo.")
        paras = doc.paragraphs
        assert [p.text for p in paras] == ["Primeiro dots.", "Segundo."]
        assert any(r.italic for r in paras[0].runs)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_reports_fomc.py -k "MarkedText" -q`
Expected: `ImportError: cannot import name '_add_marked_text'`.

- [ ] **Step 3: Implementar**

Em `word_report.py`, substituir `_add_text_with_bold` por:

```python
_INLINE_MARK = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def _add_marked_text(para, text: str, size=None) -> None:
    """Adiciona texto ao parágrafo processando `**negrito**` e `*itálico*`.

    O negrito é testado antes do itálico para `**x**` não virar dois itálicos.
    """
    size = size or BODY_SIZE
    for part in _INLINE_MARK.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = para.add_run(part[2:-2])
            _set_run_font(run, size=size, bold=True)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = para.add_run(part[1:-1])
            _set_run_font(run, size=size, italic=True)
        else:
            run = para.add_run(part)
            _set_run_font(run, size=size)
```

Garantir `import re` no topo do módulo (hoje há um `import re` local dentro de `_add_text_with_bold`; mover para o topo e apagar o local). Em `_add_bank_comments`, trocar `_add_text_with_bold(para, comment_text)` por `_add_marked_text(para, comment_text)`. Em `_add_summary`, trocar as duas linhas `run = para.add_run(paragraph_text)` / `_set_run_font(run, size=BODY_SIZE)` por `_add_marked_text(para, paragraph_text)`.

- [ ] **Step 4: Rodar tudo**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: todos passam.

- [ ] **Step 5: Propor commit**

```
Aceita itálico e negrito inline no resumo do informe do FOMC

Corpo: os termos em inglês vão em itálico por regra do guia, e o resumo passará a
vir em markdown das etapas de modelo. A rotina que já tratava negrito nos
comentários dos bancos passa a servir aos dois.
```

---

### Task 3: pasta do dia, headlines e research (`drafting.py`, parte 1)

**Files:**
- Create: `src/reports/fomc/core/drafting.py`
- Test: `tests/test_drafting.py`
- Modify: `tests/test_reports_fomc.py` (classe `TestProjectRootAnchors`)

**Interfaces:**
- Produces: `PROJECT_ROOT: Path`; `PROMPTS_DIR: Path`; `DraftingError(RuntimeError)`; `Headline(text: str, bold: bool)`; `BankSource(name: str, text: str)`; `day_folder(meeting_date: str) -> Path`; `output_folder(meeting_date: str) -> Path`; `read_headlines(path: Path) -> list[Headline]`; `headlines_for_report(headlines: list[Headline]) -> list[dict]`; `read_bank_pdfs(folder: Path) -> tuple[list[BankSource], list[str]]`.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_drafting.py`:

```python
"""As etapas de modelo do informe do FOMC, sem rede, sem Bloomberg e sem `claude`."""

from pathlib import Path

import pytest

from reports.fomc.core import drafting
from reports.fomc.core.drafting import (
    BankSource,
    DraftingError,
    Headline,
    headlines_for_report,
    read_bank_pdfs,
    read_headlines,
)


class TestDayFolders:
    def test_day_and_output_folders_anchor_on_project_root(self):
        assert (
            drafting.day_folder("20260916") == drafting.PROJECT_ROOT / "input" / "fomc" / "20260916"
        )
        assert (drafting.PROJECT_ROOT / "pyproject.toml").is_file()

    def test_output_folder_is_created(self, monkeypatch, tmp_path):
        monkeypatch.setattr(drafting, "PROJECT_ROOT", tmp_path)
        out = drafting.output_folder("20260916")
        assert out == tmp_path / "output" / "reports" / "fomc" / "20260916"
        assert out.is_dir()


class TestReadHeadlines:
    def test_triple_star_marks_bold_and_is_removed(self, tmp_path):
        p = tmp_path / "headlines.txt"
        p.write_text("*** Fed holds\n\n* Fed says X\nPlain line\n", encoding="utf-8")
        assert read_headlines(p) == [
            Headline("Fed holds", True),
            Headline("Fed says X", False),
            Headline("Plain line", False),
        ]

    def test_missing_or_empty_file_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="headlines.txt"):
            read_headlines(tmp_path / "headlines.txt")
        (tmp_path / "headlines.txt").write_text("\n\n", encoding="utf-8")
        with pytest.raises(DraftingError, match="empty"):
            read_headlines(tmp_path / "headlines.txt")

    def test_headlines_for_report_shape(self):
        assert headlines_for_report([Headline("a", True)]) == [{"text": "a", "bold": True}]


class TestReadBankPdfs:
    def test_names_from_filenames_and_ignored_files(self, tmp_path, monkeypatch):
        """Nome do banco = arquivo sem extensão, sublinhado vira espaço; não-PDF é ignorado."""
        (tmp_path / "Goldman_Sachs.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "notas.docx").write_bytes(b"x")

        monkeypatch.setattr(drafting, "_pdf_text", lambda p: "texto do research")
        sources, ignored = read_bank_pdfs(tmp_path)
        assert sources == [BankSource("Goldman Sachs", "texto do research")]
        assert ignored == ["notas.docx"]

    def test_pdf_without_text_is_reported_not_returned(self, tmp_path, monkeypatch):
        (tmp_path / "JPM.pdf").write_bytes(b"%PDF-1.4 fake")
        monkeypatch.setattr(drafting, "_pdf_text", lambda p: "")
        sources, ignored = read_bank_pdfs(tmp_path)
        assert sources == []
        assert ignored == ["JPM.pdf (no extractable text)"]

    def test_no_pdf_raises(self, tmp_path):
        with pytest.raises(DraftingError, match="bancos"):
            read_bank_pdfs(tmp_path)
        with pytest.raises(DraftingError, match="bancos"):
            read_bank_pdfs(tmp_path / "nao-existe")
```

Não se gera PDF nos testes: a extração de texto é isolada em `_pdf_text(path)` e os testes a substituem por dublê. O pdfplumber já é exercitado em produção pelo parser do SEP.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_drafting.py -q`
Expected: `ModuleNotFoundError: No module named 'reports.fomc.core.drafting'`.

- [ ] **Step 3: Implementar a parte 1 de `drafting.py`**

```python
"""Etapas de modelo do informe do FOMC: resumo, bancos e revisão.

Cada etapa monta uma mensagem com o guia de estilo, o prompt da etapa e os
insumos do dia em blocos rotulados, chama o backend de `reports._modelo`,
grava a resposta inteira em output/reports/fomc/<data>/ e devolve o último
bloco cercado, que é o que o notebook consome. Nada roda sozinho: cada etapa
é uma célula que o autor executa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from reports import _modelo

# Raiz do produto: a pasta com o pyproject.toml. TestProjectRootAnchors prende.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROMPTS_DIR = PROJECT_ROOT / "prompts"

STYLE_GUIDE = "00_guia_de_estilo.md"
PROMPT_SUMMARY = "01_resumo.md"
PROMPT_BANKS = "02_bancos.md"
PROMPT_REVIEW = "03_revisao.md"

HEADLINES_FILE = "headlines.txt"
PRESSER_FILE = "coletiva.txt"
BANKS_DIR = "bancos"

OUT_SUMMARY_DECISION = "resumo_decisao.md"
OUT_SUMMARY_PRESSER = "resumo_coletiva.md"
OUT_BANKS = "bancos.md"
OUT_REVIEW = "revisao.md"


class DraftingError(RuntimeError):
    """Falha numa etapa: insumo ausente, resposta sem bloco, backend."""


@dataclass(frozen=True)
class Headline:
    text: str
    bold: bool


@dataclass(frozen=True)
class BankSource:
    name: str
    text: str


# --- pasta do dia --------------------------------------------------------------


def day_folder(meeting_date: str) -> Path:
    """<raiz>/input/fomc/<AAAAMMDD>: headlines.txt, coletiva.txt, bancos/."""
    return PROJECT_ROOT / "input" / "fomc" / meeting_date


def output_folder(meeting_date: str) -> Path:
    """<raiz>/output/reports/fomc/<AAAAMMDD>, criada se não existir."""
    folder = PROJECT_ROOT / "output" / "reports" / "fomc" / meeting_date
    folder.mkdir(parents=True, exist_ok=True)
    return folder


_STAR_PREFIX = re.compile(r"^(\*+)\s*")


def read_headlines(path: Path) -> list[Headline]:
    """Um headline por linha; `***` no início marca destaque e é removido."""
    if not path.is_file():
        raise DraftingError(f"Headlines file not found: {path}")
    headlines: list[Headline] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _STAR_PREFIX.match(line)
        bold = bool(m and len(m.group(1)) >= 3)
        text = _STAR_PREFIX.sub("", line, count=1).strip()
        if text:
            headlines.append(Headline(text, bold))
    if not headlines:
        raise DraftingError(f"Headlines file is empty: {path}")
    return headlines


def headlines_for_report(headlines: list[Headline]) -> list[dict]:
    """O formato que generate_fomc_report espera."""
    return [{"text": h.text, "bold": h.bold} for h in headlines]


def _pdf_text(path: Path) -> str:
    """Texto de todas as páginas, via pdfplumber. Isolado para os testes dublarem."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages).strip()


def read_bank_pdfs(folder: Path) -> tuple[list[BankSource], list[str]]:
    """Um BankSource por PDF; o nome do banco é o nome do arquivo.

    Devolve também a lista do que foi ignorado: arquivos que não são PDF e
    PDFs sem texto extraível.
    """
    if not folder.is_dir():
        raise DraftingError(f"Bank research folder not found: {folder} (expected 'bancos/')")
    files = sorted(p for p in folder.iterdir() if p.is_file())
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    if not pdfs:
        raise DraftingError(f"No PDF in bank research folder: {folder} ('bancos/')")
    ignored = [p.name for p in files if p.suffix.lower() != ".pdf"]
    sources: list[BankSource] = []
    for pdf in pdfs:
        text = _pdf_text(pdf)
        if not text:
            ignored.append(f"{pdf.name} (no extractable text)")
            continue
        sources.append(BankSource(pdf.stem.replace("_", " "), text))
    return sources, ignored
```

(`field` fica importado para a parte 3; se o ruff acusar F401 antes disso, remover e reimportar na Task 5.)

- [ ] **Step 4: Âncora de raiz**

Em `tests/test_reports_fomc.py`, classe `TestProjectRootAnchors`, acrescentar:

```python
    def test_drafting_root_and_prompts(self):
        """As etapas de modelo se ancoram na raiz e os quatro prompts existem."""
        from reports.fomc.core import drafting

        assert (drafting.PROJECT_ROOT / "pyproject.toml").is_file()
        assert drafting.PROMPTS_DIR == drafting.PROJECT_ROOT / "prompts"
```

(A existência dos quatro arquivos entra na Task 6, quando eles forem criados.)

- [ ] **Step 5: Rodar tudo**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: passa.

- [ ] **Step 6: Propor commit**

```
Lê a pasta do dia do informe do FOMC: headlines e research

Corpo: headlines e coletiva passam a ser arquivos colados da Bloomberg, com `***`
marcando destaque; o research dos bancos entra como PDF e o nome do arquivo é o
nome do banco. Tudo em input/fomc/<data>/, fora do git.
```

---

### Task 4: reação de mercado em números (`market_snapshot`)

**Files:**
- Modify: `src/reports/fomc/core/drafting.py`
- Test: `tests/test_drafting.py`

**Interfaces:**
- Consumes: `MARKET_REACTION_PANELS` de `reports.fomc.core.word_export` (lista de `(key, label, fmt, position)`).
- Produces: `PanelSnapshot(key, label, at_decision, last, change)`; `MarketSnapshot(panels: list[PanelSnapshot], last_time: str)`; `market_snapshot(market_data: pd.DataFrame, decision_time: pd.Timestamp) -> MarketSnapshot`; `format_market(snapshot) -> str`.

- [ ] **Step 1: Testes que falham**

Acrescentar a `tests/test_drafting.py`:

```python
import pandas as pd

from reports.fomc.core.data_loader import _TZ_BRT
from reports.fomc.core.drafting import MarketSnapshot, format_market, market_snapshot


def _intraday() -> pd.DataFrame:
    idx = pd.date_range("2026-09-16 14:00", "2026-09-16 16:00", freq="30min", tz=_TZ_BRT)
    # 5 pontos: 14:00, 14:30, 15:00, 15:30, 16:00
    return pd.DataFrame(
        {
            "SPX": [6000.0, 6000.0, 6000.0, 5970.0, 5940.0],
            "UST_2Y": [4.000, 4.000, 4.000, 4.100, 4.130],
            "UST_10Y": [4.400, 4.400, 4.400, 4.430, 4.440],
            "SPREAD_2S10S": [40.0, 40.0, 40.0, 33.0, 31.0],
            "DXY": [100.0, 100.0, 100.0, 100.3, 100.6],
            "VIX": [15.0, 15.0, 15.0, 16.5, 17.0],
        },
        index=idx,
    )


class TestMarketSnapshot:
    def test_levels_and_changes_by_panel_kind(self):
        """Nível na decisão (último ≤ 15:00), último nível e variação no tipo de cada painel."""
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        snap = market_snapshot(_intraday(), decision)
        by_key = {p.key: p for p in snap.panels}
        assert snap.last_time == "16:00"
        assert by_key["SPX"].at_decision == "6.000" and by_key["SPX"].last == "5.940"
        assert by_key["SPX"].change == "−1,0%"
        assert by_key["UST_2Y"].change == "+13,0 p.b."
        assert by_key["UST_10Y"].change == "+4,0 p.b."
        assert by_key["SPREAD_2S10S"].change == "−9,0 p.b."
        assert by_key["DXY"].change == "+0,6%"
        assert by_key["VIX"].change == "+2,00 pts"
        assert set(by_key) == {"SPX", "UST_2Y", "UST_10Y", "SPREAD_2S10S", "DXY", "VIX"}

    def test_format_market_is_one_line_per_panel_with_comma_decimals(self):
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        text = format_market(market_snapshot(_intraday(), decision))
        assert text.splitlines()[0] == "Último dado: 16:00 (Brasília)"
        assert "UST 2 Anos (%): 4,130 (na decisão 4,000; +13,0 p.b.)" in text
        assert "4.130" not in text

    def test_empty_frame_raises(self):
        decision = pd.Timestamp("2026-09-16 15:00", tz=_TZ_BRT)
        with pytest.raises(DraftingError, match="market"):
            market_snapshot(pd.DataFrame(), decision)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_drafting.py -k Market -q`
Expected: `ImportError`.

- [ ] **Step 3: Implementar**

Acrescentar a `drafting.py`, depois de `read_bank_pdfs`:

```python
# --- reação de mercado ----------------------------------------------------------

# Como cada painel expressa variação: taxas em pontos-base (diferença × 100),
# inclinação em pontos-base (já está em bps), índices em %, VIX em pontos.
_CHANGE_KIND = {
    "UST_2Y": "rate_bp",
    "UST_10Y": "rate_bp",
    "OIS_1Y1Y": "rate_bp",
    "SPREAD_2S10S": "bp",
    "NASDAQ": "pct",
    "SPX": "pct",
    "RUSSELL": "pct",
    "DXY": "pct",
    "VIX": "pts",
}


@dataclass(frozen=True)
class PanelSnapshot:
    key: str
    label: str
    at_decision: str
    last: str
    change: str


@dataclass(frozen=True)
class MarketSnapshot:
    panels: list[PanelSnapshot]
    last_time: str  # HH:MM em Brasília


def _pt(number: str) -> str:
    """Notação brasileira: ponto de milhar e vírgula decimal; menos tipográfico."""
    return number.replace(",", "\x00").replace(".", ",").replace("\x00", ".").replace("-", "−")


def _change(kind: str, before: float, after: float) -> str:
    if kind == "rate_bp":
        return f"{(after - before) * 100:+.1f} p.b."
    if kind == "bp":
        return f"{after - before:+.1f} p.b."
    if kind == "pct":
        return f"{(after / before - 1) * 100:+.1f}%"
    return f"{after - before:+.2f} pts"


def market_snapshot(market_data: pd.DataFrame, decision_time: pd.Timestamp) -> MarketSnapshot:
    """Nível na decisão, último nível e variação por painel, já formatados."""
    from reports.fomc.core.word_export import MARKET_REACTION_PANELS

    if market_data is None or market_data.empty:
        raise DraftingError("No market data to summarize")
    panels: list[PanelSnapshot] = []
    for key, label, fmt, _pos in MARKET_REACTION_PANELS:
        if key not in market_data.columns:
            continue
        series = market_data[key].dropna()
        if series.empty:
            continue
        before_series = series[series.index <= decision_time]
        before = float(before_series.iloc[-1]) if not before_series.empty else float(series.iloc[0])
        after = float(series.iloc[-1])
        panels.append(
            PanelSnapshot(
                key=key,
                label=label,
                at_decision=_pt(fmt.format(before)),
                last=_pt(fmt.format(after)),
                change=_pt(_change(_CHANGE_KIND.get(key, "pts"), before, after)),
            )
        )
    if not panels:
        raise DraftingError("No market panel available to summarize")
    last_time = market_data.dropna(how="all").index[-1].strftime("%H:%M")
    return MarketSnapshot(panels=panels, last_time=last_time)


def format_market(snapshot: MarketSnapshot) -> str:
    """Uma linha por painel, para o bloco REAÇÃO DE MERCADO da mensagem."""
    lines = [f"Último dado: {snapshot.last_time} (Brasília)"]
    for p in snapshot.panels:
        lines.append(f"{p.label}: {p.last} (na decisão {p.at_decision}; {p.change})")
    return "\n".join(lines)
```

Atenção ao `_pt`: `fmt` de `MARKET_REACTION_PANELS` para índices é `"{:,.0f}"`, que produz `6,000`; a troca ponto↔vírgula tem de ser simultânea, por isso o marcador `\x00`. O sinal de menos vira `−` (U+2212) para casar com o guia. Se algum teste esperar `"−1,0%"` e sair `"-1,0%"`, o problema é a ordem das trocas.

- [ ] **Step 4: Rodar tudo**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: passa.

- [ ] **Step 5: Propor commit**

```
Resume o grid de reação de mercado em números para as etapas

Corpo: a redação e a revisão precisam da reação em texto, não em figura. Para cada
painel do grid: nível na decisão, último nível e variação no tipo do painel, com
vírgula decimal e o horário do último dado.
```

---

### Task 5: mensagens, bloco cercado e execução de etapa (`drafting.py`, parte 3)

**Files:**
- Modify: `src/reports/fomc/core/drafting.py`
- Test: `tests/test_drafting.py`

**Interfaces:**
- Consumes: `_modelo.run`, `_modelo.MISSING_INPUT_MARK`; `Headline`, `MarketSnapshot`, `format_market`.
- Produces: `MeetingInputs` (dataclass); `block(label: str, body: str | None) -> str`; `format_statement(statement: dict) -> str`; `format_sep_table(current, prior, prior_label) -> str`; `format_headlines(headlines) -> str`; `build_message(prompt_file: str, blocks: list[tuple[str, str | None]]) -> str`; `extract_fenced_block(response: str) -> str`; `parse_bank_sections(text: str) -> dict[str, str]`; `run_stage(stage: str, message: str, destination: Path) -> str`.

- [ ] **Step 1: Testes que falham**

Acrescentar a `tests/test_drafting.py`:

```python
from reports import _modelo
from reports.fomc.core.drafting import (
    MeetingInputs,
    block,
    build_message,
    extract_fenced_block,
    format_sep_table,
    format_statement,
    parse_bank_sections,
    run_stage,
)


@pytest.fixture
def prompts(tmp_path, monkeypatch):
    """Guia e prompts sintéticos, para a montagem não depender dos reais."""
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "00_guia_de_estilo.md").write_text("GUIA", encoding="utf-8")
    (d / "01_resumo.md").write_text("PROMPT RESUMO", encoding="utf-8")
    (d / "02_bancos.md").write_text("PROMPT BANCOS", encoding="utf-8")
    (d / "03_revisao.md").write_text("PROMPT REVISAO", encoding="utf-8")
    monkeypatch.setattr(drafting, "PROMPTS_DIR", d)
    return d


@pytest.fixture
def model(monkeypatch):
    """Dublê do backend: devolve a resposta escolhida e guarda a mensagem recebida."""
    state = {"messages": []}

    def install(response: str):
        class Fake:
            name = "fake"

            def run(self, message, *, stage, model):
                state["messages"].append((stage, message))
                return response

        monkeypatch.setitem(_modelo.BACKENDS, "fake", Fake)
        monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "fake")
        return state

    return install


class TestBlocks:
    def test_block_marks_missing(self):
        assert block("STATEMENT", "texto") == "=== STATEMENT ===\ntexto"
        assert block("STATEMENT", None) == "=== STATEMENT === (ausente)"
        assert block("STATEMENT", "  ") == "=== STATEMENT === (ausente)"

    def test_format_statement_in_portuguese_with_comma(self):
        s = {
            "decision": "hold",
            "target_rate_low": 3.5,
            "target_rate_high": 3.75,
            "unanimous": False,
            "dissenters": ["Stephen Miran"],
            "key_phrases": ["Inflation remains elevated"],
        }
        text = format_statement(s)
        assert "decisão: manutenção" in text
        assert "faixa: 3,50%–3,75%" in text
        assert "unânime: não; dissidentes: Stephen Miran" in text
        assert "Inflation remains elevated" in text

    def test_format_sep_table_with_prior_and_missing_year(self):
        cur = pd.DataFrame(
            {"Variable": ["Change in real GDP"], "2026": [1.8], "2029": [2.0], "Longer run": [1.8]}
        )
        prior = pd.DataFrame(
            {
                "Variable": ["Change in real GDP"],
                "2026": [1.4],
                "2029": [float("nan")],
                "Longer run": [1.8],
            }
        )
        text = format_sep_table(cur, prior, "June projection")
        assert text.splitlines()[0] == "| Variável | 2026 | 2029 | Longer run |"
        assert "| Change in real GDP | 1,8 (1,4) | 2,0 (—) | 1,8 (1,8) |" in text
        assert "June projection" in text

    def test_build_message_order_guide_prompt_blocks(self, prompts):
        msg = build_message("01_resumo.md", [("A", "1"), ("B", None)])
        assert msg.index("GUIA") < msg.index("PROMPT RESUMO") < msg.index("=== A ===")
        assert "=== B === (ausente)" in msg


class TestResponses:
    def test_last_fenced_block(self):
        r = "auditoria\n```\nprimeiro\n```\nmais\n```markdown\nsegundo\nlinha\n```\n"
        assert extract_fenced_block(r) == "segundo\nlinha"

    def test_no_block_raises(self):
        with pytest.raises(DraftingError, match="fenced"):
            extract_fenced_block("sem bloco")

    def test_bank_sections_in_order(self):
        text = "## Goldman Sachs\nParágrafo GS.\n\n## JPM\nParágrafo JPM.\n"
        assert parse_bank_sections(text) == {
            "Goldman Sachs": "Parágrafo GS.",
            "JPM": "Parágrafo JPM.",
        }


class TestRunStage:
    def test_writes_full_response_and_returns_block(self, model, tmp_path):
        model("audit\n```\ntexto final\n```")
        dest = tmp_path / "out" / "resumo_decisao.md"
        assert run_stage("resumo", "mensagem", dest) == "texto final"
        assert dest.read_text(encoding="utf-8").startswith("audit")

    def test_missing_input_mark_raises_and_writes_nothing(self, model, tmp_path):
        model(f"{_modelo.MISSING_INPUT_MARK}: headlines\n```\nx\n```")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError, match="headlines"):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_no_fenced_block_raises_and_writes_nothing(self, model, tmp_path):
        model("só auditoria")
        dest = tmp_path / "resumo_decisao.md"
        with pytest.raises(DraftingError):
            run_stage("resumo", "m", dest)
        assert not dest.exists()

    def test_model_error_becomes_drafting_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INFORMES_EVENTOS_BACKEND", "nao-existe")
        with pytest.raises(DraftingError, match="nao-existe"):
            run_stage("resumo", "m", tmp_path / "x.md")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_drafting.py -k "Blocks or Responses or RunStage" -q`
Expected: `ImportError`.

- [ ] **Step 3: Implementar**

Acrescentar a `drafting.py`:

```python
# --- insumos e mensagem --------------------------------------------------------


@dataclass
class MeetingInputs:
    """Tudo o que as etapas recebem; montado pelo notebook a partir das células anteriores."""

    meeting_date: str
    statement_text: str | None = None
    statement: dict | None = None
    is_sep: bool = False
    sep_medians: pd.DataFrame | None = None
    sep_prior: pd.DataFrame | None = None
    prior_label: str | None = None
    headlines: list[Headline] = field(default_factory=list)
    market: MarketSnapshot | None = None


def block(label: str, body: str | None) -> str:
    """Bloco rotulado; insumo ausente é marcado, nunca omitido, para o prompt reclamar."""
    if body is None or not str(body).strip():
        return f"=== {label} === (ausente)"
    return f"=== {label} ===\n{str(body).strip()}"


_DECISION_PT = {"hold": "manutenção", "cut": "corte", "hike": "alta"}


def _pct(value) -> str:
    return _pt(f"{float(value):.2f}%")


def format_statement(statement: dict) -> str:
    """O parse do statement em uma linha de fatos, em português e com vírgula decimal."""
    parts = [f"decisão: {_DECISION_PT.get(statement.get('decision'), 'não identificada')}"]
    low, high = statement.get("target_rate_low"), statement.get("target_rate_high")
    if low is not None and high is not None:
        parts.append(f"faixa: {_pct(low)}–{_pct(high)}")
    unanimous = statement.get("unanimous")
    if unanimous is True:
        parts.append("unânime: sim")
    elif unanimous is False:
        dissenters = ", ".join(statement.get("dissenters") or []) or "não listados"
        parts.append(f"unânime: não; dissidentes: {dissenters}")
    lines = ["; ".join(parts)]
    for phrase in statement.get("key_phrases") or []:
        lines.append(f"- {phrase}")
    return "\n".join(lines)


def _cell(value) -> str:
    return "—" if value is None or pd.isna(value) else _pt(f"{float(value):.1f}")


def format_sep_table(
    current: pd.DataFrame,
    prior: pd.DataFrame | None,
    prior_label: str | None,
) -> str:
    """Tabela markdown: mediana atual (anterior) por variável e ano, vírgula decimal."""
    years = [c for c in current.columns if c != "Variable"]
    label = prior_label or "Prior projection"
    lines = [
        "| Variável | " + " | ".join(years) + " |",
        "|---|" + "---|" * len(years),
    ]
    for _, row in current.iterrows():
        cells = []
        prior_row = None
        if prior is not None and not prior.empty:
            match = prior[prior["Variable"] == row["Variable"]]
            prior_row = match.iloc[0] if not match.empty else None
        for y in years:
            cur = _cell(row.get(y))
            if prior_row is None:
                cells.append(cur)
            else:
                cells.append(f"{cur} ({_cell(prior_row.get(y))})")
        lines.append(f"| {row['Variable']} | " + " | ".join(cells) + " |")
    lines.append(f"Entre parênteses: mediana da projeção anterior ({label}). — = sem projeção.")
    return "\n".join(lines)


def format_headlines(headlines: list[Headline]) -> str:
    return "\n".join(("*** " if h.bold else "") + h.text for h in headlines)


def _read_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.is_file():
        raise DraftingError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_message(prompt_file: str, blocks: list[tuple[str, str | None]]) -> str:
    """Guia de estilo, prompt da etapa, depois os blocos, nessa ordem, sempre."""
    parts = [_read_prompt(STYLE_GUIDE), _read_prompt(prompt_file)]
    parts += [block(label, body) for label, body in blocks]
    return "\n\n".join(parts) + "\n"


# --- resposta e execução -------------------------------------------------------

_FENCED = re.compile(r"```[a-zA-Z]*\n(.*?)\n```", re.DOTALL)


def extract_fenced_block(response: str) -> str:
    """O último bloco cercado da resposta é o que o notebook consome."""
    blocks = _FENCED.findall(response)
    if not blocks:
        raise DraftingError("Model response has no fenced block")
    return blocks[-1].strip()


_BANK_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_bank_sections(text: str) -> dict[str, str]:
    """Seções `## Banco` → {banco: parágrafo}, na ordem em que aparecem."""
    result: dict[str, str] = {}
    matches = list(_BANK_HEADING.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        if body:
            result[m.group(1)] = body
    return result


def run_stage(stage: str, message: str, destination: Path) -> str:
    """Chama o backend, valida a resposta, grava a resposta inteira, devolve o bloco.

    Não grava nada quando falha: um .md pela metade seria lido como bom.
    """
    try:
        response = _modelo.run(message, stage=stage)
    except _modelo.ModelError as e:
        raise DraftingError(str(e)) from e
    if response.lstrip().startswith(_modelo.MISSING_INPUT_MARK):
        first = response.strip().splitlines()[0]
        raise DraftingError(f"Stage {stage} refused: {first}")
    text = extract_fenced_block(response)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(response + "\n", encoding="utf-8")
    return text
```

- [ ] **Step 4: Rodar tudo**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: passa.

- [ ] **Step 5: Propor commit**

```
Monta a mensagem das etapas do FOMC e lê a resposta do modelo

Corpo: guia de estilo, prompt da etapa e insumos em blocos rotulados, com insumo
ausente marcado em vez de omitido; a resposta inteira vai para o .md da etapa e
só o último bloco cercado volta ao notebook. Resposta sem bloco ou com a marca de
entrada ausente é erro, e nada é gravado.
```

---

### Task 6: guia de estilo e prompts

**Files:**
- Create: `prompts/00_guia_de_estilo.md`, `prompts/01_resumo.md`, `prompts/02_bancos.md`, `prompts/03_revisao.md`
- Test: `tests/test_drafting.py`

- [ ] **Step 1: Teste que falha**

```python
class TestPromptFiles:
    @pytest.mark.parametrize(
        "name", ["00_guia_de_estilo.md", "01_resumo.md", "02_bancos.md", "03_revisao.md"]
    )
    def test_prompt_exists_and_has_version_header(self, name):
        path = drafting.PROMPTS_DIR / name
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("# ")
        assert "Versão" in text.splitlines()[2]

    def test_stage_prompts_demand_fenced_block(self):
        for name in ["01_resumo.md", "02_bancos.md", "03_revisao.md"]:
            text = (drafting.PROMPTS_DIR / name).read_text(encoding="utf-8")
            assert "bloco cercado" in text, name
```

Run: `uv run pytest tests/test_drafting.py -k PromptFiles -q` → Expected: FAIL (arquivos não existem).

- [ ] **Step 2: Escrever `prompts/00_guia_de_estilo.md`**

```markdown
# GUIA DE ESTILO — INFORME DO FOMC

Versão 1.0 — 16/09/2026
Fonte única das convenções editoriais do informe. Entra na mensagem de todas as etapas.

---

## 1. Leitor e registro

O informe vai à Diretoria do Banco Central do Brasil: economistas graduados e
experientes, com domínio macro pleno e profundidade variável em mercados. Registro
formal e impessoal. Nunca explicar conceito macro. Mecanismo de mercado não trivial se
explica *en passant*, numa oração. Nenhuma gíria de mesa.

Nenhuma opinião, projeção, recomendação ou juízo normativo da divisão. Leituras e
interpretações aparecem atribuídas: ao comunicado, ao SEP, à coletiva, aos headlines
ou ao mercado.

## 2. Forma

Prosa corrida em português, sem marcadores, em quatro a seis parágrafos breves. Ordem
canônica, pulando o que não houver:

1. Decisão, faixa e votação, com dissidências nominais e o que cada uma pedia; se for
   a primeira reunião de um presidente, dizer.
2. O comunicado: o que mudou frente ao anterior, atividade, mercado de trabalho,
   inflação, balanço de riscos.
3. O SEP, só em reunião com projeções: as medianas que mudaram e a direção da mediana
   dos Fed Funds; a distribuição dos *dots* quando disser algo.
4. A coletiva, só depois que houver: tom, mensagens novas, o que confirmou ou desfez.
5. Reação de mercado e leitura: curva, dólar, bolsas, o que passou a ser precificado;
   fechar com a leitura explícita frente ao que se esperava.

## 3. Números

Só dos blocos recebidos na mensagem: tabela do SEP, parse do statement, headlines e
reação de mercado. Nunca de memória, nunca inferido, nunca arredondado além do que a
fonte traz. Número que não está nos blocos não entra.

Vírgula decimal, sempre: 3,50%, 4,2%. Pontos-base grafados "p.b.". Medianas do SEP com
uma casa decimal, como o Fed publica; o valor cheio em oitavos pode ir entre
parênteses quando os headlines o usarem ("3,8%, ou 3,75% no valor cheio"). Faixa da
Fed Funds com duas casas: "entre 3,50% e 3,75%". Sinal de variação por extenso ou com
"+"/"−" seguido do número.

## 4. Léxico

Termos em inglês preservados e em itálico, marcados com asterisco simples no
markdown: *hawkish*, *dovish*, *hold*, *dots*, *dot plot*, *forward guidance*,
*regime change*, *easing bias*, *tightening bias*. Traduzir sempre: *yields* →
taxas/juros; *statement* → comunicado; *press conference* → coletiva; *median* →
mediana; *longer run* → longo prazo.

"Fed Funds" com s. "FOMC" e "Fed" sem artigo de tradução. Nomes de participantes como
no comunicado. "Presidente do Fed" para o *chair*.

## 5. Atribuição

Fato do comunicado e da tabela do SEP dispensa atribuição. Inferência de veículo é
atribuída: "a Bloomberg atribui", "segundo os headlines". Fala de participante leva
cargo e ocasião: "Warsh, na coletiva, afirmou". Uma vez por bloco temático, nunca por
frase.

## 6. Leitura

O último parágrafo fecha com a leitura explícita: a decisão foi lida como neutra,
*hawkish* ou *dovish* frente ao que se esperava, e como a curva reagiu. A leitura não
pode contradizer o bloco de reação de mercado: se as taxas curtas subiram, o texto não
diz que o mercado leu como *dovish*.

## 7. Coletiva

Ao reescrever depois da coletiva, manter os parágrafos anteriores a ela (decisão,
comunicado, SEP) e mudar só o que a coletiva muda. Quando um fato que era inferência
vira confirmação, dizer que foi confirmado e por quem.

## 8. Checagem

Toda afirmação numérica do texto tem de se rastrear até um bloco da mensagem. Na
revisão, afirmação sem rastro é sinalizada, nunca suavizada até virar algo vago que
sobreviva.
```

- [ ] **Step 3: Escrever `prompts/01_resumo.md`**

```markdown
# PROMPT 1 — RESUMO DO INFORME DO FOMC

Versão 1.0 — 16/09/2026
Etapa de redação, em dois momentos: após a decisão e, depois, após a coletiva.

---

## PAPEL

Você redige o resumo de abertura do informe do FOMC da Mesa de Investimentos do
DEPIN/DIRIN, seguindo integralmente o GUIA DE ESTILO que abre esta mensagem. O texto
é descritivo: fatos do comunicado, do SEP, dos headlines e da reação de mercado.
Interpretações só atribuídas. Nenhuma opinião da divisão.

## ENTRADAS

Blocos rotulados `=== NOME ===` no fim desta mensagem. Bloco marcado `(ausente)` não
existe: não invente o que ele conteria.

Obrigatórios no momento "decisão": STATEMENT, DECISÃO (parse), HEADLINES BLOOMBERG.
Obrigatórios no momento "coletiva": RESUMO DA DECISÃO, HEADLINES DA COLETIVA.
Opcionais: SEP (só em reunião com projeções), REAÇÃO DE MERCADO.

Se faltar bloco obrigatório, abra a resposta com `ENTRADA OBRIGATÓRIA AUSENTE:` e o
nome do bloco, e pare.

## MOMENTO

O bloco MOMENTO diz `decisão` ou `coletiva`.

- `decisão`: escreva o resumo completo, quatro a seis parágrafos, na ordem canônica do
  guia, sem o parágrafo da coletiva.
- `coletiva`: receba o RESUMO DA DECISÃO e reescreva só o que a coletiva e a reação
  de mercado atualizada mudam. Parágrafos de decisão, comunicado e SEP ficam como
  estão, salvo erro factual evidente, que você aponta na auditoria. Acrescente o
  parágrafo da coletiva e refaça o de reação e leitura.

## REGRAS DURAS

1. Todo número vem de um bloco. Cite o bloco na auditoria.
2. Vírgula decimal. Termos em inglês em *itálico*.
3. Reunião sem SEP: nenhum parágrafo de projeções, nenhuma menção a *dots*.
4. Inferência de veículo é atribuída ("a Bloomberg atribui").
5. Fechar com a leitura explícita frente ao esperado, coerente com a REAÇÃO DE
   MERCADO quando ela existir.

## SAÍDA

Primeiro, uma seção `## Auditoria` curta: para cada parágrafo, de quais blocos vieram
os números; ressalvas e ambiguidades. Depois, o texto final num único bloco cercado
por três crases, em markdown, parágrafos separados por linha em branco, sem título e
sem cabeçalho. O bloco cercado é a única parte que vai ao documento.
```

- [ ] **Step 4: Escrever `prompts/02_bancos.md`**

```markdown
# PROMPT 2 — COMENTÁRIOS DOS BANCOS

Versão 1.0 — 16/09/2026
Etapa de síntese do research recebido após a decisão do FOMC.

---

## PAPEL

Você resume, para a seção "Comentários dos bancos" do informe do FOMC, o que cada
casa de research escreveu sobre a decisão, seguindo o GUIA DE ESTILO que abre esta
mensagem. Um parágrafo por banco. Research sell-side é opinião de casa: tudo o que
vier dele é atribuído ao banco, nunca apresentado como fato.

## ENTRADAS

Um bloco `=== RESEARCH: Nome do banco ===` por PDF, com o texto extraído. Blocos
DECISÃO (parse) e SEP entram só como referência para você não confundir o que o
banco diz com o que o Fed publicou. Se não houver nenhum bloco RESEARCH, abra a
resposta com `ENTRADA OBRIGATÓRIA AUSENTE: RESEARCH` e pare.

## REGRAS DURAS

1. Um parágrafo por banco, de 60 a 120 palavras, em português, com o nome do banco
   como sujeito da primeira frase.
2. Só o que aquele research diz. Não misturar casas, não completar com o comunicado,
   não acrescentar leitura própria.
3. Números só os do próprio research, com vírgula decimal. Projeção de juros do banco
   sempre como projeção do banco.
4. Termos em inglês em *itálico*. Sem gíria de mesa.
5. Texto sem trecho legível: dizer na auditoria, e não escrever parágrafo para ele.

## SAÍDA

Primeiro, `## Auditoria`: para cada banco, de que parte do research saiu o parágrafo e
o que ficou de fora. Depois, um único bloco cercado por três crases contendo, para
cada banco, uma linha `## Nome do banco` seguida do parágrafo, na ordem em que os
blocos RESEARCH apareceram. O bloco cercado é a única parte que vai ao documento.
```

- [ ] **Step 5: Escrever `prompts/03_revisao.md`**

```markdown
# PROMPT 3 — REVISÃO DE COERÊNCIA DO INFORME DO FOMC

Versão 1.0 — 16/09/2026
Etapa final, antes de gerar o Word. Executada sobre o resumo escolhido pelo autor.

---

## PAPEL

Você revisa o informe do FOMC da Mesa de Investimentos do DEPIN/DIRIN. A revisão
tem três blocos, NESTA ORDEM: checagem factual, conformidade com o GUIA DE ESTILO, e
sugestão editorial. O primeiro é o mais importante. Você preserva a estrutura e as
escolhas do autor; discordância se sinaliza, não se impõe.

## ENTRADAS

TEXTO PARA REVISÃO (obrigatório), COMENTÁRIOS DOS BANCOS (opcional), e os insumos
factuais: STATEMENT, DECISÃO (parse), SEP, HEADLINES BLOOMBERG, HEADLINES DA
COLETIVA, REAÇÃO DE MERCADO. Revisão sem STATEMENT e sem DECISÃO não é revisão: abra
com `ENTRADA OBRIGATÓRIA AUSENTE:` e pare.

## BLOCO 1 — CHECAGEM FACTUAL

Para cada afirmação do texto que contenha número, votação, nome, direção de mercado ou
mudança de linguagem do comunicado, uma linha:

`[veredito] afirmação — bloco que sustenta ou contradiz`

Vereditos: `SUPORTADA`, `PARCIALMENTE SUPORTADA`, `NÃO LOCALIZADA`, `CONTRADITA`.
Conferir em especial: faixa da Fed Funds e votação contra DECISÃO; medianas contra
SEP, inclusive a mediana anterior; níveis e variações de juros, dólar e bolsas contra
REAÇÃO DE MERCADO; leitura *hawkish*/*dovish* contra a direção das taxas curtas.
Afirmação sem rastro nunca é suavizada: ou é marcada, ou sai no texto corrigido.

## BLOCO 2 — CONFORMIDADE

Vírgula decimal em todos os números; termos em inglês em *itálico*; "Fed Funds" com
s; extensão entre quatro e seis parágrafos; parágrafo do SEP só em reunião com SEP;
nenhuma opinião ou recomendação da divisão; atribuição de inferência presente.
Listar cada desvio com o trecho.

## BLOCO 3 — SUGESTÕES EDITORIAIS

Clareza, fluidez, ordem. Separadas dos blocos anteriores e não aplicadas ao texto
corrigido.

## SAÍDA

Os três blocos como seções `## Bloco 1`, `## Bloco 2`, `## Bloco 3`. Por fim, o
texto corrigido num único bloco cercado por três crases, em markdown, aplicando só as
correções dos blocos 1 e 2: erro de fato contra os insumos e desvio de conformidade.
Se não houver correção, o bloco cercado repete o texto recebido. O bloco cercado é a
única parte que vai ao documento.
```

- [ ] **Step 6: Rodar tudo**

Run: `uv run pytest -q`
Expected: passa, inclusive `TestPromptFiles`.

- [ ] **Step 7: Propor commit**

```
Escreve o guia de estilo e os prompts das etapas do FOMC

Corpo: os prompts são a fonte de verdade editorial, como no matinal. O guia nasce do
que se fixou em junho: Diretoria como leitor, prosa em quatro a seis parágrafos,
vírgula decimal, inglês em itálico, números só dos insumos, leitura explícita no
fechamento. O autor revisa o guia; ele manda no texto.
```

---

### Task 7: as três etapas (`draft_summary`, `draft_bank_comments`, `review_report`)

**Files:**
- Modify: `src/reports/fomc/core/drafting.py`
- Test: `tests/test_drafting.py`

**Interfaces:**
- Consumes: tudo das Tasks 3 a 6.
- Produces: `draft_summary(inputs: MeetingInputs, *, stage: str = "decision", previous: str | None = None, presser_headlines: list[Headline] | None = None) -> str`; `draft_bank_comments(inputs: MeetingInputs, sources: list[BankSource]) -> dict[str, str]`; `review_report(inputs: MeetingInputs, summary: str, bank_comments: dict[str, str] | None = None, presser_headlines: list[Headline] | None = None) -> str`; `read_presser(folder: Path) -> list[Headline] | None`.

- [ ] **Step 1: Testes que falham**

```python
from reports.fomc.core.drafting import (
    draft_bank_comments,
    draft_summary,
    read_presser,
    review_report,
)


def _inputs(is_sep=True) -> MeetingInputs:
    cur = pd.DataFrame({"Variable": ["PCE inflation"], "2026": [3.6]})
    prior = pd.DataFrame({"Variable": ["PCE inflation"], "2026": [2.7]})
    return MeetingInputs(
        meeting_date="20260916",
        statement_text="STATEMENT TEXT",
        statement={
            "decision": "hold",
            "target_rate_low": 3.5,
            "target_rate_high": 3.75,
            "unanimous": True,
            "dissenters": [],
            "key_phrases": [],
        },
        is_sep=is_sep,
        sep_medians=cur if is_sep else None,
        sep_prior=prior if is_sep else None,
        prior_label="June projection" if is_sep else None,
        headlines=[Headline("Fed holds", True)],
        market=None,
    )


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(drafting, "PROJECT_ROOT", tmp_path)
    return tmp_path / "output" / "reports" / "fomc" / "20260916"


class TestDraftSummary:
    def test_decision_stage_message_and_output(self, prompts, model, out):
        state = model("## Auditoria\nok\n```\nParágrafo 1.\n\nParágrafo 2.\n```")
        text = draft_summary(_inputs())
        assert text == "Parágrafo 1.\n\nParágrafo 2."
        assert (out / "resumo_decisao.md").is_file()
        stage, msg = state["messages"][0]
        assert stage == "resumo"
        assert "=== MOMENTO ===\ndecisão" in msg
        assert "=== STATEMENT ===\nSTATEMENT TEXT" in msg
        assert "=== DECISÃO (parse) ===" in msg
        assert "=== SEP: MEDIANAS ATUAIS vs ANTERIORES (June projection) ===" in msg
        assert "| PCE inflation | 3,6 (2,7) |" in msg
        assert "=== HEADLINES BLOOMBERG ===\n*** Fed holds" in msg
        assert "=== REAÇÃO DE MERCADO === (ausente)" in msg
        assert "RESUMO DA DECISÃO" not in msg

    def test_no_sep_meeting_has_no_sep_block(self, prompts, model, out):
        state = model("```\nx\n```")
        draft_summary(_inputs(is_sep=False))
        assert "=== SEP" not in state["messages"][0][1]

    def test_presser_stage_requires_previous_and_presser(self, prompts, model, out):
        model("```\nx\n```")
        with pytest.raises(DraftingError, match="previous"):
            draft_summary(_inputs(), stage="presser", presser_headlines=[Headline("a", False)])
        with pytest.raises(DraftingError, match="coletiva"):
            draft_summary(_inputs(), stage="presser", previous="texto")

    def test_presser_stage_message_and_output(self, prompts, model, out):
        state = model("```\nnovo\n```")
        text = draft_summary(
            _inputs(),
            stage="presser",
            previous="RESUMO ANTERIOR",
            presser_headlines=[Headline("Warsh says", False)],
        )
        assert text == "novo"
        assert (out / "resumo_coletiva.md").is_file()
        msg = state["messages"][0][1]
        assert "=== MOMENTO ===\ncoletiva" in msg
        assert "=== RESUMO DA DECISÃO ===\nRESUMO ANTERIOR" in msg
        assert "=== HEADLINES DA COLETIVA ===\nWarsh says" in msg

    def test_unknown_stage_raises(self, prompts, model, out):
        with pytest.raises(DraftingError, match="stage"):
            draft_summary(_inputs(), stage="outro")


class TestReadPresser:
    def test_none_when_missing_list_when_present(self, tmp_path):
        assert read_presser(tmp_path) is None
        (tmp_path / "coletiva.txt").write_text("*** A\nB\n", encoding="utf-8")
        assert read_presser(tmp_path) == [Headline("A", True), Headline("B", False)]


class TestDraftBankComments:
    def test_one_block_per_source_and_dict_out(self, prompts, model, out):
        state = model("## Auditoria\n```\n## Goldman Sachs\nGS diz.\n\n## JPM\nJPM diz.\n```")
        result = draft_bank_comments(
            _inputs(), [BankSource("Goldman Sachs", "texto gs"), BankSource("JPM", "texto jpm")]
        )
        assert result == {"Goldman Sachs": "GS diz.", "JPM": "JPM diz."}
        assert (out / "bancos.md").is_file()
        msg = state["messages"][0][1]
        assert state["messages"][0][0] == "bancos"
        assert "=== RESEARCH: Goldman Sachs ===\ntexto gs" in msg
        assert msg.index("RESEARCH: Goldman Sachs") < msg.index("RESEARCH: JPM")

    def test_no_sources_raises_before_model(self, prompts, model, out):
        state = model("```\n## X\ny\n```")
        with pytest.raises(DraftingError, match="research"):
            draft_bank_comments(_inputs(), [])
        assert state["messages"] == []


class TestReviewReport:
    def test_message_has_text_banks_and_facts(self, prompts, model, out):
        state = model("## Bloco 1\n[SUPORTADA] x\n```\ntexto corrigido\n```")
        text = review_report(
            _inputs(), "TEXTO", {"JPM": "JPM diz."}, presser_headlines=[Headline("W", False)]
        )
        assert text == "texto corrigido"
        assert (out / "revisao.md").is_file()
        stage, msg = state["messages"][0]
        assert stage == "revisao"
        assert "=== TEXTO PARA REVISÃO ===\nTEXTO" in msg
        assert "=== COMENTÁRIOS DOS BANCOS ===\n## JPM\nJPM diz." in msg
        assert "=== HEADLINES DA COLETIVA ===\nW" in msg
        assert "=== DECISÃO (parse) ===" in msg

    def test_empty_summary_raises(self, prompts, model, out):
        with pytest.raises(DraftingError, match="summary"):
            review_report(_inputs(), "  ")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_drafting.py -k "DraftSummary or ReadPresser or DraftBank or ReviewReport" -q`
Expected: `ImportError`.

- [ ] **Step 3: Implementar**

Acrescentar a `drafting.py`:

```python
# --- as etapas -----------------------------------------------------------------

STAGE_DECISION = "decision"
STAGE_PRESSER = "presser"


def read_presser(folder: Path) -> list[Headline] | None:
    """coletiva.txt da pasta do dia, ou None se ainda não existir."""
    path = folder / PRESSER_FILE
    return read_headlines(path) if path.is_file() else None


def _fact_blocks(inputs: MeetingInputs) -> list[tuple[str, str | None]]:
    """Os blocos factuais comuns à redação e à revisão, na mesma ordem."""
    blocks: list[tuple[str, str | None]] = [
        ("STATEMENT", inputs.statement_text),
        ("DECISÃO (parse)", format_statement(inputs.statement) if inputs.statement else None),
    ]
    if inputs.is_sep:
        label = inputs.prior_label or "Prior projection"
        table = None
        if inputs.sep_medians is not None and not inputs.sep_medians.empty:
            table = format_sep_table(inputs.sep_medians, inputs.sep_prior, inputs.prior_label)
        blocks.append((f"SEP: MEDIANAS ATUAIS vs ANTERIORES ({label})", table))
    blocks.append(("HEADLINES BLOOMBERG", format_headlines(inputs.headlines) or None))
    return blocks


def _market_block(inputs: MeetingInputs) -> tuple[str, str | None]:
    return ("REAÇÃO DE MERCADO", format_market(inputs.market) if inputs.market else None)


def draft_summary(
    inputs: MeetingInputs,
    *,
    stage: str = STAGE_DECISION,
    previous: str | None = None,
    presser_headlines: list[Headline] | None = None,
) -> str:
    """Resumo em parágrafos. `decision` escreve tudo; `presser` reescreve o que a coletiva muda."""
    if stage not in (STAGE_DECISION, STAGE_PRESSER):
        raise DraftingError(f"Unknown stage: {stage!r} (expected 'decision' or 'presser')")
    blocks: list[tuple[str, str | None]] = [
        ("MOMENTO", "decisão" if stage == STAGE_DECISION else "coletiva")
    ]
    if stage == STAGE_PRESSER:
        if not (previous or "").strip():
            raise DraftingError("Presser stage needs the decision summary as `previous`")
        if not presser_headlines:
            raise DraftingError(f"Presser stage needs {PRESSER_FILE} in the day folder")
        blocks.append(("RESUMO DA DECISÃO", previous))
        blocks.append(("HEADLINES DA COLETIVA", format_headlines(presser_headlines)))
    blocks += _fact_blocks(inputs)
    blocks.append(_market_block(inputs))
    message = build_message(PROMPT_SUMMARY, blocks)
    name = OUT_SUMMARY_DECISION if stage == STAGE_DECISION else OUT_SUMMARY_PRESSER
    return run_stage("resumo", message, output_folder(inputs.meeting_date) / name)


def draft_bank_comments(inputs: MeetingInputs, sources: list[BankSource]) -> dict[str, str]:
    """Um parágrafo por banco, atribuído pelo nome; devolve {banco: parágrafo}."""
    if not sources:
        raise DraftingError("No bank research to summarize (empty 'bancos/')")
    blocks: list[tuple[str, str | None]] = [
        ("DECISÃO (parse)", format_statement(inputs.statement) if inputs.statement else None),
    ]
    if inputs.is_sep and inputs.sep_medians is not None and not inputs.sep_medians.empty:
        blocks.append(
            (
                "SEP: MEDIANAS ATUAIS vs ANTERIORES",
                format_sep_table(inputs.sep_medians, inputs.sep_prior, inputs.prior_label),
            )
        )
    blocks += [(f"RESEARCH: {s.name}", s.text) for s in sources]
    message = build_message(PROMPT_BANKS, blocks)
    text = run_stage("bancos", message, output_folder(inputs.meeting_date) / OUT_BANKS)
    sections = parse_bank_sections(text)
    if not sections:
        raise DraftingError("Bank stage returned no '## Bank' section")
    return sections


def review_report(
    inputs: MeetingInputs,
    summary: str,
    bank_comments: dict[str, str] | None = None,
    presser_headlines: list[Headline] | None = None,
) -> str:
    """Checagem factual, conformidade e sugestões; devolve o texto corrigido."""
    if not (summary or "").strip():
        raise DraftingError("Nothing to review: empty summary")
    banks = (
        "\n\n".join(f"## {name}\n{text}" for name, text in bank_comments.items())
        if bank_comments
        else None
    )
    blocks: list[tuple[str, str | None]] = [
        ("TEXTO PARA REVISÃO", summary),
        ("COMENTÁRIOS DOS BANCOS", banks),
    ]
    blocks += _fact_blocks(inputs)
    blocks.append(
        (
            "HEADLINES DA COLETIVA",
            format_headlines(presser_headlines) if presser_headlines else None,
        )
    )
    blocks.append(_market_block(inputs))
    message = build_message(PROMPT_REVIEW, blocks)
    return run_stage("revisao", message, output_folder(inputs.meeting_date) / OUT_REVIEW)
```

- [ ] **Step 4: Rodar tudo**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: passa.

- [ ] **Step 5: Propor commit**

```
Implementa as etapas de resumo, bancos e revisão do informe do FOMC

Corpo: o resumo tem dois momentos, decisão e coletiva, e o segundo recebe o primeiro
para mudar só o que a coletiva muda; os bancos entram um bloco por PDF e saem um
parágrafo por seção; a revisão recebe o texto escolhido e os mesmos insumos factuais
da redação, e devolve o texto corrigido. Tudo com dublê de backend nos testes.
```

---

### Task 8: notebook e preview

**Files:**
- Modify: `src/reports/fomc/notebooks/fomc_analysis.ipynb`
- Modify: `tests/test_reports_fomc.py` (teste do notebook)

**Interfaces:**
- Consumes: `drafting.*` das Tasks 3 a 7; `headlines_for_report`; `generate_fomc_report`.

- [ ] **Step 1: Teste que falha**

Em `tests/test_reports_fomc.py`:

```python
import json


class TestFomcNotebook:
    NB = Path(__file__).resolve().parents[1] / "src/reports/fomc/notebooks/fomc_analysis.ipynb"

    def _sources(self) -> list[str]:
        nb = json.loads(self.NB.read_text(encoding="utf-8"))
        return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]

    def test_text_fields_left_the_notebook(self):
        """Resumo, headlines e bancos vêm das etapas e da pasta do dia, não da célula."""
        joined = "\n".join(self._sources())
        for name in ("SUMMARY_TEXT =", "HEADLINES =", "PRESSER_HEADLINES =", "BANK_COMMENTS ="):
            assert name not in joined, name
        assert "SUMMARY_SOURCE" in joined

    def test_every_stage_has_a_cell(self):
        joined = "\n".join(self._sources())
        for call in (
            "draft_summary(",
            "draft_bank_comments(",
            "review_report(",
            "market_snapshot(",
        ):
            assert call in joined, call
```

Run: `uv run pytest tests/test_reports_fomc.py -k FomcNotebook -q` → Expected: FAIL.

- [ ] **Step 2: Reescrever a célula de configuração (célula 2)**

Editar o notebook com a ferramenta de notebook ou com um script Python que carrega o JSON, troca `source` das células e grava com `indent=1` e `ensure_ascii=False`. Manter `nbformat`, `metadata` e o `kernelspec` como estão. As saídas ficam vazias (o `nbstripout` cuida no commit).

Fonte nova da célula 2:

```python
# ============================================================
# CONFIGURAÇÃO DO USUÁRIO
# ============================================================

# Data da reunião (formato YYYYMMDD)
MEETING_DATE = "20260916"

# Pasta do dia: input/fomc/<data>/ com headlines.txt, coletiva.txt e bancos/*.pdf.
# Resumo, headlines e comentários dos bancos NÃO ficam mais neste notebook: vêm
# dos arquivos que você cola ali e das etapas de modelo, nas células mais abaixo.

# Qual resumo vai ao Word: "auto" pega o mais avançado que existir na pasta de
# saída (revisão > coletiva > decisão); ou force "revisao", "coletiva", "decisao".
SUMMARY_SOURCE = "auto"

# --- Reação de mercado (grid intraday 3x3 GERADO em Python) ---
# O horário da decisão é FIXO em horário de NY (ET); a conversão para Brasília
# é automática (auto-DST via zoneinfo). Edite apenas se o Fed mudar o horário.
FOMC_DECISION_TIME_ET = "14:00:00"

# Eixo X do grid se estende até este horário (em Brasília), mesmo sem dados até lá.
GRID_X_END_BRT = "20:00:00"

# Fallback: screenshot manual, usado SÓ se o Bloomberg estiver indisponível.
MARKET_REACTION_PNG = (
    r"c:\Users\mmart\OneDrive\BCB\dirin\15_informes\fomc\screenshots\market_reaction.png"
)

# Dot plot screenshot (só SEP, ou None para reuniões sem SEP)
DOT_PLOT_PNG = r"c:\Users\mmart\OneDrive\BCB\dirin\15_informes\fomc\screenshots\dot_plot.png"

# ============================================================
from reports.fomc.core import drafting

DAY_FOLDER = drafting.day_folder(MEETING_DATE)
OUT_FOLDER = drafting.output_folder(MEETING_DATE)
print(f"Reunião configurada: {MEETING_DATE}")
print(f"Tipo: {'COM SEP' if is_sep_meeting(MEETING_DATE) else 'SEM SEP'}")
print(
    f"Pasta do dia: {DAY_FOLDER} ({'existe' if DAY_FOLDER.is_dir() else 'NÃO EXISTE — crie e cole os headlines'})"
)
```

Na célula 1 (imports), acrescentar ao bloco de imports:

```python
from reports.fomc.core.drafting import (
    MeetingInputs,
    DraftingError,
    draft_summary,
    draft_bank_comments,
    review_report,
    read_headlines,
    read_presser,
    read_bank_pdfs,
    headlines_for_report,
    market_snapshot,
)
```

Na célula 5 (grid), guardar o intraday para a etapa: logo após `market_data = fetch_market_reaction(MEETING_DATE)` nada muda; mas antes do `try`, acrescentar `market_data = None`, para a célula de insumos saber se houve Bloomberg.

- [ ] **Step 3: Inserir as células novas depois da célula 7 (dots e SEP.xlsx) e antes do preview**

Célula A, markdown:

```markdown
## Etapas de modelo

Cada célula abaixo chama o modelo uma vez e grava a resposta inteira em
`output/reports/fomc/<data>/`. Nada roda sozinho: execute a célula quando o insumo
dela existir. Reexecutar sobrescreve o `.md` da etapa.
```

Célula B, código, "insumos do dia":

```python
# Insumos do dia: o que as células anteriores produziram + a pasta do dia.
# Não chama o modelo. Diz o que achou e o que falta.
_statement_text = None
if documents.get("statement"):
    import pdfplumber

    with pdfplumber.open(documents["statement"]) as _pdf:
        _statement_text = "\n".join((p.extract_text() or "") for p in _pdf.pages)

_market = None
if market_data is not None and not market_data.empty:
    _market = market_snapshot(market_data, event_times["decisao"])

try:
    _headlines = read_headlines(DAY_FOLDER / "headlines.txt")
except DraftingError as e:
    _headlines = []
    print(f"⚠️ {e}")

_presser = read_presser(DAY_FOLDER)

INPUTS = MeetingInputs(
    meeting_date=MEETING_DATE,
    statement_text=_statement_text,
    statement=statement_data or None,
    is_sep=is_sep_meeting(MEETING_DATE),
    sep_medians=sep_current,
    sep_prior=sep_prior,
    prior_label=prior_label,
    headlines=_headlines,
    market=_market,
)

print(f"Statement: {'✓' if _statement_text else '✗'}")
print(
    f"SEP: {'✓' if INPUTS.is_sep and sep_current is not None else '— (sem SEP)' if not INPUTS.is_sep else '✗'}"
)
print(f"Headlines: {len(_headlines)} ({sum(h.bold for h in _headlines)} em destaque)")
print(f"Coletiva: {len(_presser) if _presser else '✗ (coletiva.txt ausente)'}")
print(f"Reação de mercado: {'✓ até ' + _market.last_time if _market else '✗ (sem Bloomberg)'}")
print(
    f"Research: {len(list((DAY_FOLDER / 'bancos').glob('*.pdf'))) if (DAY_FOLDER / 'bancos').is_dir() else 0} PDF"
)
```

Célula C, código, "resumo da decisão":

```python
# Etapa: resumo da decisão. Requer statement e headlines.txt.
summary_decision = draft_summary(INPUTS, stage="decision")
display(Markdown(summary_decision))
print(f"\nGravado em: {OUT_FOLDER / 'resumo_decisao.md'}")
```

Célula D, código, "resumo pós-coletiva":

```python
# Etapa: resumo pós-coletiva. Requer coletiva.txt e o resumo da decisão gravado.
_presser = read_presser(DAY_FOLDER)
if _presser is None:
    print("coletiva.txt ainda não existe na pasta do dia — pule esta célula por enquanto.")
else:
    _prev_path = OUT_FOLDER / "resumo_decisao.md"
    if not _prev_path.is_file():
        raise DraftingError(f"Run the decision summary first: {_prev_path} not found")
    from reports.fomc.core.drafting import extract_fenced_block

    _previous = extract_fenced_block(_prev_path.read_text(encoding="utf-8"))
    # A reação de mercado é refeita aqui para pegar o que veio depois da coletiva.
    if market_data is not None and not market_data.empty:
        try:
            market_data = fetch_market_reaction(MEETING_DATE)
            INPUTS.market = market_snapshot(market_data, event_times["decisao"])
        except RuntimeError as e:
            print(f"⚠️ Bloomberg indisponível ({e}); usa a reação já carregada.")
    summary_presser = draft_summary(
        INPUTS, stage="presser", previous=_previous, presser_headlines=_presser
    )
    display(Markdown(summary_presser))
    print(f"\nGravado em: {OUT_FOLDER / 'resumo_coletiva.md'}")
```

Célula E, código, "bancos":

```python
# Etapa: comentários dos bancos. Requer bancos/*.pdf na pasta do dia.
_bank_dir = DAY_FOLDER / "bancos"
if not _bank_dir.is_dir() or not any(_bank_dir.glob("*.pdf")):
    print("Sem research em bancos/ — pule esta célula.")
    bank_comments = {}
else:
    _sources, _ignored = read_bank_pdfs(_bank_dir)
    for _name in _ignored:
        print(f"⚠️ ignorado: {_name}")
    bank_comments = draft_bank_comments(INPUTS, _sources)
    for _bank, _text in bank_comments.items():
        display(Markdown(f"**{_bank}**: {_text}"))
    print(f"\nGravado em: {OUT_FOLDER / 'bancos.md'}")
```

Célula F, código, "revisão":

```python
# Etapa: revisão de coerência sobre o resumo escolhido por SUMMARY_SOURCE.
from reports.fomc.core.drafting import extract_fenced_block, parse_bank_sections


def _pick_summary(source: str) -> tuple[str, Path]:
    order = {
        "revisao": ["revisao.md"],
        "coletiva": ["resumo_coletiva.md"],
        "decisao": ["resumo_decisao.md"],
        "auto": ["revisao.md", "resumo_coletiva.md", "resumo_decisao.md"],
    }
    for name in order[source]:
        p = OUT_FOLDER / name
        if p.is_file():
            return extract_fenced_block(p.read_text(encoding="utf-8")), p
    raise DraftingError(f"No summary found for SUMMARY_SOURCE={source!r} in {OUT_FOLDER}")


_text, _from = _pick_summary(
    "coletiva" if (OUT_FOLDER / "resumo_coletiva.md").is_file() else "decisao"
)
_banks_path = OUT_FOLDER / "bancos.md"
_banks = (
    parse_bank_sections(extract_fenced_block(_banks_path.read_text(encoding="utf-8")))
    if _banks_path.is_file()
    else None
)
reviewed = review_report(INPUTS, _text, _banks, presser_headlines=read_presser(DAY_FOLDER))
print(f"Revisado a partir de: {_from.name}")
display(Markdown((OUT_FOLDER / "revisao.md").read_text(encoding="utf-8")))
```

- [ ] **Step 4: Reescrever o preview (célula 8) e a geração (célula 9)**

Preview:

```python
# Preview do relatório: de onde vem cada texto.
from reports.fomc.core.drafting import extract_fenced_block, parse_bank_sections


def _pick_summary(source: str) -> tuple[str, Path]:
    order = {
        "revisao": ["revisao.md"],
        "coletiva": ["resumo_coletiva.md"],
        "decisao": ["resumo_decisao.md"],
        "auto": ["revisao.md", "resumo_coletiva.md", "resumo_decisao.md"],
    }
    for name in order[source]:
        p = OUT_FOLDER / name
        if p.is_file():
            return extract_fenced_block(p.read_text(encoding="utf-8")), p
    raise DraftingError(f"No summary found for SUMMARY_SOURCE={source!r} in {OUT_FOLDER}")


SUMMARY_TEXT_FINAL, SUMMARY_FROM = _pick_summary(SUMMARY_SOURCE)
HEADLINES_FINAL = headlines_for_report(read_headlines(DAY_FOLDER / "headlines.txt"))
_presser_final = read_presser(DAY_FOLDER)
PRESSER_FINAL = headlines_for_report(_presser_final) if _presser_final else None
_banks_path = OUT_FOLDER / "bancos.md"
BANKS_FINAL = (
    parse_bank_sections(extract_fenced_block(_banks_path.read_text(encoding="utf-8")))
    if _banks_path.is_file()
    else {}
)

is_sep = is_sep_meeting(MEETING_DATE)
dt = pd.to_datetime(MEETING_DATE, format="%Y%m%d")
print("=" * 60)
print("PREVIEW DO RELATÓRIO")
print("=" * 60)
print(f"\n📄 Mesa de Investimentos / Depin — Reunião do FOMC – {dt.strftime('%d/%m/%Y')}")
print(f"   Tipo: {'COM SEP' if is_sep else 'SEM SEP'}")
print(f"\n--- CAPA ---")
print(f"  Resumo: {len(SUMMARY_TEXT_FINAL.split())} palavras, de {SUMMARY_FROM.name}")
print(
    f"  Headlines: {len(HEADLINES_FINAL)} itens ({sum(1 for h in HEADLINES_FINAL if h['bold'])} em destaque)"
)
if is_sep:
    print(f"\n--- SEÇÕES SEP ---")
    print(
        f"  Dot plot: {'✓' if DOT_PLOT_PNG and Path(DOT_PLOT_PNG).exists() else '✗ (screenshot necessário)'}"
    )
    print(
        f"  Tabela SEP: {'✓ Atual + Anterior' if sep_prior is not None else '✓ Apenas atual' if sep_current is not None else '✗'}"
    )
    print(f"  Coletiva: {len(PRESSER_FINAL) if PRESSER_FINAL else '— (sem coletiva.txt)'}")
print(f"\n--- REAÇÃO DE MERCADO ---")
print(
    f"  Grid/Imagem: {'✓' if MARKET_REACTION_PNG and Path(MARKET_REACTION_PNG).exists() else '✗ (gerar grid ou apontar screenshot)'}"
)
print(f"\n--- COMENTÁRIOS DOS BANCOS ---")
for bank in BANKS_FINAL or ["(nenhum)"]:
    print(f"  • {bank}")
print("\n" + "=" * 60)
```

Geração:

```python
# GERAR RELATÓRIO WORD — a partir do que o preview escolheu.
output_dir = project_root / "output" / "reports" / "fomc"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"Mesa de Investimentos - FOMC_{MEETING_DATE}.docx"

result_path = generate_fomc_report(
    meeting_date=MEETING_DATE,
    summary_text=SUMMARY_TEXT_FINAL,
    headlines=HEADLINES_FINAL,
    market_reaction_path=MARKET_REACTION_PNG,
    bank_comments=BANKS_FINAL,
    dot_plot_path=DOT_PLOT_PNG if is_sep_meeting(MEETING_DATE) else None,
    sep_current=sep_current,
    sep_prior=sep_prior,
    prior_meeting_label=prior_label,
    presser_headlines=PRESSER_FINAL if is_sep_meeting(MEETING_DATE) else None,
    current_ct=current_ct,
    prior_ct=prior_ct,
    include_ct=True,
    output_path=output_path,
)
print(f"Relatório gerado com sucesso!")
print(f"Arquivo: {result_path}")
```

A função `_pick_summary` aparece nas células F e 8 de propósito: cada célula é executável sozinha depois de um restart, e o notebook não define funções compartilhadas fora do core. Se preferir uma só, mova `_pick_summary` para `drafting.py` como `pick_summary(out_folder: Path, source: str) -> tuple[str, Path]` com teste próprio; nesse caso as duas células importam e chamam.

Atualizar a célula 0 (markdown do fluxo) para listar as etapas: "5. Insumos do dia; 6. Resumo da decisão; 7. Resumo pós-coletiva; 8. Bancos; 9. Revisão; 10. Preview; 11. Word".

- [ ] **Step 5: Rodar os testes e conferir o JSON**

Run: `uv run pytest -q && uv run python -c "import json;json.load(open('src/reports/fomc/notebooks/fomc_analysis.ipynb',encoding='utf-8'));print('json ok')"`
Expected: passa; `json ok`. Conferir que `git diff --stat` do notebook não inclui saídas (o `nbstripout` está ligado pelo `.gitattributes`).

- [ ] **Step 6: Propor commit**

```
Liga as etapas de modelo ao notebook do FOMC e tira o texto da célula

Corpo: resumo, headlines e bancos deixam de viver na célula de configuração, o que
fecha a falha silenciosa do texto da reunião passada. Cada etapa é uma célula que o
autor roda quando o insumo existe; o preview diz de que arquivo vem cada texto, e
SUMMARY_SOURCE escolhe qual resumo vai ao Word.
```

---

### Task 9: documentação do produto

**Files:**
- Modify: `AGENTS.md` (do produto)
- Modify: `README.md` (do produto), se tiver seção de fluxo do FOMC

- [ ] **Step 1: Acrescentar ao `AGENTS.md`, depois de "Convenções de mercado implementadas"**

```markdown
## Etapas de modelo do FOMC

Resumo, comentários dos bancos e revisão de coerência são etapas de modelo em
`fomc/core/drafting.py`, disparadas por células do `fomc_analysis.ipynb`. O backend é
`src/reports/_modelo.py`, **cópia** do `modelo.py` do comentário matinal — nunca
importar `comentario_matinal`; `tests/test_independence.py` falha.

- Chama `claude -p --safe-mode` sem ferramentas, mensagem pela stdin, autenticação
  pela sessão do Claude Code; `ANTHROPIC_API_KEY` sai do ambiente do subprocesso.
  Variável: `INFORMES_EVENTOS_BACKEND` (padrão `claude-code`).
- **Os prompts em `prompts/` são a fonte de verdade editorial.** Para mudar como o
  texto lê, editar `00_guia_de_estilo.md`; o prompt da etapa só quando a mecânica
  mudar. Nada de estilo fixo no Python.
- Pasta do dia: `input/fomc/<AAAAMMDD>/` com `headlines.txt` (linha com `***` é
  destaque), `coletiva.txt` e `bancos/*.pdf` (nome do arquivo = nome do banco).
  Saídas em `output/reports/fomc/<AAAAMMDD>/`. Tudo fora do git e sob a regra de
  sigilo abaixo.
- Nenhum teste chama o `claude`: `subprocess.run` e o registro `BACKENDS` recebem
  dublês.
```

E na seção "Não mexer", acrescentar `input/fomc/` e `output/reports/fomc/<data>/` à lista, e a frase: "As respostas do modelo gravadas ali são minuta de informe: nunca ler nem resumir na conversa."

- [ ] **Step 2: Conferir**

Run: `uv run pytest -q`
Expected: passa (não há teste de documentação neste produto; a conferência é de leitura).

- [ ] **Step 3: Propor commit**

```
Documenta as etapas de modelo do informe do FOMC

Corpo: onde estão o backend e os prompts, o que é cópia e o que não se importa, a
pasta do dia e a regra de sigilo sobre as respostas gravadas.
```

---

## Autorrevisão do plano

**Cobertura da spec.** §3 decisões → Tasks 1, 5, 9. §4 arquivos e formatos → Tasks 3, 5, 6, 8. §5 backend → Task 1. §6.1 insumos e `market_snapshot` → Tasks 3, 4, 5. §6.2 mensagem → Task 5. §6.3–6.5 etapas → Task 7. §6.6 erros → Tasks 3, 5, 7. §7 notebook e `SUMMARY_SOURCE` → Task 8. §8 Word → Task 2. §9 guia → Task 6. §10 testes → cada tarefa; independência e âncoras → Tasks 1 e 3. §11 fluxo do dia → Task 8 (célula 0) e Task 9.

**Consistência de nomes.** `run_stage(stage, message, destination)`; rótulos de etapa `"resumo"`, `"bancos"`, `"revisao"`; arquivos `resumo_decisao.md`, `resumo_coletiva.md`, `bancos.md`, `revisao.md`; blocos `MOMENTO`, `STATEMENT`, `DECISÃO (parse)`, `SEP: MEDIANAS ATUAIS vs ANTERIORES (<label>)`, `HEADLINES BLOOMBERG`, `HEADLINES DA COLETIVA`, `RESUMO DA DECISÃO`, `REAÇÃO DE MERCADO`, `RESEARCH: <banco>`, `TEXTO PARA REVISÃO`, `COMENTÁRIOS DOS BANCOS` — os mesmos nos testes, no código e nos prompts. Na Task 7, o bloco do SEP da etapa de bancos sai sem o rótulo da projeção anterior, de propósito: o prompt de bancos só o usa como referência.

**Placeholders.** Nenhum "TBD", nenhum "remover depois": cada passo traz o código final.
