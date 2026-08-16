"""Testes que não exigem terminal Bloomberg.

Cobrem as três regras que, se regredirem, produzem exatamente os erros que o
comando existe para impedir: dado não divulgado tratado como fato, direção de
câmbio invertida, e desaparecimento silencioso do bloco de calendário.
"""

from datetime import date, datetime

import pandas as pd
import pytest

from comentario_matinal.calendario import Evento, eventos_do_dia
from comentario_matinal.config import TZ_BR, carrega_config
from comentario_matinal.dados import _com_variacao_confiavel, ancora_fechamento_anterior
from comentario_matinal.etapas import Insumos
from comentario_matinal.texto import _direcao, monta_texto

ASOF = datetime(2026, 8, 14, 7, 40, tzinfo=TZ_BR)


# --- configuração -----------------------------------------------------------


def test_config_real_carrega_e_cabe_na_grade():
    cfg = carrega_config()
    linhas, colunas = cfg.grade
    assert len(cfg.ativos) <= linhas * colunas
    assert len({a.ticker for a in cfg.ativos}) == len(cfg.ativos)


def test_grade_e_montada_por_coluna_e_lida_por_linha():
    """O painel.toml agrupa por coluna; o matplotlib numera por linha.

    Sem a transposição, a primeira linha da imagem sairia com os quatro primeiros
    ativos do arquivo — todos yields — em vez de um de cada categoria.
    """
    cfg = carrega_config()
    linhas, colunas = cfg.grade
    ordem = cfg.ordem_da_grade()

    assert len(ordem) == len(cfg.ativos)
    assert {a.ticker for a in ordem} == {a.ticker for a in cfg.ativos}

    # A primeira linha da grade tem de trazer o topo de cada coluna do arquivo.
    topos = [next(a for a in cfg.ativos if a.coluna == c)
             for c in range(1, colunas + 1)]
    assert ordem[:colunas] == topos

    # E cada coluna da grade tem de conter só ativos daquela coluna do arquivo.
    for c in range(colunas):
        da_coluna = ordem[c::colunas]
        esperado = [a for a in cfg.ativos if a.coluna == c + 1]
        assert da_coluna == esperado


def test_ha_um_cabecalho_por_coluna_da_grade():
    cfg = carrega_config()
    _, colunas = cfg.grade
    assert len(cfg.titulos_colunas) == colunas


def test_grade_recusa_buraco_no_meio():
    """Coluna curta antes de uma cheia deslocaria todos os ativos seguintes."""
    from dataclasses import replace

    cfg = carrega_config()
    linhas, colunas = cfg.grade
    # Esvazia a primeira coluna até ficar mais curta que a última.
    primeira = [a for a in cfg.ativos if a.coluna == 1]
    encurtada = replace(cfg, ativos=[a for a in cfg.ativos
                                     if a.coluna != 1 or a in primeira[:1]])
    with pytest.raises(RuntimeError, match="célula vazia no meio"):
        encurtada.ordem_da_grade()


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


# --- markdown do comentário -------------------------------------------------


def test_enfase_vira_italico_e_forte_vira_negrito():
    """O guia exige itálico em termo em inglês sem equivalente limpo."""
    from comentario_matinal.documento import trechos_de

    t = trechos_de("o *term premium* concentra o ajuste")
    assert [(x.texto, x.italico) for x in t] == [
        ("o ", False), ("term premium", True), (" concentra o ajuste", False),
    ]

    assert trechos_de("o _outlook_ de oferta")[1].italico is True
    forte = trechos_de("o **Nikkei** encerrou")[1]
    assert forte.negrito is True and forte.italico is False


def test_asterisco_duplo_nao_e_lido_como_dois_simples():
    from comentario_matinal.documento import trechos_de

    t = trechos_de("**forte** e *fraco*")
    assert [(x.texto, x.negrito, x.italico) for x in t] == [
        ("forte", True, False), (" e ", False, False), ("fraco", False, True),
    ]


def test_marcadores_juntam_linhas_quebradas(tmp_path):
    """Marcador quebrado por largura de coluna é um marcador só."""
    from comentario_matinal.documento import le_marcadores

    md = tmp_path / "c.md"
    md.write_text(
        "# Título\n\n"
        "- Primeira linha do marcador\n"
        "  continuação do mesmo marcador\n\n"
        "- Segundo marcador\n\n"
        "Atenciosamente,\n",
        encoding="utf-8",
    )
    marcadores, ignoradas = le_marcadores(md)

    assert len(marcadores) == 2
    assert "".join(t.texto for t in marcadores[0]) == (
        "Primeira linha do marcador continuação do mesmo marcador"
    )
    # Nada some em silêncio: título e fecho voltam como ignorados.
    assert any(i.startswith("# Título") for i in ignoradas)
    assert any(i.startswith("Atenciosamente") for i in ignoradas)


# --- encadeamento entre as etapas -------------------------------------------


def test_secao_casa_titulo_com_grafia_variavel():
    """O modelo escreve o título de formas diferentes; o encadeamento não pode
    depender de uma grafia exata."""
    from comentario_matinal.etapas import secao

    for titulo in ("### C) ALERTAS", "## C — Alertas", "#### Alertas"):
        doc = f"# Topo\n\n## A) Temas\n\ntabela\n\n{titulo}\n\nconteúdo\n\n## D) Corte\n\nx"
        assert secao(doc, "alertas") == "conteúdo"


def test_secao_devolve_none_quando_nao_existe():
    from comentario_matinal.etapas import secao

    assert secao("# Topo\n\ntexto", "alertas") is None


def test_comentario_e_o_que_vem_antes_da_auditoria():
    """A redação começa direto nos marcadores: o prompt pede 'sem cabeçalho'.

    Procurar um título '1) COMENTÁRIO' falharia sempre — o que existe é o título
    do bloco de auditoria.
    """
    from comentario_matinal.etapas import texto_do_comentario

    doc = "- Primeiro marcador\n\n- Segundo marcador\n\n## 2) BLOCO DE AUDITORIA\n\ncontagem: 400"
    assert texto_do_comentario(doc) == "- Primeiro marcador\n\n- Segundo marcador"


def test_referencia_do_painel_vem_do_cabecalho():
    """O horário de redação é o do término da coleta, carimbado no painel."""
    from comentario_matinal.etapas import referencia_do_painel

    painel = ("PAINEL DIRECIONAL\n"
              "Referência: 14/08/2026 07:35 de Brasília (06:35 de Nova York)\n")
    r = referencia_do_painel(painel)
    assert (r.day, r.month, r.hour, r.minute) == (14, 8, 7, 35)
    assert referencia_do_painel("sem cabeçalho") is None


# --- fontes do dia ----------------------------------------------------------


def test_arquivo_que_nao_e_pdf_volta_nomeado(tmp_path):
    """O .docx salvo por hábito não chega ao modelo. Sem aviso, isso só
    apareceria como a ausência de um tema na triagem — tarde, e sem causa."""
    from comentario_matinal.fontes import converte

    origem = tmp_path / "fontes"
    origem.mkdir()
    for nome in ("wrap.docx", "print.png", "email.msg"):
        (origem / nome).write_text("x", encoding="utf-8")

    conv = converte(origem, tmp_path / "saida" / "fontes.txt")
    assert conv.aproveitados == 0
    assert conv.ignorados == ["email.msg", "print.png", "wrap.docx"]


def test_arquivo_oculto_nao_vira_aviso(tmp_path):
    """.gitkeep não é fonte que alguém esperava ver no comentário."""
    from comentario_matinal.fontes import converte

    origem = tmp_path / "fontes"
    origem.mkdir()
    (origem / ".gitkeep").write_text("", encoding="utf-8")
    (origem / "subpasta").mkdir()

    assert converte(origem, tmp_path / "saida" / "fontes.txt").ignorados == []


def test_pasta_de_fontes_inexistente_nao_estoura(tmp_path):
    from comentario_matinal.fontes import converte

    conv = converte(tmp_path / "nao-existe", tmp_path / "saida" / "fontes.txt")
    assert (conv.aproveitados, conv.vazios, conv.ignorados) == (0, [], [])


# --- comentário do dia anterior ---------------------------------------------


def _arquivo_falso(raiz, *marcas):
    for marca in marcas:
        destino = raiz / marca[:4] / marca[4:6] / f"{marca}.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(f"- comentário de {marca}\n", encoding="utf-8")
    return raiz


def test_anterior_pega_o_mais_recente_antes_do_plantao(tmp_path):
    """Numa segunda-feira o "dia anterior" é a sexta."""
    from comentario_matinal.etapas import comentario_anterior

    raiz = _arquivo_falso(tmp_path, "20260810", "20260813", "20260814")
    segunda = datetime(2026, 8, 17, 7, 40, tzinfo=TZ_BR)

    caminho, data = comentario_anterior(raiz, segunda)
    assert caminho.name == "20260814.md"
    assert (data.day, data.month) == (14, 8)


def test_anterior_nao_pega_o_do_proprio_dia_nem_do_futuro(tmp_path):
    """Reprocessar um plantão antigo não pode receber texto escrito depois dele."""
    from comentario_matinal.etapas import comentario_anterior

    raiz = _arquivo_falso(tmp_path, "20260813", "20260814", "20260817")
    caminho, _ = comentario_anterior(raiz, ASOF)   # 14/08
    assert caminho.name == "20260813.md"


def test_anterior_alem_da_janela_nao_e_usado(tmp_path):
    """Um texto de três semanas atrás não é "o do dia anterior".

    As etapas 1 e 3 o recebem sob esse rótulo e comparam o quadro de hoje com o
    que ele descreve; passar um texto velho produziria contradição inventada.
    """
    from comentario_matinal.etapas import comentario_anterior

    raiz = _arquivo_falso(tmp_path, "20260717")
    assert comentario_anterior(raiz, ASOF) is None


def test_anterior_ignora_nome_fora_da_convencao(tmp_path):
    from comentario_matinal.etapas import comentario_anterior

    raiz = _arquivo_falso(tmp_path, "20260813")
    (raiz / "2026" / "08" / "rascunho.md").write_text("x", encoding="utf-8")
    caminho, _ = comentario_anterior(raiz, ASOF)
    assert caminho.name == "20260813.md"


def test_anterior_sem_pasta_nao_estoura(tmp_path):
    from comentario_matinal.etapas import comentario_anterior

    assert comentario_anterior(tmp_path / "nao-existe", ASOF) is None


def test_anterior_carimba_a_data_dentro_do_corpo(tmp_path):
    """O rótulo da entrada é fixo — os prompts casam por ele. A data vai no corpo."""
    from comentario_matinal.etapas import com_data, mensagem_triagem

    raiz = _arquivo_falso(tmp_path, "20260813")
    texto = com_data((raiz / "2026" / "08" / "20260813.md").read_text("utf-8"),
                     date(2026, 8, 13))
    assert texto.startswith("(enviado em 13/08/2026)")

    ins = Insumos(guia="g", fontes="f", painel="p", calendario="c", asof=ASOF,
                  anterior=texto)
    mensagem = mensagem_triagem("prompt", ins, web=False)
    assert "**[COMENTÁRIO DO DIA ANTERIOR]**" in mensagem
    assert "(enviado em 13/08/2026)" in mensagem


def test_sem_anterior_a_entrada_diz_que_nao_veio(tmp_path):
    """"(não fornecido)" precisa aparecer: a etapa tem de saber que a checagem
    de ineditismo ficou sem base, em vez de silenciar."""
    from comentario_matinal.etapas import mensagem_triagem

    ins = Insumos(guia="g", fontes="f", painel="p", calendario="c", asof=ASOF)
    mensagem = mensagem_triagem("prompt", ins, web=False)
    assert "**[COMENTÁRIO DO DIA ANTERIOR]**\n\n(não fornecido)" in mensagem


# --- o bloco que vira o documento enviado -----------------------------------


def test_comentario_revisado_aceita_bloco_bem_formado():
    from comentario_matinal.etapas import comentario_revisado

    doc = ("## 3) TEXTO REVISADO\n\n```markdown\n"
           "- Um\n- Dois\n- Três\n- Quatro\n```\n")
    assert comentario_revisado(doc) == "- Um\n\n- Dois\n\n- Três\n\n- Quatro\n"


@pytest.mark.parametrize("doc,trecho", [
    ("## 3) TEXTO REVISADO\n\nsem bloco algum", "não trouxe bloco de código"),
    ("## 3) TEXTO REVISADO\n\n```\n\n```", "vazio"),
    ("## 3) TEXTO REVISADO\n\n```\n# Título\n- Um\n```", "não são marcadores"),
])
def test_comentario_revisado_falha_alto_em_formato_inesperado(doc, trecho):
    """Único ponto em que a saída do modelo entra direto no documento que vai à
    diretoria: formato inesperado interrompe, não grava."""
    from comentario_matinal.etapas import FormatoInesperado, comentario_revisado

    with pytest.raises(FormatoInesperado, match=trecho):
        comentario_revisado(doc)


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
