"""O painel entregue à mesa continua idêntico?

Os demais testes de renderização verificam que sai uma figura e que o arquivo
é gravado. Nenhum olha a imagem. Como a saída desta camada é o que chega ao
e-mail, este teste compara o desenho com uma referência versionada — é o que
pega mudança silenciosa numa renomeação de mil e trezentas linhas.
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
