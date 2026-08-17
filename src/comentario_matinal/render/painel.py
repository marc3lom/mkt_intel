"""Renderização do painel de monitoramento — sparklines + grade 4x4."""

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.estilo import (
    CORES,
    FONTES,
    MONITOR_FIGSIZE,
    MONITOR_GRID,
    SPARKLINE_FILL_ALPHA,
    SPARKLINE_LINE_WIDTH,
    SPARKLINE_YLIM,
)
from comentario_matinal.render.feriados import e_feriado_de_mercado
from comentario_matinal.render.gravacao import grava_figura
from comentario_matinal.render.ativos import ItemDaGrade


# ---------------------------------------------------------------------------
# Formatadores de ativo — devolvem (is_positive, value_str, change_str)
# ---------------------------------------------------------------------------


def _format_rate(px_last: float, chg_net: float, chg_pct: float):
    return chg_net >= 0, f"{px_last:.3f}%", f"({chg_net * 100:+.1f} bps)"


def _format_vol(px_last: float, chg_net: float, chg_pct: float):
    return chg_net <= 0, f"{px_last:.2f}", f"({chg_net:+.2f} pts)"


def _format_commodity(px_last: float, chg_net: float, chg_pct: float):
    return chg_pct >= 0, f"${px_last:.2f}", f"({chg_pct:+.2f} %)"


def _format_default(px_last: float, chg_net: float, chg_pct: float):
    if px_last >= 1000:
        value_str = f"{px_last:,.0f}"
    else:
        value_str = f"{px_last:.3f}" if px_last < 100 else f"{px_last:.2f}"
    return chg_pct >= 0, value_str, f"({chg_pct:+.2f} %)"


FORMATTERS = {
    "rate": _format_rate,
    "vol": _format_vol,
    "commodity": _format_commodity,
    "equity": _format_default,
    "fx": _format_default,
}


# ---------------------------------------------------------------------------
# Ajudantes de sparkline
# ---------------------------------------------------------------------------


def normaliza_serie(price_series: pd.Series) -> tuple[np.ndarray, float]:
    """Normaliza preços intradiários para escala 0-1 usando mínimo/máximo.

    Retorna (normalized_values, midpoint), onde midpoint é a posição
    normalizada do preço de abertura.
    """
    min_price = price_series.min()
    max_price = price_series.max()

    if max_price == min_price:
        return np.full(len(price_series), 0.5), 0.5

    normalized = (price_series.values - min_price) / (max_price - min_price)
    midpoint = (price_series.values[0] - min_price) / (max_price - min_price)
    return normalized, midpoint


def desenha_sparkline(
    ax: plt.Axes,
    price_series: pd.Series,
    positive_color: str = CORES["positive"],
    negative_color: str = CORES["negative"],
    line_width: float = SPARKLINE_LINE_WIDTH,
    fill_alpha: float = SPARKLINE_FILL_ALPHA,
) -> None:
    """Desenha o sparkline com áreas verde/vermelha a partir do ponto médio."""
    if price_series.empty or len(price_series) < 2:
        return

    normalized, midpoint = normaliza_serie(price_series)
    x = np.arange(len(normalized))

    # Área positiva (acima do ponto médio) — verde
    ax.fill_between(
        x, normalized, midpoint,
        where=(normalized >= midpoint),
        facecolor=positive_color, alpha=fill_alpha, interpolate=True,
    )

    # Área negativa (abaixo do ponto médio) — vermelha
    ax.fill_between(
        x, normalized, midpoint,
        where=(normalized < midpoint),
        facecolor=negative_color, alpha=fill_alpha, interpolate=True,
    )

    # Linha segmentada — a cor acompanha o preenchimento
    for i in range(len(x) - 1):
        color = positive_color if normalized[i] >= midpoint else negative_color
        ax.plot(x[i : i + 2], normalized[i : i + 2], color=color, linewidth=line_width)

    ax.set_ylim(*SPARKLINE_YLIM)


# ---------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------


def monta_painel(
    itens: list[ItemDaGrade],
    referencia: pd.DataFrame,
    intraday: dict[str, pd.Series],
    save_path: Path | None = None,
    figsize: tuple = MONITOR_FIGSIZE,
    grid: tuple[int, int] = MONITOR_GRID,
    allowed_root: Path | None = None,
    asof: datetime | None = None,
    cabecalhos: list[str] | None = None,
    selo_fechado: Path | None = None,
) -> tuple[Figure, dict[str, dict]]:
    """Monta o painel de monitoramento e relata, por ticker, o que cada tile mostra.

    Retorna ``(figure, metrics)``. O dict de métricas é indexado por ticker e
    guarda exatamente os números que o tile renderizou — inclusive a variação
    recalculada a partir da série intradiária, que NÃO é o ``chg_net_1d`` de
    ``referencia`` sempre que barras chegaram. Um chamador que também narra
    esses movimentos em texto precisa lê-los daqui; derivá-los de novo a
    partir dos campos de referência deixaria a imagem e o texto discordarem
    sobre a direção na mesma manhã.

    ``grid`` é (linhas, colunas) e precisa comportar todo item. Tiles além da
    lista de itens simplesmente não são desenhados, então uma grade maior que
    a lista deixa espaços em branco.

    ``cabecalhos`` rotula cada coluna da grade — uma string por coluna — para
    painéis cujas colunas significam algo (uma categoria por coluna). Espaço
    é reservado no topo só quando há cabeçalhos, então painéis sem eles mantêm
    seu espaçamento atual exatamente como está.

    Grava um PNG só quando ``save_path`` é informado, e só dentro de
    ``allowed_root``, que é obrigatório.
    """
    nrows, ncols = grid
    if len(itens) > nrows * ncols:
        raise ValueError(
            f"Grid {nrows}x{ncols} comporta {nrows * ncols} tiles, "
            f"mas foram passados {len(itens)} tickers."
        )
    if cabecalhos and len(cabecalhos) != ncols:
        raise ValueError(
            f"cabecalhos tem {len(cabecalhos)} entradas, "
            f"mas a grade tem {ncols} colunas."
        )
    # ``allowed_root`` só é dispensável enquanto nada é gravado: ``grava_figura``
    # o exige. Cobrar aqui, antes de desenhar, troca um ``TypeError`` obscuro de
    # ``Path(None)`` no fim da função por uma mensagem que nomeia o que faltou.
    if save_path is not None and allowed_root is None:
        raise ValueError(
            "save_path foi informado sem allowed_root: gravar exige a raiz "
            "permitida de saída."
        )

    metrics: dict[str, dict] = {}
    # ``asof`` pode vir vazio (chamador que não tem instante de referência); aí
    # o dia é mesmo o de hoje. Resolver uma vez só garante que todos os tiles
    # olhem o mesmo dia, mesmo numa execução que atravesse a meia-noite.
    dia_de_referencia = (asof or datetime.now()).date()
    color_title = CORES["title"]
    color_green = CORES["positive"]
    color_red = CORES["negative"]

    # O selo vem por parâmetro, não de uma raiz de projeto: esta camada
    # desenha, não sabe onde o repositório começa. Carregado antes da figura
    # para que a recusa abaixo não deixe uma figura aberta para trás.
    market_closed_img = None
    if selo_fechado is not None:
        # Selo informado que não existe é erro de configuração, não ausência de
        # selo: o painel sairia com os tiles fechados sem carimbo algum, e nada
        # na execução acusaria. Quem não quer carimbo passa None.
        if not selo_fechado.exists():
            raise FileNotFoundError(
                f"Selo de mercado fechado não encontrado: {selo_fechado}"
            )
        market_closed_img = plt.imread(str(selo_fechado))

    fig = plt.figure(figsize=figsize, facecolor="white")

    for idx, item in enumerate(itens):
        ticker = item.ticker
        display_name = item.rotulo
        asset_type = item.tipo

        ax = fig.add_subplot(nrows, ncols, idx + 1)

        # Dados de referência
        px_last = 0.0
        chg_net, chg_pct = 0.0, 0.0
        if ticker in referencia.index:
            row_data = referencia.loc[ticker]
            px_last = row_data.get("px_last", 0)
            chg_net = row_data.get("chg_net_1d", 0)
            chg_pct = row_data.get("chg_pct_1d", 0)

        # Série de preço
        price_series = intraday.get(ticker, pd.Series())

        # O calendário de bolsa é autoritativo: se o mercado está oficialmente
        # fechado por feriado, força o tile de "mercado fechado" mesmo quando
        # algumas barras avulsas chegam (ex.: USGG10YR continua marcando por
        # conta do pregão overnight de Londres/Ásia num feriado da SIFMA). Só
        # desenha o sparkline em dias que não são feriado.
        #
        # O dia consultado é o de ``asof``, não o do relógio da máquina: o
        # rodapé já é carimbado com ``asof``, e uma reexecução sobre outro dia
        # sairia com os feriados de hoje sobre a imagem daquele dia.
        holiday = e_feriado_de_mercado(ticker, dia_de_referencia)
        has_chart = (
            not holiday
            and not price_series.empty
            and len(price_series) >= 2
        )

        # Num dia com gráfico, deriva a variação da série intradiária, que já
        # vem ancorada no fechamento anterior. Num feriado, mantém a variação
        # oficial de 1 dia da referência.
        if has_chart:
            first_price = price_series.iloc[0]
            last_price = price_series.iloc[-1]
            chg_net = last_price - first_price
            chg_pct = (
                ((last_price - first_price) / first_price) * 100
                if first_price != 0
                else 0
            )

        # Formata os valores via tabela de despacho
        formatter = FORMATTERS.get(asset_type, _format_default)
        is_positive, value_str, change_str = formatter(px_last, chg_net, chg_pct)
        text_color = color_green if is_positive else color_red

        # Registra o que este tile de fato mostra, para que o texto sobre o
        # mesmo movimento possa ser gerado a partir dos números renderizados
        # em vez de recalculado.
        metrics[ticker] = {
            "display": display_name,
            "type": asset_type,
            "px_last": px_last,
            "chg_net": chg_net,
            "chg_pct": chg_pct,
            "value_str": value_str,
            "change_str": change_str,
            "is_positive": is_positive,
            "has_chart": has_chart,
            "holiday": holiday,
        }

        # Sparkline em dias com gráfico; caso contrário, a imagem de "mercado
        # fechado" — tanto para uma falta de dado genuína quanto para um
        # feriado (onde ela prevalece sobre qualquer barra avulsa, já que
        # `has_chart` é False em feriados).
        if has_chart:
            desenha_sparkline(
                ax=ax,
                price_series=price_series,
                positive_color=color_green,
                negative_color=color_red,
                line_width=SPARKLINE_LINE_WIDTH,
                fill_alpha=SPARKLINE_FILL_ALPHA,
            )
        elif market_closed_img is not None:
            # O carimbo vai num eixo interno, e não no do tile. `imshow` com
            # aspect="equal" encolhe a caixa do eixo que recebe a imagem, para
            # preservar o formato do PNG — e as três linhas de texto abaixo são
            # posicionadas em coordenadas DESSE eixo (transAxes). Desenhando no
            # próprio tile, o eixo encolhia e arrastava a variação para o meio do
            # carimbo em vez do meio da coluna: na mesma grade, o tile fechado
            # saía com o texto desalinhado do tile aberto ao lado.
            #
            # Com o eixo interno o tile mantém a largura inteira, o texto fica
            # ancorado na coluna, e quem encolhe é o interno — que o matplotlib
            # centraliza por padrão, que é onde o carimbo deve ficar.
            selo = ax.inset_axes([0.0, 0.0, 1.0, 1.0])
            selo.imshow(market_closed_img, aspect="equal")
            # Ancoragem explícita: ao encolher para o formato do PNG, o eixo
            # interno precisa sobrar dos dois lados, e não só à direita.
            selo.set_anchor("C")
            selo.axis("off")

        ax.axis("off")

        # Nome do ativo (topo)
        ax.text(
            0, 1.15, display_name, transform=ax.transAxes,
            fontsize=FONTES["monitor_name"], fontweight="bold",
            color=color_title, va="bottom", ha="left",
        )

        # Valor e variação
        ax.text(
            0, 1.0, value_str, transform=ax.transAxes,
            fontsize=FONTES["monitor_value"], color=text_color,
            va="bottom", ha="left",
        )
        ax.text(
            0.5, 1.0, change_str, transform=ax.transAxes,
            fontsize=FONTES["monitor_change"], color=text_color,
            va="bottom", ha="left",
        )

    # Rodapé
    fig.text(
        0.02, 0.02, "OBS: Gráficos intraday.",
        fontsize=FONTES["monitor_obs"], color="black",
        ha="left", va="bottom",
    )
    # O carimbo precisa ser o momento de referência que o chamador está
    # trabalhando, não o relógio da máquina: um chamador que também escreve
    # texto com o cabeçalho "Referência: 07:35" do contrário entregaria uma
    # imagem carimbada com a hora em que ela foi de fato renderizada.
    timestamp = (asof or datetime.now()).strftime("Atualizado em %d/%m/%y - %H:%M")
    fig.text(
        0.98, 0.02, timestamp,
        fontsize=FONTES["monitor_obs"], color=color_red,
        ha="right", va="bottom",
    )

    # Os cabeçalhos precisam de espaço vertical acima dos nomes de ativo da
    # primeira linha, que já ficam acima dos seus eixos. Reserva esse espaço
    # só quando há cabeçalhos, então painéis sem eles mantêm seu espaçamento
    # existente intocado.
    topo = 0.93 if cabecalhos else 0.97
    plt.tight_layout(rect=[0, 0.03, 1, topo])
    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    if cabecalhos:
        # Centraliza cada cabeçalho sobre sua coluna, a partir da posição já
        # diagramada dos eixos da primeira linha. Ler a geometria de volta é
        # melhor que fixar deslocamentos, que iriam variar com o tamanho da
        # figura e o número de colunas.
        for coluna, titulo in enumerate(cabecalhos):
            if coluna >= len(fig.axes):
                break
            caixa = fig.axes[coluna].get_position()
            fig.text(
                (caixa.x0 + caixa.x1) / 2, 0.965, titulo,
                fontsize=FONTES["monitor_column_header"], fontweight="bold",
                color=color_title, ha="center", va="center",
            )

    if save_path is not None:
        grava_figura(fig, save_path, allowed_root=allowed_root)

    return fig, metrics
