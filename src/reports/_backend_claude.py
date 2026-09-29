"""O backend local: a CLI do Claude Code em modo não interativo.

Módulo próprio, e não classe dentro do `_modelo.py`, porque o registro de lá
importa todo módulo `_backend_*.py` do pacote, e cada um se registra sozinho.
Assim o `_modelo.py` não cita este backend, e uma cópia do repositório sem este
arquivo continua funcionando com os demais.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from reports._modelo import ENV_BACKEND, SYSTEM_PROMPT, TIMEOUT, ModelError, register

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


# A CLI do Claude Code roda por padrão como agente de programação: descobre
# CLAUDE.md, carrega skills e narra o que vai fazer. O papel é substituído por
# inteiro, pelo SYSTEM_PROMPT do registro.
class ClaudeCode:
    """Backend local: o Claude Code em modo não interativo."""

    name = "claude-code"

    @staticmethod
    def available() -> bool:
        """Há CLI nesta máquina? É o que decide o padrão, sem variável de ambiente."""
        return shutil.which("claude") is not None

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

        # A mensagem vai pela stdin, nunca por argumento — o limite de linha de
        # comando do Windows fica em torno de 32 mil caracteres.
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


register(ClaudeCode)
