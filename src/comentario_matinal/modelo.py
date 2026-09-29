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
    nome = os.environ.get(ENV_BACKEND)
    if not nome:
        nome = padrao()
        # Com um backend local instalado neste repositório mas indisponível
        # neste ambiente — um kernel sem o executável no PATH, por exemplo —,
        # quem o esperava só descobriria o Copilot pela espera. Numa cópia sem
        # backend local não há o que avisar: o Copilot é o único.
        if nome == "copilot" and any(hasattr(c, "disponivel")
                                     for c in BACKENDS.values()):
            print(f"Aviso: sem {ENV_BACKEND} e sem backend local disponível "
                  "neste ambiente; usando o copilot.", file=sys.stderr)
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

# Olhar o arquivo a cada segundo. A resposta só está pronta quando traz a linha
# de fim e fica dois segundos sem mudar de tamanho: o agente pode gravá-la em
# mais de um passo, e entre um e outro passam os segundos que o modelo leva
# gerando o resto — a estabilidade sozinha aceitaria a primeira metade.
INTERVALO = 1.0
ESTAVEL = 2.0

# O código de leitura vai em quatro trechos: três espalhados pelo corpo da
# mensagem e o último no fim. Só quem leu tudo junta o código inteiro.
PARTES_DO_CODIGO = 4

RE_LEITURA = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")
RE_FIM = re.compile(r"<!--\s*fim:\s*([0-9a-f]+)\s*-->")


def _trecho(n: int, parte: str) -> str:
    return f"<!-- trecho de leitura {n}/{PARTES_DO_CODIGO}: {parte} -->"


def mensagem_para_o_copilot(mensagem: str, codigo: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e o código em trechos.

    O arquivo é longo, e o agente o lê em pedaços. Pôr o código só no fim
    provaria apenas que ele chegou ao fim — um agente que lesse o começo e
    saltasse para a última linha passaria. Com os trechos a um quarto, à metade
    e a três quartos do texto, e o último no fim, o código inteiro só sai de
    quem leu o corpo todo, que é onde estão as fontes do dia.

    Cada trecho entra numa linha em branco — entre parágrafos, nunca no meio de
    uma tabela, que ele desmancharia para o modelo.
    """
    tamanho = len(codigo) // PARTES_DO_CODIGO
    partes = [codigo[i * tamanho:(i + 1) * tamanho]
              for i in range(PARTES_DO_CODIGO)]
    linhas = mensagem.rstrip().splitlines()

    posicoes = []
    for k in range(1, PARTES_DO_CODIGO):
        alvo = len(linhas) * k // PARTES_DO_CODIGO
        posicoes.append(next((i for i in range(alvo, len(linhas))
                              if not linhas[i].strip()), alvo))
    # De trás para a frente, para que inserir um não desloque os seguintes.
    for k, pos in reversed(list(enumerate(posicoes, 1))):
        linhas[pos:pos] = ["", _trecho(k, partes[k - 1]), ""]

    return (
        SYSTEM_PROMPT + SEPARADOR + "\n".join(linhas) + SEPARADOR
        + "## FIM DA MENSAGEM\n\n"
        + _trecho(PARTES_DO_CODIGO, partes[-1]) + "\n\n"
        f"O código de leitura é a junção, na ordem, dos {PARTES_DO_CODIGO} "
        "trechos de leitura espalhados por esta mensagem. A primeira linha do "
        "arquivo de resposta é exatamente `<!-- leitura: CÓDIGO -->` e a "
        "última é exatamente `<!-- fim: CÓDIGO -->`, com o código no lugar de "
        "CÓDIGO; a saída pedida vai entre as duas.\n"
    )


def tira_codigo(resposta: str, codigo: str, etapa: str) -> str:
    """Confere as linhas de leitura e de fim e devolve o que está entre elas."""
    texto = resposta.lstrip("\ufeff")
    leitura = RE_LEITURA.search(texto[:500])
    if leitura is None:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} não traz a linha de leitura: a "
            "mensagem não foi lida até o fim. Rodar a célula de novo e, no "
            "chat, repetir o comando."
        )
    fins = list(RE_FIM.finditer(texto))
    if not fins:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} não traz a linha de fim: chegou "
            "incompleta. Rodar a célula de novo e repetir o comando no chat."
        )
    fim = fins[-1]
    if leitura.group(1) != codigo or fim.group(1) != codigo:
        raise CodigoDeOutraExecucao(
            f"A resposta da etapa {etapa} traz o código de outra execução, ou "
            "um código montado sem ler a mensagem inteira. Rodar a célula de "
            "novo e repetir o comando no chat."
        )
    corpo = texto[leitura.end():fim.start()].strip()
    if not corpo:
        raise ErroDoModelo(f"A etapa {etapa} devolveu resposta vazia.")
    return corpo


class CodigoDeOutraExecucao(ErroDoModelo):
    """A resposta traz um código que não é o desta execução."""


def _apaga(caminho: Path) -> None:
    """Apaga a resposta; arquivo travado vira erro legível, não traceback."""
    try:
        caminho.unlink(missing_ok=True)
    except PermissionError:
        raise ErroDoModelo(
            f"Não consegui apagar {caminho}: o arquivo está em uso por outro "
            "programa (antivírus, indexador, editor aberto). Fechar o que o "
            "segura e rodar a célula de novo."
        ) from None


def espera_resposta(caminho: Path, etapa: str, limite: float | None = None,
                    recusada: bool = False) -> str:
    """Espera a resposta trazer a linha de fim e parar de crescer.

    ``limite`` é o instante (``time.monotonic``) em que a espera desiste; sem
    ele, vale o ``TEMPO_LIMITE`` a partir de agora. ``recusada`` diz que já se
    descartou uma resposta com o código de outra execução, e muda a mensagem
    de quando o prazo acaba.
    """
    if limite is None:
        limite = time.monotonic() + TEMPO_LIMITE
    tamanho, desde = -1, 0.0
    while time.monotonic() < limite:
        # O Windows trava o arquivo enquanto o agente grava: ler nessa hora
        # falha, e a resposta só não está pronta ainda.
        try:
            if caminho.is_file():
                atual = caminho.stat().st_size
                if atual > 0 and atual == tamanho:
                    if time.monotonic() - desde >= ESTAVEL:
                        texto = caminho.read_text(encoding="utf-8")
                        if RE_FIM.search(texto):
                            return texto
                else:
                    tamanho, desde = atual, time.monotonic()
        except OSError:
            pass
        time.sleep(INTERVALO)
    if recusada:
        raise ErroDoModelo(
            f"Em {TEMPO_LIMITE}s só chegou à etapa {etapa} resposta com o código "
            "de outra execução — de um chat anterior, ou montado sem ler a "
            f"mensagem inteira. Repetir o comando /{COMANDO}-{etapa} no chat."
        )
    if caminho.is_file():
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} ficou incompleta: em {TEMPO_LIMITE}s "
            "não chegou a linha de fim. Rodar a célula de novo e repetir o "
            f"comando /{COMANDO}-{etapa} no chat."
        )
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
        _apaga(resposta)

        codigo = secrets.token_hex(4)
        pedido.write_text(mensagem_para_o_copilot(mensagem, codigo),
                          encoding="utf-8")
        if modelo:
            print(f"Aviso: o modelo {modelo!r} não se escolhe daqui; vale o "
                  "escolhido no chat do Copilot.", file=sys.stderr)
        print(f"\nNo chat do Copilot (Ctrl+Alt+I), em modo agente, digite "
              f"/{COMANDO}-{etapa} e espere. A resposta chega em {resposta}.",
              file=sys.stderr, flush=True)

        # Uma resposta com código de outra execução — o chat de uma rodada
        # anterior terminando agora — é descartada, e a espera continua no
        # mesmo prazo: a de agora pode estar a segundos de chegar.
        limite = time.monotonic() + TEMPO_LIMITE
        recusada = False
        while True:
            texto = espera_resposta(resposta, etapa, limite, recusada)
            try:
                return tira_codigo(texto, codigo, etapa)
            except CodigoDeOutraExecucao:
                recusada = True
                _apaga(resposta)


registra(Copilot)

# Na última linha de propósito: os backends opcionais importam daqui o
# SYSTEM_PROMPT, o TEMPO_LIMITE, o ErroDoModelo e o registra, que a esta altura
# já existem.
_importa_opcionais()
