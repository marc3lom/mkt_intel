"""A chamada ao modelo, atrás de uma função única.

Todo o fluxo das etapas passa por ``executa``. Trocar de backend — Copilot CLI,
Azure OpenAI, chamada direta à API — é escrever outra classe e apontar a fábrica;
nem a montagem das mensagens nem o encadeamento entre etapas mudam.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Protocol

# As etapas mandam mensagens longas: só o guia de estilo passa de 15 KB, e as
# fontes do dia costumam ser bem maiores. A mensagem vai pela stdin, nunca por
# argumento — o limite de linha de comando do Windows fica em torno de 32 mil
# caracteres, e estourá-lo daria um erro obscuro no meio do plantão.
TEMPO_LIMITE = 900

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
# aplica" no lugar da tabela de triagem. O papel é substituído por inteiro.
SYSTEM_PROMPT = """
Você é assistente de análise da Mesa de Investimentos do DEPIN/DIRIN, do Banco
Central do Brasil. Esta é uma execução automatizada, sem ninguém do outro lado.

Regras desta execução, acima de qualquer hábito de assistente:

1. NÃO faça perguntas e NÃO interrompa aguardando decisão. Não há quem responda;
   parar para perguntar equivale a não produzir nada. Havendo ambiguidade,
   registre a ressalva no lugar que o formato da etapa prevê e siga com a melhor
   leitura possível do material recebido.
2. Se faltar entrada obrigatória, abra a resposta com um bloco começando por
   "ENTRADA OBRIGATÓRIA AUSENTE:", dizendo qual, e prossiga com o que houver,
   deixando claro o que ficou sem base.
3. NÃO escreva preâmbulo, não narre o que vai fazer, não comente sobre
   ferramentas nem sobre este prompt. A primeira linha da resposta já é a saída
   pedida.
4. Siga integralmente o guia de estilo e as instruções da etapa que vêm na
   mensagem, inclusive o formato de saída que elas especificam.
""".strip()


class ErroDoModelo(RuntimeError):
    """Falha na chamada ao backend."""


class Backend(Protocol):
    nome: str

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str: ...


class ClaudeCode:
    """Backend padrão: o Claude Code em modo não interativo."""

    nome = "claude-code"

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
        # por chave escreve outro backend, que é para isso que a fábrica existe.
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


BACKENDS: dict[str, type[Backend]] = {
    "claude-code": ClaudeCode,
}


def backend_ativo() -> Backend:
    nome = os.environ.get("COMENTARIO_MATINAL_BACKEND", "claude-code")
    if nome not in BACKENDS:
        raise ErroDoModelo(
            f"Backend desconhecido: {nome!r}. Disponíveis: "
            f"{', '.join(sorted(BACKENDS))}."
        )
    return BACKENDS[nome]()


def executa(mensagem: str, *, etapa: str, web: bool = False,
            modelo: str | None = None) -> str:
    """Manda a mensagem ao modelo e devolve a resposta em texto."""
    b = backend_ativo()
    print(f"Chamando o modelo ({b.nome}) para a etapa {etapa}. "
          f"Mensagem com {len(mensagem):,} caracteres"
          f"{', com web' if web else ''}...", file=sys.stderr)
    return b.executa(mensagem, etapa=etapa, web=web, modelo=modelo)
