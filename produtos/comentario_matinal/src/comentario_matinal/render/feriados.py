"""Detecção de feriado de mercado para o painel de monitoramento.

O painel desenha o selo de "mercado fechado" sempre que o Bloomberg não devolve
barras intradiárias para um instrumento. Isso sozinho não distingue um feriado
de bolsa genuíno de um erro de dado. Este módulo mapeia cada ticker a um
calendário do ``pandas-market-calendars`` e informa se aquele mercado está
fechado por feriado num dia dado, para que o painel rotule o tile "Feriado" em
vez do selo genérico de fechado.

Câmbio, ouro, petróleo e cripto negociam ~24/5 e não têm um calendário de
feriado de bolsa única confiável, então ficam de fora de propósito (ver
``ativos.CALENDARIOS_DE_MERCADO``) e mantêm o selo genérico de fechado.
"""

import logging
from datetime import date, datetime

import pandas as pd

from comentario_matinal.render.ativos import CALENDARIOS_DE_MERCADO

logger = logging.getLogger("comentario_matinal")

# Cache dos objetos de calendário — construí-los não é trivial e os tickers se repetem.
_CAL_CACHE: dict[str, object] = {}


def _get_calendar(name: str):
    if name not in _CAL_CACHE:
        import pandas_market_calendars as mcal

        _CAL_CACHE[name] = mcal.get_calendar(name)
    return _CAL_CACHE[name]


def e_feriado_de_mercado(ticker: str, dia: date | None = None) -> bool:
    """Retorna True se a bolsa mapeada de ``ticker`` estiver fechada por feriado.

    Retorna False quando o mercado está aberto, quando ``dia`` cai num fim de
    semana (não é "feriado"), ou quando o ticker não tem calendário mapeado.
    Pregões de fechamento antecipado / meio expediente contam como abertos e
    retornam False.

    O painel usa isto para forçar o tile de "mercado fechado" num feriado
    mesmo quando algumas barras avulsas chegam (ex.: USGG10YR continua
    marcando por conta do pregão overnight de Londres/Ásia num feriado da
    SIFMA).
    """
    name = CALENDARIOS_DE_MERCADO.get(ticker)
    if name is None:
        return False

    dia = dia or datetime.now().date()
    ts = pd.Timestamp(dia)
    if ts.weekday() >= 5:  # fim de semana — não é feriado
        return False

    try:
        cal = _get_calendar(name)
        sched = cal.schedule(start_date=ts, end_date=ts)
    except Exception as e:
        logger.warning("Consulta de feriado falhou para %s (%s): %s", ticker, name, e)
        return False

    return len(sched) == 0  # sem pregão nesse dia → feriado
