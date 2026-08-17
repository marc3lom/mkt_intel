"""O painel entregue à mesa continua idêntico?

Os demais testes de renderização verificam que sai uma figura e que o arquivo
é gravado. Nenhum olha a imagem. Como a saída desta camada é o que chega ao
e-mail, estes testes comparam o desenho com uma referência versionada — é o que
pega mudança silenciosa numa renomeação de mil e trezentas linhas.

São duas referências: uma grade pequena de ativos inventados, que isola a
renderização de um tile, e o painel de produção inteiro, montado a partir do
``config/painel.toml`` real.
"""

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.testing.compare import compare_images

REFERENCIA = Path(__file__).parent / "referencia" / "painel.png"
REFERENCIA_COMPLETA = Path(__file__).parent / "referencia" / "painel_completo.png"

# O painel carimba o horário. Sem asof fixo a imagem muda a cada execução e a
# comparação nunca fecha.
ASOF = datetime(2026, 8, 17, 7, 54)

TICKERS = ["AA Index", "BB Index", "CC Curncy", "DD Comdty"]


def _itens():
    from comentario_matinal.render.ativos import ItemDaGrade

    return [
        ItemDaGrade("AA Index", "aa", "Taxa 10a", "rate"),
        ItemDaGrade("BB Index", "bb", "Bolsa Fut", "equity"),
        ItemDaGrade("CC Curncy", "cc", "Moeda", "fx"),
        ItemDaGrade("DD Comdty", "dd", "Petróleo", "commodity"),
    ]


def _referencia() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "px_last": [4.250, 5300.0, 5.4321, 88.75],
            "chg_net_1d": [0.035, 42.0, -0.0123, 1.20],
            "chg_pct_1d": [0.83, 0.80, -0.23, 1.37],
        },
        index=TICKERS,
    )


def _intraday() -> dict[str, pd.Series]:
    """Dois ativos com barras, dois sem.

    Os sem barras exercitam o selo de mercado fechado, que carrega uma imagem
    de disco — o item mais fácil de esquecer na mudança de lugar, e o que não
    quebra teste algum quando some.
    """
    passo = np.linspace(0.0, 1.0, 40)
    return {
        "AA Index": pd.Series(4.20 + 0.05 * passo),
        "BB Index": pd.Series(5260.0 + 40.0 * passo),
    }


def _desenha(destino: Path):
    from comentario_matinal.config import MERCADO_FECHADO
    from comentario_matinal.render.painel import monta_painel

    fig, _ = monta_painel(
        _itens(),
        _referencia(),
        _intraday(),
        save_path=destino,
        allowed_root=destino.parent,
        grid=(1, 4),
        asof=ASOF,
        cabecalhos=["Taxas", "Bolsas", "Moedas", "Commodities"],
        selo_fechado=MERCADO_FECHADO,
    )
    plt.close(fig)
    return destino


def test_painel_bate_com_a_referencia(tmp_path):
    saida = _desenha(tmp_path / "painel.png")

    assert REFERENCIA.exists(), (
        f"Referência ausente. Gerar uma vez com:\n"
        f'  uv run python -c "'
        f"import sys; sys.path.insert(0,'tests'); "
        f"from test_referencia import _desenha, REFERENCIA; "
        f"REFERENCIA.parent.mkdir(exist_ok=True); _desenha(REFERENCIA)\""
    )

    # tol em unidades de RMS por pixel. O backend Agg é determinístico — duas
    # renderizações do mesmo asof dão RMS 0, sem ruído de antialiasing a
    # tolerar. Um minuto a mais no carimbo já produz RMS ~0.72 (poucos
    # pixels, no canto do horário), então 1.0 deixaria passar exatamente a
    # mudança que este teste existe para pegar; 0.1 fecha essa margem.
    diferenca = compare_images(str(REFERENCIA), str(saida), tol=0.1)
    assert diferenca is None, diferenca


# ---------------------------------------------------------------------------
# O painel de produção — a grade inteira, do painel.toml
# ---------------------------------------------------------------------------

# O teste acima desenha quatro ativos inventados numa grade 1x4. O que sai por
# e-mail é outra coisa: cinco linhas por quatro colunas, os vinte ativos do
# painel.toml, atravessando `carrega_config` e `ordem_da_grade` — que transpõe a
# ordem por coluna do arquivo para a ordem por linha em que o matplotlib numera
# os subplots. Nada disso está coberto pela referência pequena: uma troca na
# transposição, um cabeçalho fora de lugar ou um formatador trocado sairiam com
# a imagem pequena intacta.

# Segunda-feira comum, sem feriado em nenhum dos calendários mapeados. Além de
# fixar o carimbo do rodapé, é dela que sai a data da consulta de feriado — é o
# que mantém a imagem igual em qualquer dia em que o teste rode.
ASOF_COMPLETO = datetime(2026, 8, 17, 7, 40)

# Índices (na ordem de desenho) dos ativos deixados sem barras intradiárias, para
# que a referência cubra também o selo de mercado fechado — o elemento que
# depende de um arquivo em disco e some sem quebrar nada.
SEM_BARRAS = {2, 9}

# Valor de partida por tipo de ativo, para que cada formatador apareça na imagem
# com número da ordem de grandeza que ele espera.
BASE_POR_TIPO = {
    "rate": 4.0,
    "equity": 5000.0,
    "fx": 1.25,
    "commodity": 80.0,
    "vol": 15.0,
}


def _itens_reais():
    from comentario_matinal.config import carrega_config

    cfg = carrega_config()
    return cfg, cfg.para_itens_da_grade(cfg.ordem_da_grade())


def _referencia_real(itens) -> pd.DataFrame:
    """Preços sintéticos e fixos, alternando alta e baixa.

    Não há dado de mercado real aqui — nem poderia haver, nenhum teste toca o
    Bloomberg. O que importa é que os números sejam os mesmos a cada execução e
    que metade suba e metade caia, para que as duas cores apareçam na imagem.
    """
    px, chg_net, chg_pct = [], [], []
    for i, item in enumerate(itens):
        sinal = 1.0 if i % 2 == 0 else -1.0
        base = BASE_POR_TIPO[item.tipo] * (1.0 + i / 50.0)
        variacao = sinal * base * (0.002 + i / 2000.0)
        px.append(base)
        chg_net.append(variacao)
        chg_pct.append(variacao / base * 100.0)
    return pd.DataFrame(
        {"px_last": px, "chg_net_1d": chg_net, "chg_pct_1d": chg_pct},
        index=[item.ticker for item in itens],
    )


def _intraday_real(itens, referencia: pd.DataFrame) -> dict[str, pd.Series]:
    """Uma série ondulada por ativo, menos os de ``SEM_BARRAS``.

    A onda existe para que o sparkline tenha área verde e vermelha ao mesmo
    tempo; sem ela uma reta não exercitaria o preenchimento em dois trechos.
    """
    passo = np.linspace(0.0, 1.0, 40)
    series: dict[str, pd.Series] = {}
    for i, item in enumerate(itens):
        if i in SEM_BARRAS:
            continue
        inicial = referencia.at[item.ticker, "px_last"]
        variacao = referencia.at[item.ticker, "chg_net_1d"]
        onda = np.sin(passo * (4.0 + i % 3) + i)
        series[item.ticker] = pd.Series(
            inicial + variacao * (passo + 0.4 * onda)
        )
    return series


def _desenha_completo(destino: Path):
    from comentario_matinal.config import MERCADO_FECHADO
    from comentario_matinal.render.painel import monta_painel

    cfg, itens = _itens_reais()
    referencia = _referencia_real(itens)
    fig, _ = monta_painel(
        itens,
        referencia,
        _intraday_real(itens, referencia),
        save_path=destino,
        allowed_root=destino.parent,
        grid=cfg.grade,
        asof=ASOF_COMPLETO,
        cabecalhos=cfg.titulos_colunas,
        selo_fechado=MERCADO_FECHADO,
    )
    plt.close(fig)
    return destino


def test_painel_completo_bate_com_a_referencia(tmp_path):
    saida = _desenha_completo(tmp_path / "painel_completo.png")

    assert REFERENCIA_COMPLETA.exists(), (
        f"Referência ausente. Gerar uma vez com:\n"
        f'  uv run python -c "'
        f"import sys; sys.path.insert(0,'tests'); "
        f"from test_referencia import _desenha_completo, REFERENCIA_COMPLETA; "
        f"REFERENCIA_COMPLETA.parent.mkdir(exist_ok=True); "
        f'_desenha_completo(REFERENCIA_COMPLETA)"'
    )

    # Mesma tolerância do teste pequeno, e pelo mesmo motivo: o Agg é
    # determinístico, então o único ruído possível é o que se quer pegar.
    diferenca = compare_images(str(REFERENCIA_COMPLETA), str(saida), tol=0.1)
    assert diferenca is None, diferenca
