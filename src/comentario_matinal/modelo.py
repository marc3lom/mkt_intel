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
import sys
from typing import Protocol

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


# Na última linha de propósito: os backends opcionais importam daqui o
# SYSTEM_PROMPT, o TEMPO_LIMITE, o ErroDoModelo e o registra, que a esta altura
# já existem.
_importa_opcionais()
