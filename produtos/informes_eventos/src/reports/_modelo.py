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
