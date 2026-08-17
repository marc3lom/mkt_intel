"""Definição do item de grade e mapeamentos de referência do painel."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemDaGrade:
    """Representa um único ativo monitorado."""

    ticker: str
    nome: str
    rotulo: str
    tipo: str  # "rate", "equity", "fx", "commodity", "vol"


# Calendários de bolsa (nomes do pandas-market-calendars) para detecção de
# feriado. Usado por comentario_matinal.render.feriados para distinguir um
# feriado de bolsa genuíno ("Feriado")
# de um erro de dado por ausência de barras intradiárias. Só instrumentos com
# um calendário de bolsa única confiável estão mapeados; câmbio, ouro,
# petróleo e cripto negociam ~24/5 e não têm esse tipo de calendário, então
# ficam de fora de propósito e caem no selo genérico de "mercado fechado".
CALENDARIOS_DE_MERCADO: dict[str, str] = {
    "USGG10YR Index": "SIFMAUS",   # US Treasury cash (SIFMA bond calendar)
    "ES1 Index": "CME_Equity",     # S&P 500 future (CME)
    "GDBR10 Index": "EUREX_Bond",  # Bund / German govt 10y (Eurex bond)
    "VG1 Index": "EUREX",          # EuroStoxx 50 future (Eurex)
    "NK1 Index": "JPX",            # Nikkei 225 future (Osaka / JPX)
    "GJGB10 Index": "JPX",         # JGB 10y yield index (Japan)
    "GUKG10 Index": "LSE",         # Gilt 10y (UK)
    "Z 1 Index": "LSE",            # FTSE 100 future (ICE Europe, feriados do UK)
    "GCNY10YR Index": "XSHG",      # China govt 10y (mainland China calendar)
    "IFB1 Index": "XSHG",          # CSI 300 future (CFFEX ~ mainland China)
    "VIX Index": "CFE",            # VIX (CBOE)
}
