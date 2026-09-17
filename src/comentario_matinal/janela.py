"""A janela do plantão e o fuso em que ela é medida.

O comentário é produzido e enviado entre 7h00 e 9h00. Fora disso a execução é
ensaio, e o comando carimba as saídas para que um arquivo de teste não seja
confundido com um de plantão — nem por quem o abre depois, nem pelo modelo, que
recebe o painel em texto inteiro e passa a ver o marcador.

O fuso é o da máquina, lido a cada execução. Nesta mesa isso é Brasília; o
relógio de hardware guardar UTC (``RealTimeIsUniversal=1``, padrão de dual boot
com Linux) não interfere, porque o sistema operacional entrega hora local já
convertida e o Python pergunta ao sistema, não ao RTC.

Rodando de outro fuso a janela continua fazendo sentido como hora do analista,
mas as regras temporais do guia não: elas são escritas na relação Brasília↔Nova
York — sessão europeia em curso, mercado americano à vista ainda fechado. Daí
``divergencia``, que não impede nada e manda conferir à mão.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, tzinfo

from comentario_matinal.config import TZ_BR

# Inclusive nas duas pontas: 07h00 e 09h00 são horários de plantão.
ABERTURA = time(7, 0)
FECHAMENTO = time(9, 0)


def faixa() -> str:
    """A janela como o comando a anuncia: "07h00 a 09h00"."""
    return f"{ABERTURA:%Hh%M} a {FECHAMENTO:%Hh%M}"


def fuso_local() -> tzinfo:
    """O fuso da máquina, como offset fixo do instante corrente.

    ``astimezone()`` sem argumento devolve o fuso do sistema. O que volta carrega
    o offset de agora, não as regras de mudança de horário do lugar — suficiente
    aqui, porque tudo o que se mede é a manhã corrente, e não datas distantes.
    """
    return datetime.now().astimezone().tzinfo


def agora() -> datetime:
    """O instante corrente no fuso da máquina."""
    return datetime.now(fuso_local())


def na_janela(momento: datetime) -> bool:
    """Diz se o horário de parede de ``momento`` cai dentro da janela.

    Lê o horário como ele veio, sem converter de fuso: a janela é a hora do
    analista, e quem chama já entrega o instante no fuso em que ele trabalha.
    """
    return ABERTURA <= momento.time() <= FECHAMENTO


def _offset(delta: timedelta | None) -> str:
    """Formata um offset como UTC−03:00, com o sinal do lado certo."""
    total = int((delta or timedelta()).total_seconds())
    sinal = "+" if total >= 0 else "−"
    horas, resto = divmod(abs(total), 3600)
    return f"UTC{sinal}{horas:02d}:{resto // 60:02d}"


def rotulo_fuso(momento: datetime) -> str:
    """Como nomear o fuso de um carimbo.

    Carimbar "de Brasília" um horário que não é de Brasília faria a etapa aplicar
    a elegibilidade temporal do guia contra a referência errada — e o erro seria
    invisível, porque o texto continuaria parecendo correto.
    """
    if momento.utcoffset() == momento.astimezone(TZ_BR).utcoffset():
        return "de Brasília"
    return f"do fuso local ({_offset(momento.utcoffset())})"


def divergencia() -> str | None:
    """Aviso quando a máquina não está no fuso para o qual o processo foi escrito."""
    local = datetime.now().astimezone()
    if local.utcoffset() == datetime.now(TZ_BR).utcoffset():
        return None
    return (
        f"Aviso: o fuso desta máquina é {_offset(local.utcoffset())}, e não o de "
        f"Brasília ({_offset(datetime.now(TZ_BR).utcoffset())}). A janela de "
        f"{faixa()} passa a ser medida na hora local, mas as regras temporais do "
        "guia pressupõem a relação Brasília↔Nova York — sessão europeia em curso, "
        "mercado americano à vista ainda fechado. Conferir a elegibilidade das "
        "fontes à mão, e conferir também o calendário: os horários do BQL chegam "
        "no fuso do terminal."
    )
