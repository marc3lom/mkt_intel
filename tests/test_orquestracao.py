"""O caminho de coleta produz os mesmos quatro arquivos, com o mesmo conteúdo.

Os demais testes cobrem módulos. A orquestração — que ordem, que argumento, que
arquivo — não é exercitada por nenhum, e é justamente ela que a extração do
`plantao.py` move. Este teste é a rede: verde contra o `cli.main()` de hoje e
verde contra o núcleo extraído depois.
"""

from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

from comentario_matinal.config import TZ_BR, carrega_config

# Onde os coletores estão ligados. ``from … import`` liga o nome no módulo que
# importa, então é lá que o monkeypatch precisa agir — não no módulo de origem.
# A Tarefa 2 muda esta linha, e só ela.
MODULO = "comentario_matinal.cli"

MARCA = "20260817"


def _referencia(cfg) -> pd.DataFrame:
    tickers = [a.ticker for a in cfg.ativos]
    return pd.DataFrame(
        {
            "px_last": [100.0 + i for i in range(len(tickers))],
            "chg_net_1d": [0.5] * len(tickers),
            "chg_pct_1d": [0.5] * len(tickers),
        },
        index=tickers,
    )


def _intraday(cfg) -> dict[str, pd.Series]:
    """Dois ativos com barras, o resto sem — exercita o selo de mercado fechado."""
    tickers = [a.ticker for a in cfg.ativos]
    return {t: pd.Series([100.0, 100.5, 101.0]) for t in tickers[:2]}


def _eco() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "United States", "DATA": "2026-08-17", "HORÁRIO": "09:30",
         "EVENTO": "Empire Manufacturing", "PERÍODO": "Aug",
         "ESTIMATIVA": "10.0", "ATUAL": "-", "ANTERIOR": "15.6", "REVISADO": "-"},
        {"PAÍS": "China", "DATA": "2026-08-17", "HORÁRIO": "04:00",
         "EVENTO": "Retail Sales YoY", "PERÍODO": "Jul",
         "ESTIMATIVA": "1.5", "ATUAL": "0.6", "ANTERIOR": "1.0", "REVISADO": "-"},
    ])


def _bancos() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "Eurozone Aggregate", "DATA": "2026-08-17", "HORÁRIO": "06:30",
         "EVENTO": "ECB's Lane Speaks in Dublin"},
    ])


@pytest.fixture
def bloomberg_falsa(monkeypatch):
    cfg = carrega_config()
    monkeypatch.setattr(f"{MODULO}.coleta_referencia",
                        lambda ativos: (_referencia(cfg), []))
    monkeypatch.setattr(f"{MODULO}.coleta_intraday",
                        lambda ativos, asof, ref: _intraday(cfg))
    monkeypatch.setattr(f"{MODULO}.coleta_calendario",
                        lambda: (_eco(), _bancos()))
    return cfg


def test_coleta_produz_os_quatro_arquivos(bloomberg_falsa, monkeypatch, tmp_path):
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert (tmp_path / f"painel_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"calendario_{MARCA}.png").stat().st_size > 10_000

    md = (tmp_path / f"calendario_{MARCA}.md").read_text(encoding="utf-8")
    assert "CALENDÁRIO ECONÔMICO" in md
    assert "Empire Manufacturing" in md
    assert "ECB's Lane Speaks in Dublin" in md


def test_bloco_direcional_lista_todo_ativo_do_painel(bloomberg_falsa, monkeypatch,
                                                     tmp_path):
    """O bloco é o que as três etapas de IA leem como estado do mercado.

    Um ativo que suma dele some da triagem, da redação e da revisão de uma vez —
    e sem erro, porque nada afirma que ele deveria estar lá.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    texto = (tmp_path / f"painel_{MARCA}.txt").read_text(encoding="utf-8")
    assert "PAINEL DIRECIONAL" in texto
    assert "17/08/2026 07:40" in texto
    for ativo in bloomberg_falsa.ativos:
        assert ativo.rotulo in texto, f"{ativo.rotulo} sumiu do bloco direcional"
