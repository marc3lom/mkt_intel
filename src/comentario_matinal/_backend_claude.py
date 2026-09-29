"""O backend local: a CLI do Claude Code em modo não interativo.

Módulo próprio, e não classe dentro do `modelo.py`, porque o registro de lá
descobre backends opcionais pelo prefixo `_backend_` do nome do módulo. Assim o
`modelo.py` não cita este backend, e uma cópia do repositório sem este arquivo
continua funcionando com os demais.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from comentario_matinal.modelo import (
    SYSTEM_PROMPT,
    TEMPO_LIMITE,
    ErroDoModelo,
    registra,
)

# A mensagem vai pela stdin, nunca por argumento — o limite de linha de comando
# do Windows fica em torno de 32 mil caracteres, e estourá-lo daria um erro
# obscuro no meio do plantão.

# Sem ferramenta alguma por padrão. Tudo o que a etapa precisa vai injetado na
# mensagem, então acesso a arquivo só acrescentaria não-determinismo — e, no caso
# da web, o risco de o modelo introduzir tema que não está nas fontes do dia.
FERRAMENTAS_BLOQUEADAS = [
    "Bash", "Read", "Write", "Edit", "NotebookEdit", "Glob", "Grep",
    "Task", "WebSearch", "WebFetch",
]
FERRAMENTAS_WEB = ["WebSearch", "WebFetch"]


# A CLI do Claude Code roda por padrão como agente de programação: descobre
# CLAUDE.md, carrega skills e hooks, e narra o que vai fazer. Numa etapa do
# plantão isso aparece como preâmbulo do tipo "vou verificar se alguma skill se
# aplica" no lugar da tabela de triagem. O papel é substituído por inteiro, pelo
# SYSTEM_PROMPT do registro.
class ClaudeCode:
    """Backend local: o Claude Code em modo não interativo."""

    nome = "claude-code"

    @staticmethod
    def disponivel() -> bool:
        """Há CLI nesta máquina? É o que decide o padrão, sem variável de ambiente."""
        return shutil.which("claude") is not None

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str:
        executavel = shutil.which("claude")
        if not executavel:
            raise ErroDoModelo(
                "O executável `claude` não está no PATH. Instale o Claude Code "
                "ou aponte outro backend em COMENTARIO_MATINAL_BACKEND."
            )

        bloqueadas = [f for f in FERRAMENTAS_BLOQUEADAS
                      if not (web and f in FERRAMENTAS_WEB)]
        # --safe-mode pula descoberta de CLAUDE.md, hooks, skills, plugins, MCP
        # e agentes do ambiente do usuário: a etapa tem de render o mesmo
        # resultado em qualquer máquina, e não herdar a configuração de quem
        # está de plantão. Aqui era --bare, que desliga a mesma lista mas
        # também restringe a autenticação a ANTHROPIC_API_KEY ou apiKeyHelper —
        # a sessão do Claude Code nunca é lida, e numa máquina autenticada por
        # assinatura toda etapa morre com código 1 antes de chegar ao modelo.
        comando = [executavel, "-p", "--safe-mode",
                   "--system-prompt", SYSTEM_PROMPT,
                   "--disallowed-tools", *bloqueadas]
        # Sem --model, vale a configuração da CLI do usuário: fixar o modelo aqui
        # esconderia uma decisão de custo dentro do código.
        if modelo:
            comando += ["--model", modelo]

        # O plantão autentica pela sessão do Claude Code. Uma chave de API
        # esquecida no ambiente tem precedência sobre ela, então uma chave
        # antiga, de conta sem saldo ou de outra organização, sombreia em
        # silêncio uma assinatura válida e derruba a etapa. Quem quiser rodar
        # por chave escreve outro backend, que é para isso que o registro existe.
        ambiente = {k: v for k, v in os.environ.items()
                    if k != "ANTHROPIC_API_KEY"}

        try:
            r = subprocess.run(
                comando, input=mensagem, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=TEMPO_LIMITE,
                env=ambiente,
            )
        except subprocess.TimeoutExpired:
            raise ErroDoModelo(
                f"A etapa {etapa} passou de {TEMPO_LIMITE}s sem responder."
            ) from None

        if r.returncode != 0:
            # Ao falhar, a CLI escreve o motivo no stdout — "Credit balance is
            # too low", "Not logged in" — e deixa o stderr vazio. Ler só o
            # stderr, como se fazia aqui, produzia "saiu com código 1" sem
            # motivo nenhum: às sete da manhã isso custa a reprodução à mão de
            # algo que o processo já tinha na tela.
            erro = " ".join(t for t in ((r.stderr or "").strip(),
                                        (r.stdout or "").strip()) if t)
            raise ErroDoModelo(
                f"`claude` saiu com código {r.returncode}. {erro[-600:]}")

        # Fora do caminho de erro, o stdout traz só a resposta.
        saida = (r.stdout or "").strip()
        if not saida:
            raise ErroDoModelo(f"A etapa {etapa} devolveu resposta vazia.")
        return saida


registra(ClaudeCode)
