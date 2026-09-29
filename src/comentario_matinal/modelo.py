"""A chamada ao modelo, atrás de uma função única.

Todo o fluxo das etapas passa por ``executa``. Trocar de backend é escrever
outra classe e registrá-la; nem a montagem das mensagens nem o encadeamento
entre etapas mudam.

Backends opcionais moram em módulos ``_backend_*.py`` deste pacote, importados
aqui, e cada um se registra com ``registra`` no fim do próprio módulo. Um
backend opcional que responde ``disponivel()`` verdadeiro vira o padrão; sem
nenhum, o padrão é o que não depende de programa algum instalado.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Protocol

from comentario_matinal.config import SAIDA_PADRAO

# As etapas mandam mensagens longas: só o guia de estilo passa de 15 KB, e as
# fontes do dia costumam ser bem maiores.
TEMPO_LIMITE = 900

SEPARADOR = "\n\n" + "=" * 70 + "\n\n"

# As regras de uma execução automatizada. Valem para todo backend: o que roda
# um programa as passa como papel do sistema; o que conversa por arquivo as põe
# no topo do arquivo. Sem elas, um assistente abre a resposta narrando o que vai
# fazer, ou para esperando uma decisão que ninguém vai tomar.
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

ENV_BACKEND = "COMENTARIO_MATINAL_BACKEND"


class ErroDoModelo(RuntimeError):
    """Falha na chamada ao backend."""


class Backend(Protocol):
    nome: str

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str: ...


BACKENDS: dict[str, type[Backend]] = {}


def registra(classe: type[Backend]) -> None:
    """Põe um backend no registro. Os opcionais chamam isto no fim do módulo."""
    BACKENDS.setdefault(classe.nome, classe)


def _importa_opcionais() -> None:
    """Importa cada ``_backend_*.py`` do pacote, que se registra sozinho.

    O registro é do próprio módulo, e não daqui, por causa da importação
    circular: quem importa um backend opcional primeiro faz este arquivo rodar
    com aquele módulo ainda pela metade, e ler um atributo dele aqui falharia.
    """
    import comentario_matinal

    for info in pkgutil.iter_modules(comentario_matinal.__path__):
        if info.name.startswith("_backend_"):
            importlib.import_module(f"comentario_matinal.{info.name}")


def padrao() -> str:
    """O backend sem variável de ambiente: o opcional disponível, senão o copilot."""
    for nome, classe in BACKENDS.items():
        disponivel = getattr(classe, "disponivel", None)
        if disponivel is not None and disponivel():
            return nome
    return "copilot"


def backend_ativo() -> Backend:
    nome = os.environ.get(ENV_BACKEND) or padrao()
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


# --------------------------------------------------------------------------
# Copilot: a conversa é por arquivo
# --------------------------------------------------------------------------

# Pasta fixa porque os prompt files de `.github/prompts/` a citam por caminho: o
# agente do Copilot não recebe argumento, lê e grava onde o prompt manda.
PASTA_COPILOT = SAIDA_PADRAO / "copilot"
COMANDO = "matinal"

# Olhar o arquivo a cada segundo, e só aceitá-lo depois de dois segundos sem
# mudar de tamanho: o agente pode gravar a resposta em mais de um passo, e ler
# no meio entregaria metade dela à etapa seguinte.
INTERVALO = 1.0
ESTAVEL = 2.0

RE_LEITURA = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")


def mensagem_para_o_copilot(mensagem: str, codigo: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e, no fim, o código.

    O código vai na última linha de propósito. O arquivo é longo, o agente o lê
    em trechos, e só quem chegou ao fim sabe qual código devolver — é a prova
    de que as fontes do dia foram lidas inteiras, e não só o começo.
    """
    return (
        SYSTEM_PROMPT + SEPARADOR + mensagem.rstrip() + SEPARADOR
        + "## FIM DA MENSAGEM\n\n"
        "A primeira linha do arquivo de resposta é exatamente "
        f"`<!-- leitura: {codigo} -->`; a saída pedida começa na linha "
        "seguinte.\n"
    )


def tira_codigo(resposta: str, codigo: str, etapa: str) -> str:
    """Confere o código de leitura e o tira da resposta."""
    texto = resposta.lstrip("\ufeff")
    achado = RE_LEITURA.search(texto[:500])
    if achado is None:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} não traz a linha de leitura: a "
            "mensagem não foi lida até o fim. Rodar a célula de novo e, no "
            "chat, repetir o comando."
        )
    if achado.group(1) != codigo:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} traz o código de outra execução. "
            "Rodar a célula de novo e repetir o comando no chat."
        )
    corpo = (texto[:achado.start()] + texto[achado.end():]).strip()
    if not corpo:
        raise ErroDoModelo(f"A etapa {etapa} devolveu resposta vazia.")
    return corpo


def espera_resposta(caminho: Path, etapa: str) -> str:
    """Espera o arquivo de resposta aparecer e parar de crescer."""
    limite = time.monotonic() + TEMPO_LIMITE
    tamanho, desde = -1, 0.0
    while time.monotonic() < limite:
        if caminho.is_file():
            atual = caminho.stat().st_size
            if atual > 0 and atual == tamanho:
                if time.monotonic() - desde >= ESTAVEL:
                    return caminho.read_text(encoding="utf-8")
            else:
                tamanho, desde = atual, time.monotonic()
        time.sleep(INTERVALO)
    raise ErroDoModelo(
        f"Nenhuma resposta da etapa {etapa} em {TEMPO_LIMITE}s. No chat do "
        f"Copilot, em modo agente, o comando é /{COMANDO}-{etapa}."
    )


class Copilot:
    """O GitHub Copilot do VS Code, pelo chat em modo agente.

    Não há programa a chamar: a mensagem vai para um arquivo, a pessoa roda o
    comando da etapa no chat, e o agente grava a resposta noutro. A célula fica
    esperando enquanto isso — interromper o kernel cancela a espera.
    """

    nome = "copilot"

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str:
        if web:
            raise ErroDoModelo(
                "O backend copilot não libera a web: o prompt file da etapa só "
                "lê e grava arquivos. Rodar a etapa com web=False."
            )
        PASTA_COPILOT.mkdir(parents=True, exist_ok=True)
        pedido = PASTA_COPILOT / f"{etapa}.mensagem.md"
        resposta = PASTA_COPILOT / f"{etapa}.resposta.md"
        # A de uma execução anterior passaria pela de agora.
        resposta.unlink(missing_ok=True)

        codigo = secrets.token_hex(4)
        pedido.write_text(mensagem_para_o_copilot(mensagem, codigo),
                          encoding="utf-8")
        if modelo:
            print(f"Aviso: o modelo {modelo!r} não se escolhe daqui; vale o "
                  "escolhido no chat do Copilot.", file=sys.stderr)
        print(f"\nNo chat do Copilot (Ctrl+Alt+I), em modo agente, digite "
              f"/{COMANDO}-{etapa} e espere. A resposta chega em {resposta}.",
              file=sys.stderr, flush=True)

        return tira_codigo(espera_resposta(resposta, etapa), codigo, etapa)


registra(Copilot)

# Na última linha de propósito: os backends opcionais importam daqui o
# SYSTEM_PROMPT, o TEMPO_LIMITE, o ErroDoModelo e o registra, que a esta altura
# já existem.
_importa_opcionais()
