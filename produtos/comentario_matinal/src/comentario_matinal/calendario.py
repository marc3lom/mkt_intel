"""Calendário econômico — tabela e status de divulgação, da mesma consulta.

A tabela enviada à diretoria e o bloco de status usado na checagem do comentário
saem do mesmo ``DataFrame`` do BQL. O que os separa é apenas o recorte: a tabela
mostra a janela do dia anterior e do dia, como a camada de renderização sempre
fez; o bloco de status olha só o dia da redação.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from comentario_matinal.config import TZ_BR

# O horário do BQL chega no fuso do terminal, que nesta mesa é Brasília.
# Verificado empiricamente contra releases de horário fixo conhecido:
#   US Initial Jobless Claims / PPI  ->  09:30  (08:30 de Nova York, +1h)
#   US U. of Mich. Sentiment         ->  11:00  (10:00 de Nova York, +1h)
#   Eurozone GDP SA QoQ              ->  06:00  (11:00 de Bruxelas, -5h)
#   UK GDP / Industrial Production   ->  03:00  (07:00 de Londres, -4h)
# Fosse hora local de praça, o europeu apareceria como 11:00 e o britânico como
# 07:00. Aparecem deslocados pelo delta exato de Brasília, então o fuso é único.
FUSO_BQL = TZ_BR


@dataclass(frozen=True)
class Evento:
    """Um release econômico do dia, com o status apurado."""

    pais: str
    evento: str
    horario: str
    momento: datetime | None
    divulgado: bool | None   # None = horário não informado, status indeterminado

    @property
    def status(self) -> str:
        if self.divulgado is None:
            return "STATUS INDETERMINADO — VERIFICAR"
        return "DIVULGADO" if self.divulgado else "AINDA NÃO DIVULGADO"


def coleta_calendario() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Puxa o calendário econômico e os eventos de bancos centrais via BQL.

    O BQL é acessado pelo ``polars-bloomberg`` e não pelo xbbg: a licença
    Bloomberg Anywhere exige a tag ``clientContext.appName=EXCEL``, que o endpoint
    BQL do xbbg não envia — a chamada volta como "User not authorized to use BQL".
    Por isso esta consulta é separada da de mercado; não há como fundi-las.
    """
    from comentario_matinal.bql import busca_bancos_centrais, busca_calendario

    eco = busca_calendario()
    bancos = busca_bancos_centrais()

    # Sem isto, o bloco de calendário desaparece em silêncio e a checagem de
    # status some junto, sem ninguém notar que ela deixou de acontecer.
    if eco.empty:
        print("Aviso: a consulta BQL do calendário econômico voltou vazia. "
              "O bloco de status NÃO foi apurado nesta execução — conferir o "
              "calendário à mão antes de publicar.", file=sys.stderr)
    if bancos.empty:
        print("Aviso: a consulta BQL de bancos centrais voltou vazia.",
              file=sys.stderr)

    return eco, bancos


def tabela_markdown(eco: pd.DataFrame, bancos: pd.DataFrame) -> str:
    """Renderiza o calendário como texto, para alimentar as etapas de IA.

    A imagem serve ao e-mail; o modelo recebe texto. É a mesma razão pela qual o
    bloco direcional existe: pedir a um modelo que leia número em gráfico é a
    coisa menos confiável que ele faz, e a origem dos dois erros que este
    processo existe para impedir.
    """
    def bloco(titulo: str, df: pd.DataFrame) -> list[str]:
        if df is None or df.empty:
            return [f"### {titulo}", "", "Sem eventos.", ""]
        colunas = list(df.columns)
        linhas = [f"### {titulo}", "",
                  "| " + " | ".join(colunas) + " |",
                  "|" + "|".join(["---"] * len(colunas)) + "|"]
        for _, r in df.iterrows():
            celulas = ["-" if pd.isna(r[c]) else str(r[c]).strip() for c in colunas]
            linhas.append("| " + " | ".join(celulas) + " |")
        linhas.append("")
        return linhas

    return "\n".join(bloco("CALENDÁRIO ECONÔMICO", eco)
                     + bloco("BANCOS CENTRAIS", bancos)).strip() + "\n"


def _momento(data: object, horario: object) -> datetime | None:
    """Combina as colunas DATA e HORÁRIO do BQL num instante com fuso."""
    if data is None or horario is None:
        return None
    texto_data, texto_hora = str(data).strip(), str(horario).strip()
    if not texto_data or not texto_hora or texto_hora.lower() in {"nan", "none"}:
        return None
    for formato in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(f"{texto_data} {texto_hora}", formato).replace(tzinfo=FUSO_BQL)
        except ValueError:
            continue
    return None


def eventos_do_dia(eco: pd.DataFrame, asof: datetime) -> list[Evento]:
    """Filtra o calendário para o dia da redação e apura o status de cada release.

    O status vem da comparação entre o horário de divulgação e o horário de
    redação, e nunca de o valor efetivo estar preenchido. Um índice econômico
    carrega o print anterior indefinidamente: às 7h40 o valor presente é o número
    do mês passado, não o do dia. Testar o valor marcaria como divulgado todo
    indicador acompanhado, que é exatamente o erro que este bloco existe para
    impedir.
    """
    if eco.empty:
        return []

    eventos: list[Evento] = []
    for _, linha in eco.iterrows():
        momento = _momento(linha.get("DATA"), linha.get("HORÁRIO"))

        if momento is None:
            # Sem horário não dá para descartar o release; sinaliza em vez de
            # adivinhar. Só entra se a data for a de hoje.
            data_txt = str(linha.get("DATA", "")).strip()
            if data_txt != asof.strftime("%Y-%m-%d"):
                continue
            eventos.append(Evento(
                pais=str(linha.get("PAÍS", "")).strip(),
                evento=str(linha.get("EVENTO", "")).strip(),
                horario="horário não informado",
                momento=None,
                divulgado=None,
            ))
            continue

        if momento.date() != asof.date():
            continue

        eventos.append(Evento(
            pais=str(linha.get("PAÍS", "")).strip(),
            evento=str(linha.get("EVENTO", "")).strip(),
            horario=f"{momento:%Hh%M}",
            momento=momento,
            divulgado=momento <= asof,
        ))

    eventos.sort(key=lambda e: (e.momento is None, e.momento or asof))
    return eventos
