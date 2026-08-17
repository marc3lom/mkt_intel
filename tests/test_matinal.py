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
    """USD/JPY sobe quando o iene enfraquece; o rótulo do TEXTO tem de dizer o par.

    Um rótulo "JPY" faria o bloco direcional afirmar "JPY: alta" num dia de iene
    em queda — a direção oposta à do dado. Na grade o rótulo curto é aceitável e
    é a convenção de mesa: o tile traz o nível ao lado, e 159,20 só se lê como
    USD/JPY. Os dois campos são separados justamente para isso, e este teste
    existe para que encurtar o da grade não arraste o do texto junto.
    """
    cfg = carrega_config()
    por_ticker = {a.ticker: a for a in cfg.ativos}
    assert por_ticker["USDJPY Curncy"].rotulo == "USD/JPY"
    assert por_ticker["USDCNH Curncy"].rotulo == "USD/CNH"
    assert por_ticker["USDJPY Curncy"].rotulo_grade == "JPY"
    assert por_ticker["USDCNH Curncy"].rotulo_grade == "CNH"


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


REDACAO_REAL = """- Primeiro marcador do comentário.

- Segundo marcador do comentário.

---

**BLOCO DE AUDITORIA** (não integra o e-mail)

**Contagem de palavras**: total 450.

**Ressalvas**
- uma ressalva que começa com marcador, dentro da auditoria
"""


def test_comentario_e_auditoria_com_titulo_em_negrito():
    """O caso que a estreia expôs.

    O prompt pede "### 2) BLOCO DE AUDITORIA"; o modelo entregou o título em
    negrito. O varredor só reconhecia títulos `#`, então nem o fim do comentário
    nem a auditoria eram localizados, e o documento inteiro ia nos dois campos.
    Amarrar o encadeamento à obediência de formato é o que se está desfazendo.
    """
    from comentario_matinal.etapas import partes_da_redacao

    comentario, auditoria = partes_da_redacao(REDACAO_REAL)
    assert comentario == ("- Primeiro marcador do comentário.\n\n"
                          "- Segundo marcador do comentário.")
    assert auditoria.startswith("**BLOCO DE AUDITORIA**")
    assert "Contagem de palavras" in auditoria
    # A ressalva em marcador está DEPOIS do corte: não volta para o comentário.
    assert "uma ressalva que começa com marcador" in auditoria
    assert "ressalva" not in comentario


@pytest.mark.parametrize("separador", [
    "## 2) BLOCO DE AUDITORIA",
    "### BLOCO DE AUDITORIA",
    "---",
    "___",
    "**BLOCO DE AUDITORIA**",
])
def test_o_corte_funciona_com_qualquer_marcacao_de_fim(separador):
    """Título, regra horizontal ou negrito — o comentário termina em todos."""
    from comentario_matinal.etapas import partes_da_redacao

    doc = f"- Um marcador.\n\n- Outro marcador.\n\n{separador}\n\nauditoria aqui\n"
    comentario, auditoria = partes_da_redacao(doc)
    assert comentario == "- Um marcador.\n\n- Outro marcador."
    assert "auditoria aqui" in auditoria


def test_preambulo_antes_dos_marcadores_nao_entra_no_comentario():
    """A triagem abriu com uma ressalva de janela; a redação pode fazer o mesmo."""
    from comentario_matinal.etapas import partes_da_redacao

    doc = "**RESSALVA:** janela atípica.\n\n- Um marcador.\n\n**AUDITORIA**\n\nx\n"
    comentario, _ = partes_da_redacao(doc)
    assert comentario == "- Um marcador."


def test_referencia_do_painel_vem_do_cabecalho():
    """O horário de redação é o do término da coleta, carimbado no painel."""
    from comentario_matinal.etapas import referencia_do_painel

    painel = ("PAINEL DIRECIONAL\n"
              "Referência: 14/08/2026 07:35 de Brasília (06:35 de Nova York)\n")
    r = referencia_do_painel(painel)
    assert (r.day, r.month, r.hour, r.minute) == (14, 8, 7, 35)
    assert referencia_do_painel("sem cabeçalho") is None


# --- arquivamento do enviado ------------------------------------------------


def _docx_com(tmp_path, *marcadores):
    """Um .docx mínimo com os marcadores no estilo do template."""
    from docx import Document

    d = Document()
    d.add_paragraph("Comentário Matinal – Mesa de Investimentos")
    for m in marcadores:
        d.add_paragraph(m, style="List Paragraph")
    d.add_paragraph("Atenciosamente,")
    caminho = tmp_path / "comentario.docx"
    d.save(str(caminho))
    return caminho


def test_marcadores_iguais_nao_divergem(tmp_path):
    """Ênfase não conta: *termo* no Markdown vira termo no Word."""
    from comentario_matinal.enviado import divergencias

    md = tmp_path / "c.md"
    md.write_text("- O *term premium* avança.\n\n- O dólar cede.\n", encoding="utf-8")
    docx = _docx_com(tmp_path, "O term premium avança.", "O dólar cede.")

    assert divergencias(docx, md) == []


def test_texto_corrigido_no_word_e_apontado(tmp_path):
    """O caso que motiva a comparação: o autor corrige no Word e o .md fica para
    trás — e é o .md que vira o "dia anterior" da triagem seguinte."""
    from comentario_matinal.enviado import divergencias

    md = tmp_path / "c.md"
    md.write_text("- A volatilidade implícita cede.\n\n- O dólar cede.\n",
                  encoding="utf-8")
    docx = _docx_com(tmp_path, "A volatilidade implícita recua.", "O dólar cede.")

    div = divergencias(docx, md)
    assert len(div) == 1
    assert div[0].indice == 1
    assert "cede" in div[0].no_md and "recua" in div[0].no_docx


def test_contagem_diferente_de_marcadores_e_divergencia(tmp_path):
    """Marcador apagado no Word não pode passar por coincidência de prefixo."""
    from comentario_matinal.enviado import divergencias

    md = tmp_path / "c.md"
    md.write_text("- Um.\n\n- Dois.\n\n- Três.\n", encoding="utf-8")
    docx = _docx_com(tmp_path, "Um.", "Dois.")

    div = divergencias(docx, md)
    assert len(div) == 1
    assert div[0].indice == 3
    assert div[0].no_docx == ""


def test_espaco_e_quebra_nao_contam_como_divergencia(tmp_path):
    from comentario_matinal.enviado import divergencias

    md = tmp_path / "c.md"
    md.write_text("- Uma frase\n  quebrada por largura.\n", encoding="utf-8")
    docx = _docx_com(tmp_path, "Uma frase  quebrada   por largura.")

    assert divergencias(docx, md) == []


def test_recorte_mostra_a_palavra_que_sumiu():
    from comentario_matinal.enviado import Divergencia, recortes

    d = Divergencia(1, "a maioria dos mercados de swap embute altas",
                       "a maioria dos mercados de embute altas")

    (no_md, no_docx), = recortes(d, contexto=2)
    assert "swap" in no_md
    assert "swap" not in no_docx
    assert "maioria" not in no_md, "contexto de 2 palavras não deve alcançar"


def test_recorte_alcanca_diferenca_no_fim_do_marcador():
    """O defeito da primeira rodada em produção: o aviso cortava o marcador nos
    primeiros caracteres, e uma diferença lá no fim saía invisível — as duas
    linhas apareciam idênticas na tela."""
    from comentario_matinal.enviado import Divergencia, recortes

    comum = " ".join(f"palavra{i}" for i in range(120))
    d = Divergencia(1, f"{comum} encobertos", f"{comum} rastreados")

    (no_md, no_docx), = recortes(d)
    assert "encobertos" in no_md
    assert "rastreados" in no_docx
    assert "palavra0" not in no_md, "o recorte deve ir à diferença, não ao início"


def test_recorte_junta_diferencas_proximas_e_separa_as_distantes():
    from comentario_matinal.enviado import Divergencia, recortes

    meio = " ".join(f"palavra{i}" for i in range(60))
    d = Divergencia(1, f"alfa {meio} beta", f"gama {meio} delta")

    assert len(recortes(d)) == 2


def test_recorte_de_marcador_ausente_nao_estoura():
    from comentario_matinal.enviado import Divergencia, recortes

    d = Divergencia(3, "O dólar cede.", "")

    (no_md, no_docx), = recortes(d)
    assert "dólar" in no_md
    assert no_docx == ""


def test_relatorio_aponta_o_marcador_e_o_trecho():
    from comentario_matinal.enviado import Divergencia, relatorio

    d = Divergencia(4, "no fim de semana, que custou", "no fim semana, que custou")

    linhas = "\n".join(relatorio([d]))
    assert "M4" in linhas
    assert "de semana" in linhas


def test_relatorio_diz_ausente_quando_o_marcador_sumiu():
    from comentario_matinal.enviado import Divergencia, relatorio

    linhas = "\n".join(relatorio([Divergencia(5, "Permanecem sob vigília.", "")]))
    assert "(ausente)" in linhas


def test_arquiva_nos_dois_destinos(tmp_path):
    from comentario_matinal.enviado import arquiva

    saida, arq = tmp_path / "saida", tmp_path / "arquivo"
    saida.mkdir()
    (saida / "comentario_20260817.md").write_text("- Um.\n", encoding="utf-8")
    (saida / "comentario_20260817.docx").write_bytes(b"PK-falso")

    destinos = arquiva(saida, arq, "20260817")

    assert (arq / "2026" / "08" / "20260817.md").read_text(encoding="utf-8") == "- Um.\n"
    assert (arq / "2026" / "08" / "comentario_20260817.docx").exists()
    assert len(destinos) == 2


def test_destino_existente_nao_e_sobrescrito(tmp_path):
    """Rearquivar não pode apagar em silêncio o comentário de um dia já enviado."""
    from comentario_matinal.enviado import DestinoOcupado, arquiva

    saida, arq = tmp_path / "saida", tmp_path / "arquivo"
    saida.mkdir()
    (saida / "comentario_20260817.md").write_text("- Novo.\n", encoding="utf-8")
    antigo = arq / "2026" / "08" / "20260817.md"
    antigo.parent.mkdir(parents=True)
    antigo.write_text("- Original.\n", encoding="utf-8")

    with pytest.raises(DestinoOcupado, match="20260817.md"):
        arquiva(saida, arq, "20260817")
    assert antigo.read_text(encoding="utf-8") == "- Original.\n"


def test_docx_ausente_arquiva_so_o_texto(tmp_path):
    """O .md é o que importa; sem o .docx o arquivamento segue, com aviso."""
    from comentario_matinal.enviado import arquiva

    saida, arq = tmp_path / "saida", tmp_path / "arquivo"
    saida.mkdir()
    (saida / "comentario_20260817.md").write_text("- Um.\n", encoding="utf-8")

    destinos = arquiva(saida, arq, "20260817")
    assert len(destinos) == 1
    assert destinos[0].name == "20260817.md"


def test_limpeza_apaga_conteudo_e_preserva_as_pastas(tmp_path):
    from comentario_matinal.enviado import limpa

    fontes, saida = tmp_path / "fontes", tmp_path / "saida"
    for d in (fontes, saida):
        d.mkdir()
        (d / "algo.txt").write_text("x", encoding="utf-8")
    (saida / "sub").mkdir()

    n = limpa([fontes, saida])

    assert fontes.is_dir() and saida.is_dir()
    assert list(fontes.iterdir()) == [] and list(saida.iterdir()) == []
    assert n == 3


# --- janela do plantão ------------------------------------------------------


@pytest.mark.parametrize("hora,minuto,dentro", [
    (6, 59, False),
    (7, 0, True),      # abertura entra
    (7, 40, True),
    (8, 59, True),
    (9, 0, True),      # fechamento entra
    (9, 1, False),
    (14, 20, False),   # o horário dos testes de mesa
    (0, 0, False),
])
def test_bordas_da_janela(hora, minuto, dentro):
    from comentario_matinal.janela import na_janela

    momento = datetime(2026, 8, 17, hora, minuto, tzinfo=TZ_BR)
    assert na_janela(momento) is dentro


def test_fuso_local_desta_maquina_e_o_de_brasilia():
    """O relógio de hardware em UTC (RealTimeIsUniversal=1) não muda o fuso que o
    sistema entrega: o Windows converte antes, e o Python pede ao sistema."""
    from comentario_matinal.janela import agora, fuso_local

    assert agora().utcoffset() == datetime.now(TZ_BR).utcoffset()
    assert fuso_local() is not None


def test_divergencia_e_none_quando_o_fuso_bate():
    from comentario_matinal.janela import divergencia

    assert divergencia() is None


def test_rotulo_do_fuso_nomeia_brasilia_e_denuncia_o_resto():
    """Carimbar "de Brasília" um horário que não é de Brasília faria a etapa
    aplicar as regras temporais do guia contra a referência errada."""
    from zoneinfo import ZoneInfo

    from comentario_matinal.janela import rotulo_fuso

    assert rotulo_fuso(datetime(2026, 8, 17, 7, 40, tzinfo=TZ_BR)) == "de Brasília"

    lisboa = datetime(2026, 8, 17, 7, 40, tzinfo=ZoneInfo("Europe/Lisbon"))
    assert rotulo_fuso(lisboa) == "do fuso local (UTC+01:00)"

    toquio = datetime(2026, 8, 17, 7, 40, tzinfo=ZoneInfo("Asia/Tokyo"))
    assert rotulo_fuso(toquio) == "do fuso local (UTC+09:00)"


# --- dry run ----------------------------------------------------------------


def _metricas(cfg):
    return {a.ticker: {"chg_net": 0.05, "chg_pct": 1.0, "has_chart": True}
            for a in cfg.ativos}


def test_painel_fora_da_janela_sai_carimbado():
    """O carimbo vai no título, nunca na linha 'Referência:' — é ela que
    referencia_do_painel casa para achar o horário de redação."""
    from comentario_matinal.etapas import referencia_do_painel

    cfg = carrega_config()
    tarde = datetime(2026, 8, 16, 14, 20, tzinfo=TZ_BR)
    texto = monta_texto(cfg, _metricas(cfg), [], tarde, [],
                        calendario_vazio=True, dry_run=True)

    assert texto.splitlines()[0] == "PAINEL DIRECIONAL — DRY RUN"
    assert "DRY RUN" not in texto.splitlines()[1]
    r = referencia_do_painel(texto)
    assert (r.hour, r.minute) == (14, 20), "o carimbo não pode quebrar a regex"


def test_painel_dentro_da_janela_nao_carimba():
    cfg = carrega_config()
    texto = monta_texto(cfg, _metricas(cfg), [], ASOF, [],
                        calendario_vazio=True, dry_run=False)
    assert texto.splitlines()[0] == "PAINEL DIRECIONAL"
    assert "DRY RUN" not in texto


def test_marcador_de_ensaio_chega_a_mensagem_da_etapa():
    """O painel em texto vai injetado inteiro na mensagem: as três etapas herdam
    o marcador sem código novo no caminho delas, e podem registrá-lo na
    auditoria em vez de tratar o ensaio como plantão."""
    from comentario_matinal.etapas import mensagem_triagem

    cfg = carrega_config()
    tarde = datetime(2026, 8, 16, 14, 20, tzinfo=TZ_BR)
    painel = monta_texto(cfg, _metricas(cfg), [], tarde, [],
                         calendario_vazio=True, dry_run=True)
    ins = Insumos(guia="g", fontes="f", painel=painel, calendario="c", asof=tarde)

    assert "PAINEL DIRECIONAL — DRY RUN" in mensagem_triagem("prompt", ins, web=False)


def test_painel_nomeia_o_fuso_do_carimbo():
    cfg = carrega_config()
    texto = monta_texto(cfg, _metricas(cfg), [], ASOF, [],
                        calendario_vazio=True, dry_run=False)
    assert "de Brasília (06:40 de Nova York)" in texto


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


def test_ativo_com_mercado_fechado_e_marcado_no_texto():
    """O caso que a estreia expôs, e que duas passagens do modelo não pegaram.

    A imagem carimba MARKET CLOSED; o texto dizia só "VIX: baixa", e o comentário
    saiu afirmando que "na sessão corrente a volatilidade implícita cede" — sendo
    que aquela variação era da sexta-feira. A revisão declarou o VIX coerente,
    porque a informação nunca chegou a ela.

    O painel grava `has_chart` nas métricas; o texto passa a lê-lo, de modo que
    imagem e texto façam a MESMA afirmação sobre estar aberto ou fechado.
    """
    cfg = carrega_config()
    alvo = cfg.ativos[0]
    metricas = {
        a.ticker: {"chg_net": 0.05, "chg_pct": 1.0,
                   "has_chart": a.ticker != alvo.ticker}
        for a in cfg.ativos
    }
    texto = monta_texto(cfg, metricas, [], ASOF, [], calendario_vazio=True)

    assert f"  {alvo.rotulo}: alta — MERCADO FECHADO" in texto
    # Quem está aberto não ganha o carimbo: exatamente uma LINHA DE ATIVO o traz.
    abertos = [a for a in cfg.ativos if a.ticker != alvo.ticker]
    assert f"  {abertos[0].rotulo}: alta\n" in texto
    marcadas = [l for l in texto.splitlines()
                if l.startswith("  ") and "MERCADO FECHADO" in l]
    assert len(marcadas) == 1
    # E a nota explicando o marcador acompanha, senão o modelo o ignora.
    assert "variação da sessão anterior" in texto


def test_indisponivel_prevalece_sobre_mercado_fechado():
    """Sem dado não há direção a qualificar; dizer as duas coisas confunde."""
    cfg = carrega_config()
    alvo = cfg.ativos[0]
    metricas = {a.ticker: {"chg_net": 0.05, "chg_pct": 1.0, "has_chart": False}
                for a in cfg.ativos}
    texto = monta_texto(cfg, metricas, [], ASOF, [alvo.ticker], calendario_vazio=True)
    assert f"  {alvo.rotulo}: indisponível\n" in texto


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
