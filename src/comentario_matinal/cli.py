"""O plantão inteiro, do mercado ao documento.

    uv run matinal                      painel, calendário e bloco direcional
    uv run matinal triagem              etapa 1 — inventário de temas
    uv run matinal redacao --temas "…"  etapa 2 — o texto
    uv run matinal revisao              etapa 3 — checagem e texto revisado
    uv run matinal --comentario x.md    o .docx a partir do template

A coleta de mercado é única e serve a todas as saídas: a imagem colada no e-mail
e o texto usado para checar o comentário descrevem, por construção, os mesmos
números. Entre a triagem e a redação a decisão é humana — a redação recebe os
temas escolhidos pelo autor.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

# Backend sem tela: isto roda em linha de comando, não em notebook.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from comentario_matinal.calendario import (  # noqa: E402
    coleta_calendario,
    eventos_do_dia,
    tabela_markdown,
)
from comentario_matinal.config import (  # noqa: E402
    ARQUIVO_PADRAO,
    CONFIG_PADRAO,
    FONTES_PADRAO,
    GUIA_DE_ESTILO,
    PROMPT_ETAPA,
    SAIDA_PADRAO,
    TEMPLATE_PADRAO,
    carrega_config,
)
from comentario_matinal.dados import coleta_intraday, coleta_referencia  # noqa: E402
from comentario_matinal.janela import (  # noqa: E402
    agora,
    divergencia,
    faixa,
    fuso_local,
    na_janela,
)
from comentario_matinal.texto import monta_texto  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("comando", nargs="?", default=None,
                        choices=["triagem", "redacao", "revisao"],
                        help="Etapa de IA a executar. Sem argumento, coleta o "
                             "mercado e gera painel, calendário e texto.")
    parser.add_argument("--temas", type=str, default=None,
                        help="Temas escolhidos pelo autor, separados por '|': "
                             "dominante primeiro. Só para `redacao`.")
    parser.add_argument("--temas-arquivo", type=Path, default=None,
                        help="Arquivo com os temas, alternativa a --temas.")
    parser.add_argument("--fontes", type=Path, default=FONTES_PADRAO,
                        help=f"Pasta com os PDFs do dia. Padrão: {FONTES_PADRAO}")
    parser.add_argument("--anterior", type=Path, default=None,
                        help="Comentário do dia anterior, em .md. Sem isto, o "
                             "mais recente de `arquivo/` é usado.")
    parser.add_argument("--arquivo", type=Path, default=ARQUIVO_PADRAO,
                        help=f"Pasta dos comentários enviados. Padrão: {ARQUIVO_PADRAO}")
    parser.add_argument("--sem-anterior", action="store_true",
                        help="Roda a etapa sem o comentário do dia anterior.")
    parser.add_argument("--modelo", type=str, default=None,
                        help="Fixa o modelo da etapa. Sem isto, vale a "
                             "configuração da CLI do Claude Code.")
    parser.add_argument("--web", action="store_true",
                        help="Libera busca na web para confirmar dado já "
                             "presente nas fontes. O uso é registrado na "
                             "auditoria da etapa.")
    parser.add_argument("--asof", type=str, default=None,
                        help="Horário de referência ISO, ex. 2026-08-14T07:35. "
                             "Padrão: agora, no fuso da máquina. Não afeta a "
                             "decisão de dry run, que olha o relógio real.")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO,
                        help=f"Diretório das saídas. Padrão: {SAIDA_PADRAO}")
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--sem-calendario", action="store_true",
                        help="Pula a consulta BQL do calendário. Útil quando o "
                             "terminal não tem licença BQL.")
    parser.add_argument("--comentario", type=Path, default=None,
                        help="Markdown do comentário revisado. Monta o .docx "
                             "final a partir do template, reaproveitando o "
                             "painel e o calendário já gerados para a data.")
    parser.add_argument("--template", type=Path, default=TEMPLATE_PADRAO)
    args = parser.parse_args()

    asof = (datetime.fromisoformat(args.asof).replace(tzinfo=fuso_local())
            if args.asof else agora())

    # A janela é julgada pelo relógio real, nunca pelo --asof. Reproduzir um
    # horário antigo é ensaio por definição, e passar `--asof 07:35` às 07h50 —
    # que é o uso real do flag — continua sendo plantão.
    dry_run = not na_janela(agora())
    if dry_run:
        print(f"\n*** DRY RUN — fora da janela de {faixa()} ***\n"
              "Execução de ensaio. Não enviar o resultado à diretoria.\n",
              file=sys.stderr)
    aviso_fuso = divergencia()
    if aviso_fuso:
        print(aviso_fuso, file=sys.stderr)

    cfg = carrega_config(args.config)
    saida = args.saida.expanduser().resolve()
    saida.mkdir(parents=True, exist_ok=True)
    marca = f"{asof:%Y%m%d}"

    caminho_painel = saida / f"painel_{marca}.png"
    caminho_tabela = saida / f"calendario_{marca}.png"

    # As etapas de IA consomem o material já gerado pela coleta; nenhuma delas
    # toca no Bloomberg.
    if args.comando:
        return _roda_etapa(args, saida, marca)

    # O comentário é escrito depois do painel. Recoletar aqui produziria um
    # documento com o mercado de agora e um texto redigido contra o de antes —
    # exatamente a divergência que este comando existe para impedir. Havendo as
    # imagens do dia, a montagem as reaproveita e não toca no Bloomberg.
    if args.comentario and caminho_painel.exists() and caminho_tabela.exists():
        return _monta_documento(args, saida, marca, caminho_painel, caminho_tabela)

    # --- Mercado: uma coleta, três consumidores -----------------------------
    print(f"Coletando referência de {len(cfg.ativos)} ativos...", file=sys.stderr)
    ref, indisponiveis = coleta_referencia(cfg.ativos)
    if ref.empty:
        print("Erro: a consulta de referência não devolveu dado algum. "
              "Terminal Bloomberg ativo?", file=sys.stderr)
        return 1

    print("Coletando barras intradiárias...", file=sys.stderr)
    intraday = coleta_intraday(cfg.ativos, asof, ref)

    # --- Saída 1: o painel em imagem ---------------------------------------
    from daily.monitor import build_monitor_panel

    # A grade é desenhada na ordem de leitura por linha; o painel.toml lista por
    # coluna. As métricas voltam indexadas por ticker, então o texto não é afetado.
    fig, metricas = build_monitor_panel(
        cfg.para_ticker_info(cfg.ordem_da_grade()), ref, intraday,
        save_path=caminho_painel,
        grid=cfg.grade,
        allowed_root=saida,
        asof=asof,
        column_headers=cfg.titulos_colunas or None,
    )
    plt.close(fig)
    print(f"Painel:     {caminho_painel}")

    # --- Saída 2: a tabela do calendário econômico -------------------------
    eco = bancos = None
    if not args.sem_calendario:
        print("Consultando calendário econômico (BQL)...", file=sys.stderr)
        eco, bancos = coleta_calendario()

        from daily.tables import (
            CB_TABLE_SPEC_COMBINED,
            ECO_TABLE_SPEC,
            render_combined_tables,
        )

        fig_tab = render_combined_tables(
            [(eco, ECO_TABLE_SPEC), (bancos, CB_TABLE_SPEC_COMBINED)],
            save_path=caminho_tabela,
            allowed_root=saida,
        )
        if fig_tab is None:
            caminho_tabela = None
            print("Aviso: sem dados para renderizar a tabela do calendário.",
                  file=sys.stderr)
        else:
            plt.close(fig_tab)
            print(f"Calendário: {caminho_tabela}")

        # As etapas de IA leem o calendário como texto, nunca como imagem: pedir
        # a um modelo que leia número em gráfico é a origem dos dois erros que
        # este processo existe para impedir.
        caminho_cal_md = saida / f"calendario_{marca}.md"
        caminho_cal_md.write_text(tabela_markdown(eco, bancos), encoding="utf-8")
        print(f"Calendário: {caminho_cal_md}")

    # --- Saída 3: o bloco direcional em texto ------------------------------
    calendario_vazio = args.sem_calendario or eco is None or eco.empty
    eventos = [] if calendario_vazio else eventos_do_dia(eco, asof)

    texto = monta_texto(
        cfg=cfg, metricas=metricas, eventos=eventos, asof=asof,
        indisponiveis=indisponiveis, calendario_vazio=calendario_vazio,
        dry_run=dry_run,
    )
    caminho_texto = saida / f"painel_{marca}.txt"
    caminho_texto.write_text(texto, encoding="utf-8")
    print(f"Texto:      {caminho_texto}")

    print()
    print(texto)

    if indisponiveis:
        print(f"\nAviso: {len(indisponiveis)} ativo(s) do painel sem dado de "
              f"referência — {', '.join(indisponiveis)}", file=sys.stderr)

    # --- Saída 4: o documento final, quando há comentário revisado ---------
    if args.comentario:
        if not caminho_tabela:
            print("Erro: sem a tabela do calendário não há como montar o "
                  "documento.", file=sys.stderr)
            return 1
        return _monta_documento(args, saida, marca, caminho_painel, caminho_tabela)

    return 0


def _le(caminho: Path) -> str | None:
    return caminho.read_text(encoding="utf-8") if caminho.exists() else None


def _anterior(args, asof: datetime) -> str | None:
    """Resolve o comentário do dia anterior: explícito, automático, ou nenhum.

    A triagem julga ineditismo do tema contra ele, e a revisão procura
    contradição não sinalizada. Só a redação não o recebe. Depender de alguém
    lembrar de passar `--anterior` fazia as duas checagens não acontecerem no dia
    corrido, que é justamente quando elas importam.
    """
    from comentario_matinal.etapas import com_data, comentario_anterior

    if args.sem_anterior:
        return None

    if args.anterior:
        texto = _le(args.anterior)
        if texto is None:
            print(f"Aviso: {args.anterior} não existe; a etapa roda sem o "
                  "comentário do dia anterior.", file=sys.stderr)
        return texto

    achado = comentario_anterior(args.arquivo, asof)
    if achado is None:
        print(f"Aviso: nenhum comentário recente em {args.arquivo}. A etapa roda "
              "sem o do dia anterior — a checagem de ineditismo e de contradição "
              "fica sem base. Arquivar o comentário enviado resolve.",
              file=sys.stderr)
        return None

    caminho, data = achado
    print(f"Anterior:   {caminho.name} ({data:%d/%m/%Y})", file=sys.stderr)
    return com_data(caminho.read_text(encoding="utf-8"), data)


def _roda_etapa(args, saida: Path, marca: str) -> int:
    """Executa uma das três etapas de IA a partir do material já coletado."""
    from comentario_matinal.etapas import (
        FormatoInesperado,
        Insumos,
        comentario_revisado,
        mensagem_redacao,
        mensagem_revisao,
        mensagem_triagem,
        partes_da_redacao,
        roda,
        secao_ou_tudo,
    )
    from comentario_matinal.fontes import converte
    from comentario_matinal.modelo import ErroDoModelo

    etapa = args.comando

    # Fontes: PDF vira texto, para que o insumo seja o mesmo em qualquer backend.
    caminho_fontes = saida / f"fontes_{marca}.txt"
    conv = converte(args.fontes, caminho_fontes)
    n = conv.aproveitados
    if n:
        print(f"Fontes:     {n} PDF(s) convertidos em {caminho_fontes}",
              file=sys.stderr)
    else:
        print(f"Aviso: nenhum PDF aproveitado em {args.fontes}. A etapa vai rodar "
              "sem fontes noticiosas.", file=sys.stderr)
    if conv.vazios:
        print(f"Aviso: {len(conv.vazios)} PDF(s) não renderam texto — provavelmente "
              f"digitalização sem OCR: {', '.join(conv.vazios)}", file=sys.stderr)
    if conv.ignorados:
        print(f"Aviso: {len(conv.ignorados)} arquivo(s) de {args.fontes} NÃO foram "
              "lidos, porque só PDF é aproveitado como fonte — o conteúdo deles "
              f"não chegou ao modelo: {', '.join(conv.ignorados)}. "
              "Reimprimir em PDF (Outlook: Arquivo → Imprimir → Microsoft Print "
              "to PDF; navegador: Ctrl+P → Salvar em PDF).", file=sys.stderr)

    painel_txt = _le(saida / f"painel_{marca}.txt")
    calendario_md = _le(saida / f"calendario_{marca}.md")
    if painel_txt is None:
        print(f"Erro: falta o bloco direcional de {marca}. Rodar `uv run matinal` "
              "antes das etapas.", file=sys.stderr)
        return 1
    if calendario_md is None:
        print(f"Aviso: falta o calendário em texto de {marca}; a etapa roda sem "
              "ele.", file=sys.stderr)

    # O horário de redação é o do término da coleta, que é o carimbo do painel.
    # O relógio da máquina faria a etapa analisar material das 7h35 afirmando ser
    # meio-dia.
    from comentario_matinal.etapas import referencia_do_painel

    do_painel = referencia_do_painel(painel_txt)
    if args.asof:
        asof = datetime.fromisoformat(args.asof).replace(tzinfo=fuso_local())
        if do_painel and abs((asof - do_painel).total_seconds()) > 300:
            print(f"Aviso: --asof ({asof:%d/%m %Hh%M}) diverge da referência do "
                  f"painel ({do_painel:%d/%m %Hh%M}). O painel é o material que a "
                  "etapa analisa; conferir se é mesmo o do dia.", file=sys.stderr)
    elif do_painel:
        asof = do_painel
    else:
        asof = agora()
        print("Aviso: não consegui ler a referência do painel; usando o relógio.",
              file=sys.stderr)

    ins = Insumos(
        guia=GUIA_DE_ESTILO.read_text(encoding="utf-8"),
        fontes=caminho_fontes.read_text(encoding="utf-8") if n else "",
        painel=painel_txt,
        calendario=calendario_md or "",
        asof=asof,
        # A redação não recebe o comentário anterior; procurá-lo aqui só geraria
        # aviso enganoso na etapa que não o usa.
        anterior=_anterior(args, asof) if etapa in ("triagem", "revisao") else None,
    )
    prompt = PROMPT_ETAPA[etapa].read_text(encoding="utf-8")
    destino = saida / f"{etapa}_{marca}.md"

    if etapa == "triagem":
        mensagem = mensagem_triagem(prompt, ins, args.web)

    elif etapa == "redacao":
        temas = args.temas
        if args.temas_arquivo:
            if not args.temas_arquivo.exists():
                print(f"Erro: {args.temas_arquivo} não existe.", file=sys.stderr)
                return 1
            temas = args.temas_arquivo.read_text(encoding="utf-8")
        elif temas:
            temas = "\n".join(f"- {t.strip()}" for t in temas.split("|") if t.strip())
        if not temas:
            print("Erro: a redação precisa dos temas escolhidos pelo autor. "
                  "Passar --temas \"dominante | tema 2 | tema 3\" ou "
                  "--temas-arquivo. A decisão editorial entre a triagem e a "
                  "redação é humana.", file=sys.stderr)
            return 1

        anterior = _le(saida / f"triagem_{marca}.md")
        if anterior is None:
            print(f"Erro: falta a triagem de {marca}. Rodar `uv run matinal "
                  "triagem` antes.", file=sys.stderr)
            return 1
        alertas = secao_ou_tudo(anterior, "C) ALERTAS", "alertas")
        mensagem = mensagem_redacao(prompt, ins, temas, alertas, args.web)

    else:  # revisao
        anterior = _le(saida / f"redacao_{marca}.md")
        if anterior is None:
            print(f"Erro: falta a redação de {marca}. Rodar `uv run matinal "
                  "redacao` antes.", file=sys.stderr)
            return 1
        texto, auditoria = partes_da_redacao(anterior)
        mensagem = mensagem_revisao(prompt, ins, texto, auditoria, args.web)

    try:
        resposta = roda(mensagem, etapa, destino, web=args.web, modelo=args.modelo)
    except ErroDoModelo as e:
        print(f"Erro na etapa {etapa}: {e}", file=sys.stderr)
        return 1

    print(f"{etapa.capitalize():<11} {destino}")

    if etapa == "revisao":
        # Único ponto em que a saída do modelo entra direto no documento enviado
        # à diretoria. Formato inesperado interrompe em vez de gravar.
        try:
            md = comentario_revisado(resposta)
        except FormatoInesperado as e:
            print(f"\nErro: {e}", file=sys.stderr)
            print(f"A revisão completa está em {destino}.", file=sys.stderr)
            return 1
        caminho_md = saida / f"comentario_{marca}.md"
        caminho_md.write_text(md, encoding="utf-8")
        print(f"Comentário: {caminho_md}")
        print(f"\nMontar o documento: uv run matinal --comentario {caminho_md}",
              file=sys.stderr)
    elif etapa == "triagem":
        print("\nEscolher os temas e seguir para a redação:\n"
              "  uv run matinal redacao --temas \"dominante | tema 2 | tema 3\"",
              file=sys.stderr)

    return 0


def _monta_documento(args, saida: Path, marca: str,
                     painel: Path, calendario: Path) -> int:
    """Monta o .docx final a partir do template, com as imagens do dia."""
    from comentario_matinal.documento import monta

    if not args.comentario.exists():
        print(f"Erro: {args.comentario} não existe.", file=sys.stderr)
        return 1
    if not args.template.exists():
        print(f"Erro: template não encontrado em {args.template}.", file=sys.stderr)
        return 1

    destino = saida / f"comentario_{marca}.docx"
    try:
        monta(
            template=args.template,
            markdown=args.comentario,
            painel=painel,
            calendario=calendario,
            destino=destino,
        )
    except RuntimeError as e:
        print(f"Erro ao montar o documento: {e}", file=sys.stderr)
        return 1

    print(f"Documento:  {destino}")
    print("Abrir no Word para inserir o gráfico do dia, se houver, conferir o "
          "texto e exportar o PDF.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
