"""Testes que não exigem terminal Bloomberg.

Cobrem as três regras que, se regredirem, produzem exatamente os erros que o
comando existe para impedir: dado não divulgado tratado como fato, direção de
câmbio invertida, e desaparecimento silencioso do bloco de calendário.
"""

from datetime import datetime

import pandas as pd
import pytest

from comentario_matinal.calendario import Evento, eventos_do_dia
from comentario_matinal.config import TZ_BR, carrega_config
from comentario_matinal.dados import _com_variacao_confiavel, ancora_fechamento_anterior
from comentario_matinal.texto import _direcao, monta_texto

ASOF = datetime(2026, 8, 14, 7, 40, tzinfo=TZ_BR)


# --- configuração -----------------------------------------------------------


def test_config_real_carrega_e_cabe_na_grade():
    cfg = carrega_config()
    linhas, colunas = cfg.grade
    assert len(cfg.ativos) <= linhas * colunas
    assert len({a.ticker for a in cfg.ativos}) == len(cfg.ativos)


def test_config_traduz_tipos_para_a_camada_de_render():
    cfg = carrega_config()
    validos = {"rate", "equity", "fx", "commodity", "vol"}
    assert {t.type for t in cfg.para_ticker_info()} <= validos


def test_rotulo_de_par_de_cambio_e_inequivoco():
    """USD/JPY sobe quando o iene enfraquece; o rótulo tem de dizer o par.

    Um rótulo "JPY" faria o bloco direcional afirmar "JPY: alta" num dia de iene
    em queda — a direção oposta à do dado.
    """
    cfg = carrega_config()
    rotulos = {a.ticker: a.rotulo for a in cfg.ativos}
    assert rotulos["USDJPY Curncy"] == "USD/JPY"
    assert rotulos["USDCNH Curncy"] == "USD/CNH"


# --- direção ----------------------------------------------------------------


@pytest.mark.parametrize("variacao,limiar,esperado", [
    (0.50, 0.25, "alta"),
    (-0.50, 0.25, "baixa"),
    (0.10, 0.25, "estável"),
    (-0.10, 0.25, "estável"),
    (0.25, 0.25, "alta"),      # no limiar, já é movimento
    (float("nan"), 0.25, "indisponível"),
])
def test_direcao(variacao, limiar, esperado):
    assert _direcao(variacao, limiar) == esperado


# --- sinal do percentual ----------------------------------------------------


def test_percentual_recalculado_tem_o_sinal_da_variacao_liquida():
    """O CHG_PCT_1D do Bloomberg vem invertido em USD/JPY e USD/CNH.

    Valores reais observados em 14/08/2026: USDJPY px 159.18 com variação líquida
    -0.24 chegou ao campo como +0.1507 %. O sinal decide a cor do tile e a palavra
    do texto, então ele é sempre recalculado do fechamento anterior.
    """
    ref = pd.DataFrame(
        {"px_last": [159.18, 6.7424, 1.1583],
         "chg_net_1d": [-0.24, -0.0022, 0.0053],
         "chg_pct_1d": [0.1507, 0.0326, 0.4598]},   # como o Bloomberg entrega
        index=["USDJPY Curncy", "USDCNH Curncy", "EURUSD Curncy"],
    )
    saida = _com_variacao_confiavel(ref)

    assert saida.at["USDJPY Curncy", "chg_pct_1d"] < 0
    assert saida.at["USDCNH Curncy", "chg_pct_1d"] < 0
    assert saida.at["EURUSD Curncy", "chg_pct_1d"] > 0
    for ticker in saida.index:
        net = saida.at[ticker, "chg_net_1d"]
        pct = saida.at[ticker, "chg_pct_1d"]
        assert (net > 0) == (pct > 0), f"sinal divergente em {ticker}"


# --- base de cálculo da variação --------------------------------------------


def test_ancora_faz_a_variacao_ser_a_do_dia_e_nao_a_da_sessao():
    """O caso do Nikkei em 14/08/2026, que expôs o erro.

    O futuro abriu 730 pontos ACIMA do fechamento anterior e encerrou 80 abaixo
    dele. O painel calcula a variação como último menos primeiro ponto da série;
    sem a âncora, "primeiro" é a abertura e a conta devolve -1,18 % — a queda
    dentro do pregão — em vez dos -0,12 % do dia. Em mercado asiático já fechado
    o gap de abertura é a maior parte do movimento, então o erro é grande.
    """
    fechamento_anterior = 68690.0
    barras = pd.Series([69420.0, 69000.0, 68610.0])

    sem_ancora = barras.iloc[-1] - barras.iloc[0]
    assert round(sem_ancora / barras.iloc[0] * 100, 2) == -1.17  # a sessão

    ancorada = ancora_fechamento_anterior(barras, fechamento_anterior)
    com_ancora = ancorada.iloc[-1] - ancorada.iloc[0]
    assert ancorada.iloc[0] == fechamento_anterior
    assert len(ancorada) == len(barras) + 1
    assert round(com_ancora / fechamento_anterior * 100, 2) == -0.12  # o dia


def test_ancora_preserva_o_sinal_quando_o_gap_inverte_a_direcao():
    """Gap de alta seguido de queda leve: o dia sobe, a sessão cai."""
    ancorada = ancora_fechamento_anterior(pd.Series([110.0, 108.0, 105.0]), 100.0)
    assert ancorada.iloc[-1] - ancorada.iloc[0] > 0     # dia: +5
    assert 105.0 - 110.0 < 0                            # sessão: -5


@pytest.mark.parametrize("anterior", [None, float("nan")])
def test_ancora_sem_fechamento_anterior_devolve_a_serie_intacta(anterior):
    barras = pd.Series([1.0, 2.0])
    assert ancora_fechamento_anterior(barras, anterior).equals(barras)


def test_ancora_em_serie_vazia_nao_inventa_ponto():
    vazia = pd.Series(dtype="float64")
    assert ancora_fechamento_anterior(vazia, 100.0).empty


# --- status de divulgação ---------------------------------------------------


def _calendario_falso() -> pd.DataFrame:
    return pd.DataFrame([
        # já saiu às 06h00, antes das 07h40
        {"PAÍS": "Eurozone Aggregate", "DATA": "2026-08-14", "HORÁRIO": "06:00",
         "EVENTO": "GDP SA QoQ", "ATUAL": 0.40},
        # sai às 09h30, DEPOIS da redação — mas com ATUAL preenchido
        {"PAÍS": "United States", "DATA": "2026-08-14", "HORÁRIO": "09:30",
         "EVENTO": "Retail Sales Advance MoM", "ATUAL": -0.60},
        # sem horário informado
        {"PAÍS": "United States", "DATA": "2026-08-14", "HORÁRIO": None,
         "EVENTO": "Sem horário", "ATUAL": 1.0},
        # outro dia
        {"PAÍS": "United Kingdom", "DATA": "2026-08-13", "HORÁRIO": "03:00",
         "EVENTO": "GDP QoQ", "ATUAL": 0.40},
    ])


def test_status_vem_do_horario_e_nao_do_valor_preenchido():
    """O caso que motiva a regra inteira.

    Um índice econômico carrega o print anterior indefinidamente: às 7h40 o campo
    ATUAL do Retail Sales já está preenchido com o número do mês passado. Decidir
    o status por ele marcaria como divulgado um indicador que ainda vai sair.
    """
    eventos = eventos_do_dia(_calendario_falso(), ASOF)
    por_evento = {e.evento: e for e in eventos}

    assert por_evento["GDP SA QoQ"].divulgado is True
    assert por_evento["Retail Sales Advance MoM"].divulgado is False
    assert por_evento["Retail Sales Advance MoM"].status == "AINDA NÃO DIVULGADO"
    assert por_evento["Sem horário"].divulgado is None
    assert "INDETERMINADO" in por_evento["Sem horário"].status
    assert "GDP QoQ" not in por_evento, "release de outro dia não pode entrar"


def test_status_vira_divulgado_quando_o_horario_passa():
    tarde = datetime(2026, 8, 14, 13, 10, tzinfo=TZ_BR)
    eventos = {e.evento: e for e in eventos_do_dia(_calendario_falso(), tarde)}
    assert eventos["Retail Sales Advance MoM"].divulgado is True


def test_calendario_vazio_nao_produz_lista_vazia_silenciosa():
    assert eventos_do_dia(pd.DataFrame(), ASOF) == []


# --- texto ------------------------------------------------------------------


def test_texto_avisa_quando_o_calendario_nao_foi_apurado():
    """Sem aviso, o bloco some e ninguém nota que a checagem deixou de ocorrer."""
    cfg = carrega_config()
    metricas = {
        a.ticker: {"chg_net": 0.05, "chg_pct": 1.0, "has_chart": True}
        for a in cfg.ativos
    }
    texto = monta_texto(cfg, metricas, [], ASOF, [], calendario_vazio=True)
    assert "CONSULTA INDISPONÍVEL" in texto
    assert "DIVULGADO" not in texto.split("CALENDÁRIO ECONÔMICO DO DIA")[1].split("Nota:")[0]


def test_texto_lista_todo_ativo_do_config_uma_vez():
    cfg = carrega_config()
    metricas = {
        a.ticker: {"chg_net": 0.05, "chg_pct": 1.0, "has_chart": True}
        for a in cfg.ativos
    }
    evento = Evento("United States", "CPI", "09h30", None, False)
    texto = monta_texto(cfg, metricas, [evento], ASOF, [], calendario_vazio=False)
    for ativo in cfg.ativos:
        assert f"  {ativo.rotulo}: " in texto, f"{ativo.rotulo} ausente do texto"


def test_ativo_sem_dado_sai_como_indisponivel():
    cfg = carrega_config()
    alvo = cfg.ativos[0]
    metricas = {
        a.ticker: {"chg_net": 0.05, "chg_pct": 1.0, "has_chart": True}
        for a in cfg.ativos
    }
    texto = monta_texto(cfg, metricas, [], ASOF, [alvo.ticker], calendario_vazio=True)
    assert f"  {alvo.rotulo}: indisponível" in texto
