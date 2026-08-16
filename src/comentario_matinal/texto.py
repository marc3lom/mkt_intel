"""O bloco direcional em texto, gerado a partir do que a imagem mostrou.

As direções aqui não são recalculadas dos campos de referência: elas saem das
métricas que o construtor do painel devolveu, isto é, exatamente os números que
cada tile renderizou. É isso que impede a imagem enviada à diretoria e o texto
usado na checagem de discordarem sobre a direção de um mesmo ativo.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from comentario_matinal.calendario import Evento
from comentario_matinal.config import Config

TZ_NY = ZoneInfo("America/New_York")


def _direcao(variacao: float, limiar: float) -> str:
    """Traduz uma variação em direção qualitativa.

    O limiar existe para que ruído não seja narrado como movimento: tudo dentro
    da banda é reportado como estável, que é o que o comentário deve dizer também.
    """
    if variacao != variacao:  # NaN
        return "indisponível"
    if abs(variacao) < limiar:
        return "estável"
    return "alta" if variacao > 0 else "baixa"


def monta_texto(
    cfg: Config,
    metricas: dict[str, dict],
    eventos: list[Evento],
    asof: datetime,
    indisponiveis: list[str],
    calendario_vazio: bool,
    dry_run: bool = False,
) -> str:
    from comentario_matinal.janela import rotulo_fuso

    out: list[str] = []
    asof_ny = asof.astimezone(TZ_NY)
    fuso = rotulo_fuso(asof)

    # O marcador vai no título, e nunca na linha "Referência:" — é ela que
    # etapas.referencia_do_painel casa para achar o horário de redação, e é este
    # texto inteiro que vai injetado na mensagem das três etapas. Assim o modelo
    # também sabe que está num ensaio, sem código novo no caminho das etapas.
    out.append("PAINEL DIRECIONAL — DRY RUN" if dry_run else "PAINEL DIRECIONAL")
    out.append(f"Referência: {asof:%d/%m/%Y %H:%M} {fuso} "
               f"({asof_ny:%H:%M} de Nova York)")
    out.append("Direções apuradas contra o fechamento anterior, a partir dos mesmos "
               "dados do painel enviado. Sem níveis — uso exclusivo para checagem "
               "de coerência.")
    out.append("")

    taxas = [a for a in cfg.ativos if a.e_taxa]
    precos = [a for a in cfg.ativos if not a.e_taxa]

    out.append("Taxas (direção da taxa):")
    for ativo in taxas:
        m = metricas.get(ativo.ticker)
        if m is None or ativo.ticker in indisponiveis:
            direcao = "indisponível"
        else:
            # Para taxa, a variação líquida já está em pontos percentuais da
            # própria taxa; o limiar é expresso na mesma unidade (0.01 = 1 bp).
            direcao = _direcao(float(m["chg_net"]), cfg.limiar_estabilidade_taxa)
        out.append(f"  {ativo.rotulo}: {direcao}")

    out.append("")
    out.append("Preços:")
    for ativo in precos:
        m = metricas.get(ativo.ticker)
        if m is None or ativo.ticker in indisponiveis:
            direcao = "indisponível"
        else:
            direcao = _direcao(float(m["chg_pct"]), cfg.limiar_estabilidade)
        out.append(f"  {ativo.rotulo}: {direcao}")

    out.append("")
    out.append("CALENDÁRIO ECONÔMICO DO DIA")
    if calendario_vazio:
        out.append("  CONSULTA INDISPONÍVEL — o calendário não pôde ser apurado nesta")
        out.append("  execução. Conferir à mão antes de publicar; não tratar nenhum")
        out.append("  indicador como divulgado sem essa conferência.")
    elif not eventos:
        out.append("  Sem releases acompanhados para a data.")
    else:
        out.append(f"Status apurado contra o horário de redação "
                   f"({asof:%Hh%M} {fuso}).")
        for e in eventos:
            pais = f"{e.pais} — " if e.pais else ""
            out.append(f"  {pais}{e.evento} — previsto para {e.horario} — {e.status}")

    out.append("")
    out.append("Nota: item marcado como AINDA NÃO DIVULGADO não pode aparecer no "
               "comentário como fato consumado, ainda que citado por wrap de fonte.")

    return "\n".join(out)
