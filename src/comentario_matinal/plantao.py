"""O plantão como funções, sem terminal e sem notebook.

O comando e o notebook são fachadas sobre este módulo. Nenhum dos dois
implementa o plantão, e é por isso que não podem divergir: há uma
implementação só.

Três coisas que o ``cli.py`` misturava ficam separadas aqui. Erro levanta
exceção. Aviso — o que não impede seguir, mas o autor precisa ver — viaja na
lista ``avisos`` do resultado, em vez de ir ao stderr e sumir. Código de saída
é vocabulário de terminal e não existe neste módulo.

Os avisos acumulados até um erro viajam na própria exceção. Sem isso eles se
perderiam justamente na execução que deu errado, que é quando o autor mais
precisa deles para entender o que faltou.

Este módulo diz o que aconteceu, nunca o que digitar em seguida: "Rodar `uv run
matinal` antes das etapas" é conselho certo no terminal e errado numa célula de
notebook, onde não há linha de comando alguma na tela que o autor está olhando.
O que falta, e o que contornaria uma recusa, viaja como dado — ``REMEDIOS`` nas
exceções, ``AVISOS`` nos avisos —, e a frase é escrita por cada fachada. Assim o
núcleo não conhece front-end nenhum, em vez de conhecer dois.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.calendario import (
    coleta_calendario,
    eventos_do_dia,
    tabela_markdown,
)
from comentario_matinal.config import (
    ARQUIVO_PADRAO,
    CONFIG_PADRAO,
    FONTES_PADRAO,
    GUIA_DE_ESTILO,
    MERCADO_FECHADO,
    PROMPT_ETAPA,
    SAIDA_PADRAO,
    TEMPLATE_PADRAO,
    Config,
    carrega_config,
)
from comentario_matinal.dados import coleta_intraday, coleta_referencia
from comentario_matinal.enviado import Divergencia
from comentario_matinal.janela import agora, divergencia, faixa, fuso_local, na_janela
from comentario_matinal.texto import monta_texto

# Os passos públicos, na ordem do runbook. É este o contrato que o notebook
# precisa cobrir, e é dele que o teste de sincronia parte.
PASSOS = (
    "contexto",
    "coleta_mercado",
    "desenha_painel",
    "prepara_calendario",
    "monta_bloco",
    "roda_etapa",
    # Depois de `roda_etapa` porque a escolha de temas acontece entre a triagem
    # e a redação, e `roda_etapa` cobre as três etapas numa entrada só. É a
    # ordem em que os dois aparecem no notebook, que é o que o teste afere.
    "temas_da_triagem",
    "monta_documento",
    "confere",
    "fecha_plantao",
)

# As duas etapas que recebem o comentário do dia anterior: a triagem para julgar
# ineditismo do tema, a revisão para apanhar contradição não sinalizada. A
# redação não o recebe, e procurá-lo ali só geraria aviso enganoso.
COM_ANTERIOR = ("triagem", "revisao")

# Tolerância entre o `asof` que o autor fixa e a referência gravada no painel.
# Cinco minutos cobrem o uso real do flag — reproduzir às 07h50 o horário de
# redação das 07h35 —, e acima disso o painel provavelmente é de outro dia.
TOLERANCIA_ASOF = 300

# O que falta, ou o que contornaria a recusa, nomeado como dado. A frase que
# ensina a supri-lo é de cada fachada: o mesmo `COLETA_AUSENTE` vira "rodar
# `uv run matinal`" no terminal e "rodar as células do Passo 1" no notebook.
COLETA_AUSENTE = "coleta_ausente"
TRIAGEM_AUSENTE = "triagem_ausente"
TRIAGEM_ILEGIVEL = "triagem_ilegivel"
REDACAO_AUSENTE = "redacao_ausente"
TEMAS_AUSENTES = "temas_ausentes"
FORCAR_FORA_DA_JANELA = "forcar_fora_da_janela"
FORCAR_DIVERGENCIA = "forcar_divergencia"
FORCAR_DESTINO_OCUPADO = "forcar_destino_ocupado"

# Todos eles, para que a fachada que esquecer um seja pega por teste em vez de
# calar a instrução em silêncio.
REMEDIOS = (
    COLETA_AUSENTE,
    TRIAGEM_AUSENTE,
    TRIAGEM_ILEGIVEL,
    REDACAO_AUSENTE,
    TEMAS_AUSENTES,
    FORCAR_FORA_DA_JANELA,
    FORCAR_DIVERGENCIA,
    FORCAR_DESTINO_OCUPADO,
)

# Avisos que cada fachada mostra à sua maneira. Um deles chama a coisa de
# `--asof` no terminal e de argumento de função no notebook; o outro é banner de
# stderr de um lado e faixa colorida do outro, e quem já o desenhou não quer o
# texto de novo logo abaixo.
DRY_RUN = "dry_run"
ASOF_DIVERGE_DO_PAINEL = "asof_diverge_do_painel"

AVISOS = (DRY_RUN, ASOF_DIVERGE_DO_PAINEL)


class Aviso(str):
    """Aviso que cada fachada pode dizer com o seu próprio vocabulário.

    É ``str`` para que quem só precisa mostrá-lo não precise saber de nada: o
    texto que ele carrega já está pronto e não nomeia flag alguma. O ``codigo`` e
    os ``dados`` existem para quem precisa dizer a mesma coisa em outra língua.
    """

    codigo: str
    dados: dict[str, str]

    def __new__(cls, texto: str, codigo: str, **dados: str) -> Self:
        aviso = super().__new__(cls, texto)
        aviso.codigo = codigo
        aviso.dados = dados
        return aviso


class ErroDePlantao(RuntimeError):
    """Impede seguir. Cada fachada decide como mostrar.

    Carrega os avisos já acumulados quando o erro apareceu, porque eles foram
    produzidos antes dele e o autor precisa vê-los na mesma ordem.

    A mensagem diz o fato e para aí. ``remedio``, quando existe, nomeia o que
    supriria a falta; a frase que ensina a supri-la é de quem chamou.
    """

    def __init__(self, mensagem: str, avisos: list[str] | None = None,
                 remedio: str | None = None) -> None:
        super().__init__(mensagem)
        self.avisos = list(avisos or [])
        self.remedio = remedio


class SemDadoDeMercado(ErroDePlantao):
    """A consulta de referência voltou vazia — terminal Bloomberg inativo?"""


class FaltaInsumo(ErroDePlantao):
    """Falta material que um passo anterior deveria ter produzido."""


class SemTemas(FaltaInsumo):
    """A redação foi pedida sem os temas escolhidos pelo autor.

    Separada das demais faltas porque a decisão editorial entre a triagem e a
    redação é humana: o que falta não é arquivo, é escolha. Como cada fachada
    pede os temas de um jeito, a mensagem que ensina a passá-los é delas.
    """


class ErroNoModelo(ErroDePlantao):
    """O modelo não devolveu a etapa. Qual etapa era, quem chamou sabe."""


class RevisaoIlegivel(ErroDePlantao):
    """A revisão veio em formato que o extrator não reconhece.

    Guarda o destino porque a resposta completa do modelo ficou gravada lá — é
    o arquivo que o autor precisa abrir para entender o que saiu.
    """

    def __init__(self, mensagem: str, destino: Path,
                 avisos: list[str] | None = None) -> None:
        super().__init__(mensagem, avisos)
        self.destino = destino


class MontagemFalhou(ErroDePlantao):
    """O template ou o Markdown impediram montar o .docx."""


# Por padrão, `roda_etapa` procura sozinha o comentário do dia anterior em
# ``ctx.arquivo``. O comando passa None quando recebe --sem-anterior, e o texto
# lido quando recebe --anterior. A busca automática é regra de negócio, não
# vocabulário de terminal, e por isso mora aqui.
AUTOMATICO = object()


@dataclass(frozen=True)
class Contexto:
    cfg: Config
    asof: datetime
    # Se o horário veio do autor ou do relógio. `roda_etapa` decide com isto
    # entre o `asof` pedido e a referência gravada no painel, e sem o campo as
    # duas fachadas divergiriam: o notebook não tem `args.asof` para consultar.
    asof_explicito: bool
    saida: Path
    fontes: Path
    arquivo: Path
    marca: str          # AAAAMMDD
    dry_run: bool
    avisos: list[str]   # divergência de fuso, hoje impressa e esquecida


@dataclass(frozen=True)
class Mercado:
    referencia: pd.DataFrame
    intraday: dict[str, pd.Series]
    indisponiveis: list[str]


@dataclass(frozen=True)
class Painel:
    figura: Figure
    metricas: dict[str, dict]
    caminho: Path


@dataclass(frozen=True)
class Calendario:
    eco: pd.DataFrame | None
    bancos: pd.DataFrame | None
    figura: Figure | None
    caminho_png: Path | None
    caminho_md: Path | None
    avisos: list[str]


@dataclass(frozen=True)
class Bloco:
    texto: str
    caminho: Path
    avisos: list[str]


@dataclass(frozen=True)
class Etapa:
    nome: str
    texto: str
    caminho: Path
    asof: datetime            # o horário de redação efetivamente usado
    comentario: Path | None   # só a revisão produz
    avisos: list[str]


@dataclass(frozen=True)
class Fechamento:
    arquivados: list[Path]
    removidos: int
    # O que foi arquivado sem conferência contra o documento enviado. Este aviso
    # não impede fechar o plantão, mas diz que o `.md` que amanhã será lido como
    # comentário do dia anterior entrou no arquivo sem ninguém garantir que é o
    # texto que a diretoria recebeu.
    avisos: list[str]


def _le(caminho: Path) -> str | None:
    return caminho.read_text(encoding="utf-8") if caminho.exists() else None


def _diz(progresso: Callable[[str], None] | None, mensagem: str) -> None:
    """Anuncia que um trabalho demorado começou.

    Progresso não é aviso e não cabe no resultado: ele só serve enquanto o
    passo roda, e quem lê o resultado já sabe que ele terminou. Quem quiser
    mostrar passa a função; o padrão é ninguém ver nada.
    """
    if progresso is not None:
        progresso(mensagem)


def contexto(asof: datetime | str | None = None,
             saida: Path = SAIDA_PADRAO,
             fontes: Path = FONTES_PADRAO,
             arquivo: Path = ARQUIVO_PADRAO,
             config: Path = CONFIG_PADRAO) -> Contexto:
    """O que vale para o plantão inteiro: configuração, horário e pastas.

    A janela é julgada pelo relógio real, nunca pelo ``asof``. Reproduzir um
    horário antigo é ensaio por definição, e passar `--asof 07:35` às 07h50 —
    que é o uso real do flag — continua sendo plantão.
    """
    explicito = asof is not None
    if isinstance(asof, str):
        momento = datetime.fromisoformat(asof).replace(tzinfo=fuso_local())
    elif asof is None:
        momento = agora()
    else:
        momento = asof

    avisos: list[str] = []
    dry_run = not na_janela(agora())
    if dry_run:
        avisos.append(Aviso(
            f"\n*** DRY RUN — fora da janela de {faixa()} ***\n"
            "Execução de ensaio. Não enviar o resultado à diretoria.\n",
            DRY_RUN, faixa=faixa()))
    aviso_fuso = divergencia()
    if aviso_fuso:
        avisos.append(aviso_fuso)

    cfg = carrega_config(config)
    saida = saida.expanduser().resolve()
    saida.mkdir(parents=True, exist_ok=True)

    return Contexto(
        cfg=cfg,
        asof=momento,
        asof_explicito=explicito,
        saida=saida,
        fontes=fontes,
        arquivo=arquivo,
        marca=f"{momento:%Y%m%d}",
        dry_run=dry_run,
        avisos=avisos,
    )


def coleta_mercado(ctx: Contexto,
                   progresso: Callable[[str], None] | None = None) -> Mercado:
    """Uma coleta, três consumidores: a imagem, o texto e o documento.

    A referência vem antes das barras porque a série intradiária é ancorada no
    fechamento anterior, que sai daquela. Inverter a ordem faria a variação ler
    como a da sessão, e não como a do dia.
    """
    _diz(progresso, f"Coletando referência de {len(ctx.cfg.ativos)} ativos...")
    ref, indisponiveis = coleta_referencia(ctx.cfg.ativos)
    if ref.empty:
        raise SemDadoDeMercado("a consulta de referência não devolveu dado algum. "
                               "Terminal Bloomberg ativo?")

    _diz(progresso, "Coletando barras intradiárias...")
    intraday = coleta_intraday(ctx.cfg.ativos, ctx.asof, ref)
    return Mercado(referencia=ref, intraday=intraday, indisponiveis=indisponiveis)


def desenha_painel(ctx: Contexto, mercado: Mercado) -> Painel:
    """O painel em imagem, e as métricas que cada tile de fato mostrou."""
    from comentario_matinal.render.painel import monta_painel

    caminho = ctx.saida / f"painel_{ctx.marca}.png"

    # A grade é desenhada na ordem de leitura por linha; o painel.toml lista por
    # coluna. As métricas voltam indexadas por ticker, então o texto não é afetado.
    fig, metricas = monta_painel(
        ctx.cfg.para_itens_da_grade(ctx.cfg.ordem_da_grade()),
        mercado.referencia, mercado.intraday,
        save_path=caminho,
        grid=ctx.cfg.grade,
        allowed_root=ctx.saida,
        asof=ctx.asof,
        cabecalhos=ctx.cfg.titulos_colunas or None,
        selo_fechado=MERCADO_FECHADO,
    )
    plt.close(fig)
    return Painel(figura=fig, metricas=metricas, caminho=caminho)


def prepara_calendario(ctx: Contexto,
                       progresso: Callable[[str], None] | None = None) -> Calendario:
    """A tabela do calendário econômico, em imagem e em texto.

    As etapas de IA leem o calendário como texto, nunca como imagem: pedir a um
    modelo que leia número em gráfico é a origem dos dois erros que este
    processo existe para impedir.
    """
    _diz(progresso, "Consultando calendário econômico (BQL)...")
    eco, bancos = coleta_calendario()

    from comentario_matinal.render.tabelas import ESPEC_BC, ESPEC_ECO, monta_tabelas

    avisos: list[str] = []
    caminho_png: Path | None = ctx.saida / f"calendario_{ctx.marca}.png"
    fig = monta_tabelas(
        [(eco, ESPEC_ECO), (bancos, ESPEC_BC)],
        save_path=caminho_png,
        allowed_root=ctx.saida,
    )
    if fig is None:
        caminho_png = None
        avisos.append("Aviso: sem dados para renderizar a tabela do calendário.")
    else:
        plt.close(fig)

    caminho_md = ctx.saida / f"calendario_{ctx.marca}.md"
    caminho_md.write_text(tabela_markdown(eco, bancos), encoding="utf-8")

    return Calendario(eco=eco, bancos=bancos, figura=fig,
                      caminho_png=caminho_png, caminho_md=caminho_md, avisos=avisos)


def monta_bloco(ctx: Contexto, mercado: Mercado, painel: Painel,
                calendario: Calendario | None) -> Bloco:
    """O bloco direcional em texto — o que as três etapas leem como mercado.

    Sem calendário o bloco continua saindo: ele descreve o mercado, e a ausência
    da agenda é dita no próprio texto. ``calendario=None`` é o caso de quem
    pulou a consulta BQL, e vale o mesmo que consulta vazia.
    """
    calendario_vazio = (calendario is None
                        or calendario.eco is None
                        or calendario.eco.empty)
    eventos = [] if calendario_vazio else eventos_do_dia(calendario.eco, ctx.asof)

    texto = monta_texto(
        cfg=ctx.cfg, metricas=painel.metricas, eventos=eventos, asof=ctx.asof,
        indisponiveis=mercado.indisponiveis, calendario_vazio=calendario_vazio,
        dry_run=ctx.dry_run,
    )
    caminho = ctx.saida / f"painel_{ctx.marca}.txt"
    caminho.write_text(texto, encoding="utf-8")

    avisos: list[str] = []
    if mercado.indisponiveis:
        avisos.append(f"\nAviso: {len(mercado.indisponiveis)} ativo(s) do painel sem "
                      f"dado de referência — {', '.join(mercado.indisponiveis)}")
    return Bloco(texto=texto, caminho=caminho, avisos=avisos)


def _do_arquivo(ctx: Contexto, asof: datetime,
                avisa: Callable[[str], None]) -> str | None:
    """Procura o comentário do dia anterior: no arquivo, senão em PDF nas fontes.

    Depender de alguém lembrar de apontar o arquivo fazia as duas checagens que
    ele alimenta — ineditismo e contradição — não acontecerem no dia corrido,
    que é justamente quando elas importam.

    O arquivado vence: é o texto exato que foi enviado, com a data no nome. O
    PDF é para quem não tem o arquivo — o colega que não fez o plantão de ontem
    anexa o e-mail impresso junto das fontes.
    """
    from comentario_matinal.etapas import com_data, comentario_anterior
    from comentario_matinal.fontes import anterior_em_pdf

    achado = comentario_anterior(ctx.arquivo, asof)
    if achado is not None:
        caminho, data = achado
        avisa(f"Anterior:   {caminho.name} ({data:%d/%m/%Y})")
        return com_data(caminho.read_text(encoding="utf-8"), data)

    em_pdf = anterior_em_pdf(ctx.fontes)
    if em_pdf is not None:
        nome, texto = em_pdf
        avisa(f"Anterior:   {nome} (PDF anexado às fontes)")
        return f"(anexado em PDF, {nome}; data de envio não verificada)\n\n{texto}"

    avisa(f"Aviso: nenhum comentário recente em {ctx.arquivo}, nem PDF "
          f"anterior*.pdf em {ctx.fontes}. A etapa roda só com as fontes — a "
          "checagem de ineditismo e de contradição fica sem base.")
    return None


# Uma linha da tabela de temas candidatos: o número na primeira célula, o tema
# na segunda. A linha de separação (`|---|---|`) não casa, porque exige dígitos.
RE_TEMA_CANDIDATO = re.compile(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|", re.MULTILINE)


def temas_da_triagem(ctx: Contexto, numeros: list[int]) -> str:
    """Os temas escolhidos, na ordem do autor, tirados da tabela da triagem.

    O primeiro número é o dominante — é dele que o guia manda partir o marcador
    de abertura —, e a ordem devolvida é a pedida, não a da tabela.

    O que sai daqui é ponto de partida, não texto final. A ressalva que amarra o
    marcador — um limite temporal, uma atribuição obrigatória, uma direção que o
    painel contradiz — é o que o autor acrescenta, e a tabela não tem como saber.
    Em 17/08 foi uma ressalva dessas que impediu o texto de afirmar que o dólar
    caíra na sessão, quando o painel mostrava o câmbio estável.
    """
    caminho = ctx.saida / f"triagem_{ctx.marca}.md"
    texto = _le(caminho)
    if texto is None:
        raise FaltaInsumo(f"falta a triagem de {ctx.marca}.",
                          remedio=TRIAGEM_AUSENTE)

    # A tabela numerada é a da seção A. Recortá-la evita que uma tabela futura
    # noutra seção entre na conta sem ninguém perceber.
    inicio = texto.find("A) TEMAS CANDIDATOS")
    trecho = texto[inicio:] if inicio >= 0 else texto
    fim = trecho.find("\n###", 1)
    if fim > 0:
        trecho = trecho[:fim]

    por_numero = {int(n): tema for n, tema in RE_TEMA_CANDIDATO.findall(trecho)}
    if not por_numero:
        # O modelo já desobedeceu formato uma vez — o `partes_da_redacao` existe
        # por isso. Devolver lista vazia em silêncio faria a redação rodar sem
        # tema algum, e o autor descobriria lendo o comentário.
        raise FaltaInsumo(
            f"não achei a tabela de temas candidatos em {caminho.name}.",
            remedio=TRIAGEM_ILEGIVEL,
        )

    faltando = [n for n in numeros if n not in por_numero]
    if faltando:
        raise FaltaInsumo(
            f"a triagem de {ctx.marca} não tem o tema "
            + ", ".join(str(n) for n in faltando)
            + f"; ela vai de 1 a {max(por_numero)}."
        )

    return "".join(f"- {por_numero[n]}\n" for n in numeros)


def roda_etapa(ctx: Contexto, nome: str, *, temas: str | None = None,
               anterior: str | None | object = AUTOMATICO,
               web: bool = False, modelo: str | None = None,
               progresso: Callable[[str], None] | None = None) -> Etapa:
    """Executa uma das três etapas de IA a partir do material já coletado.

    A ordem das checagens importa. O painel é lido antes de o horário de redação
    ser resolvido, porque é dele que esse horário sai; e o comentário anterior é
    procurado depois, porque a busca é datada por ele.

    Todo aviso daqui nasce antes da chamada ao modelo, que leva minutos. Guardá-lo
    só no resultado o entregaria depois da espera, quando ele já não serve para
    decidir se vale interromper: sem fontes noticiosas, ou sem o comentário do dia
    anterior, o autor prefere parar e resolver a rodar a etapa assim. Por isso
    ``progresso`` — quem o passa vê cada aviso na hora, e o resultado continua
    carregando todos para quem só quiser lê-los no fim.
    """
    from comentario_matinal.etapas import (
        FormatoInesperado,
        Insumos,
        comentario_revisado,
        mensagem_redacao,
        mensagem_revisao,
        mensagem_triagem,
        partes_da_redacao,
        referencia_do_painel,
        roda,
        secao_ou_tudo,
    )
    from comentario_matinal.fontes import converte
    from comentario_matinal.modelo import ErroDoModelo

    avisos: list[str] = []

    def avisa(mensagem: str) -> None:
        avisos.append(mensagem)
        _diz(progresso, mensagem)

    # Fontes: PDF vira texto, para que o insumo seja o mesmo em qualquer backend.
    caminho_fontes = ctx.saida / f"fontes_{ctx.marca}.txt"
    conv = converte(ctx.fontes, caminho_fontes)
    n = conv.aproveitados
    if n:
        avisa(f"Fontes:     {n} PDF(s) convertidos em {caminho_fontes}")
    else:
        avisa(f"Aviso: nenhum PDF aproveitado em {ctx.fontes}. A etapa vai rodar "
              "sem fontes noticiosas.")
    if conv.vazios:
        avisa(f"Aviso: {len(conv.vazios)} PDF(s) não renderam texto — provavelmente "
              f"digitalização sem OCR: {', '.join(conv.vazios)}")
    if conv.ignorados:
        avisa(f"Aviso: {len(conv.ignorados)} arquivo(s) de {ctx.fontes} NÃO foram "
              "lidos, porque só PDF é aproveitado como fonte — o conteúdo deles "
              f"não chegou ao modelo: {', '.join(conv.ignorados)}. "
              "Reimprimir em PDF (Outlook: Arquivo → Imprimir → Microsoft Print "
              "to PDF; navegador: Ctrl+P → Salvar em PDF).")

    painel_txt = _le(ctx.saida / f"painel_{ctx.marca}.txt")
    calendario_md = _le(ctx.saida / f"calendario_{ctx.marca}.md")
    if painel_txt is None:
        raise FaltaInsumo(f"falta o bloco direcional de {ctx.marca}.", avisos,
                          remedio=COLETA_AUSENTE)
    if calendario_md is None:
        avisa(f"Aviso: falta o calendário em texto de {ctx.marca}; a etapa roda "
              "sem ele.")

    # O horário de redação é o do término da coleta, que é o carimbo do painel.
    # O relógio da máquina faria a etapa analisar material das 7h35 afirmando ser
    # meio-dia.
    do_painel = referencia_do_painel(painel_txt)
    if ctx.asof_explicito:
        asof = ctx.asof
        if do_painel and abs((asof - do_painel).total_seconds()) > TOLERANCIA_ASOF:
            avisa(Aviso(
                f"Aviso: o horário de redação fixado ({asof:%d/%m %Hh%M}) diverge "
                f"da referência do painel ({do_painel:%d/%m %Hh%M}). O painel é o "
                "material que a etapa analisa; conferir se é mesmo o do dia.",
                ASOF_DIVERGE_DO_PAINEL,
                asof=f"{asof:%d/%m %Hh%M}", painel=f"{do_painel:%d/%m %Hh%M}"))
    elif do_painel:
        asof = do_painel
    else:
        asof = agora()
        avisa("Aviso: não consegui ler a referência do painel; usando o relógio.")

    if nome not in COM_ANTERIOR:
        texto_anterior = None
    elif anterior is AUTOMATICO:
        texto_anterior = _do_arquivo(ctx, asof, avisa)
    else:
        texto_anterior = anterior

    ins = Insumos(
        guia=GUIA_DE_ESTILO.read_text(encoding="utf-8"),
        fontes=caminho_fontes.read_text(encoding="utf-8") if n else "",
        painel=painel_txt,
        calendario=calendario_md or "",
        asof=asof,
        anterior=texto_anterior,
    )
    prompt = PROMPT_ETAPA[nome].read_text(encoding="utf-8")
    destino = ctx.saida / f"{nome}_{ctx.marca}.md"

    if nome == "triagem":
        mensagem = mensagem_triagem(prompt, ins, web)

    elif nome == "redacao":
        if not temas:
            raise SemTemas("a redação precisa dos temas escolhidos pelo autor. A "
                           "decisão editorial entre a triagem e a redação é "
                           "humana.", avisos, remedio=TEMAS_AUSENTES)
        triagem = _le(ctx.saida / f"triagem_{ctx.marca}.md")
        if triagem is None:
            raise FaltaInsumo(f"falta a triagem de {ctx.marca}.", avisos,
                              remedio=TRIAGEM_AUSENTE)
        alertas = secao_ou_tudo(triagem, "C) ALERTAS", "alertas")
        mensagem = mensagem_redacao(prompt, ins, temas, alertas, web)

    else:  # revisao
        redacao = _le(ctx.saida / f"redacao_{ctx.marca}.md")
        if redacao is None:
            raise FaltaInsumo(f"falta a redação de {ctx.marca}.", avisos,
                              remedio=REDACAO_AUSENTE)
        texto, auditoria = partes_da_redacao(redacao)
        mensagem = mensagem_revisao(prompt, ins, texto, auditoria, web)

    try:
        resposta = roda(mensagem, nome, destino, web=web, modelo=modelo)
    except ErroDoModelo as e:
        raise ErroNoModelo(str(e), avisos) from e

    comentario: Path | None = None
    if nome == "revisao":
        # Único ponto em que a saída do modelo entra direto no documento enviado
        # à diretoria. Formato inesperado interrompe em vez de gravar.
        try:
            md = comentario_revisado(resposta)
        except FormatoInesperado as e:
            raise RevisaoIlegivel(str(e), destino, avisos) from e
        comentario = ctx.saida / f"comentario_{ctx.marca}.md"
        comentario.write_text(md, encoding="utf-8")

    return Etapa(nome=nome, texto=resposta, caminho=destino, asof=asof,
                 comentario=comentario, avisos=avisos)


def monta_documento(ctx: Contexto, comentario: Path,
                    template: Path = TEMPLATE_PADRAO) -> Path:
    """Monta o .docx final a partir do template, com as imagens do dia.

    As imagens são as da data, não as de agora: o comentário foi escrito contra
    o painel gravado, e recoletar aqui produziria um documento cujo texto e cuja
    imagem descrevem manhãs diferentes.

    A falta da tabela do calendário recusa a montagem aqui, e não em cada
    fachada: é regra de negócio — o template tem dois lugares de imagem, e um
    deles ficaria vazio no documento que vai à diretoria. Recusar no núcleo
    também impede que o `add_picture` estoure com `FileNotFoundError`, que não é
    `ErroDePlantao` e escaparia do notebook como traceback cru.
    """
    from comentario_matinal.documento import monta

    if not comentario.exists():
        raise FaltaInsumo(f"{comentario} não existe.")
    if not template.exists():
        raise FaltaInsumo(f"template não encontrado em {template}.")

    calendario = ctx.saida / f"calendario_{ctx.marca}.png"
    if not calendario.exists():
        raise FaltaInsumo("sem a tabela do calendário não há como montar o "
                          "documento.")

    destino = ctx.saida / f"comentario_{ctx.marca}.docx"
    try:
        monta(
            template=template,
            markdown=comentario,
            painel=ctx.saida / f"painel_{ctx.marca}.png",
            calendario=calendario,
            destino=destino,
        )
    except RuntimeError as e:
        raise MontagemFalhou(str(e)) from e

    return destino


def confere(ctx: Contexto) -> list[Divergencia]:
    """Compara o documento com o Markdown, sem arquivar nem limpar.

    Existe para rodar entre o Word e o e-mail, que é a única janela em que a
    divergência ainda tem conserto. O `fecha_plantao` faz a mesma checagem, mas
    roda depois do envio: ali ela só serve para não contaminar a triagem de
    amanhã, não para salvar o comentário de hoje.
    """
    from comentario_matinal.enviado import divergencias

    md = ctx.saida / f"comentario_{ctx.marca}.md"
    docx = ctx.saida / f"comentario_{ctx.marca}.docx"

    for caminho in (md, docx):
        if not caminho.exists():
            raise FaltaInsumo(f"{caminho} não existe. A conferência compara os dois "
                              "arquivos da data; sem ambos não há o que comparar.")

    return divergencias(docx, md)


def fecha_plantao(ctx: Contexto, forcar: bool = False,
                  progresso: Callable[[str], None] | None = None) -> Fechamento:
    """Arquiva o comentário enviado e limpa o dia.

    Único passo que bloqueia fora da janela. Os outros produzem artefato, que
    sai carimbado como ensaio; este AFIRMA que o comentário foi enviado à
    diretoria, e o que ele arquiva vira o "comentário do dia anterior" da manhã
    seguinte. Registrar um ensaio ali contamina a triagem seguinte em silêncio.

    O aviso daqui precisa sair no momento em que aparece: o ``arquiva`` escreve
    direto no stderr logo em seguida, e guardar o nosso para o fim trocaria a
    ordem das duas linhas que o autor lê como uma frase só.
    """
    from comentario_matinal.enviado import (
        DestinoOcupado,
        arquiva,
        divergencias,
        limpa,
        relatorio,
    )

    avisos: list[str] = []

    def avisa(mensagem: str) -> None:
        avisos.append(mensagem)
        _diz(progresso, mensagem)

    if ctx.dry_run and not forcar:
        raise ErroDePlantao(
            f"fora da janela de {faixa()} — esta execução é ensaio, e `enviado` "
            "registra o comentário como enviado à diretoria. O que for arquivado "
            "vira o \"comentário do dia anterior\" de amanhã.",
            avisos, remedio=FORCAR_FORA_DA_JANELA)

    md = ctx.saida / f"comentario_{ctx.marca}.md"
    docx = ctx.saida / f"comentario_{ctx.marca}.docx"

    if docx.exists() and md.exists():
        div = divergencias(docx, md)
        if div and not forcar:
            raise ErroDePlantao(
                f"o .docx e o .md divergem em {len(div)} marcador(es). O .md é o "
                "que fica arquivado e o que a triagem de amanhã lê como comentário "
                "do dia anterior.\n\n"
                + "\n".join(relatorio(div))
                + "\nNada foi arquivado.",
                avisos, remedio=FORCAR_DIVERGENCIA)
    elif not docx.exists():
        avisa("Aviso: não há .docx da data; arquivando sem conferir o texto "
              "contra o documento enviado.")

    try:
        escritos = arquiva(ctx.saida, ctx.arquivo, ctx.marca, forcar=forcar)
    except FileNotFoundError as e:
        raise ErroDePlantao(str(e), avisos) from e
    except DestinoOcupado as e:
        raise ErroDePlantao(f"{e}.\nNada foi arquivado e nada foi apagado.",
                            avisos, remedio=FORCAR_DESTINO_OCUPADO) from e

    # Só aqui, e só depois de o arquivamento ter dado certo.
    n = limpa([ctx.fontes, ctx.saida])
    return Fechamento(arquivados=escritos, removidos=n, avisos=avisos)
