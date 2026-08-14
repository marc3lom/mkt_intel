"""Comando único do plantão: painel, calendário e bloco direcional.

Uma execução produz as três saídas do plantão a partir de uma única coleta de
mercado. A imagem colada no e-mail e o texto usado para checar o comentário
descrevem, por construção, os mesmos números.

Uso:
    uv run matinal
    uv run matinal --asof 2026-08-14T07:35
    uv run matinal --saida ./saida
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

from comentario_matinal.calendario import coleta_calendario, eventos_do_dia  # noqa: E402
from comentario_matinal.config import (  # noqa: E402
    CONFIG_PADRAO,
    SAIDA_PADRAO,
    TEMPLATE_PADRAO,
    TZ_BR,
    carrega_config,
)
from comentario_matinal.dados import coleta_intraday, coleta_referencia  # noqa: E402
from comentario_matinal.texto import monta_texto  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asof", type=str, default=None,
                        help="Horário de referência ISO, ex. 2026-08-14T07:35. "
                             "Padrão: agora, em horário de Brasília.")
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

    asof = (datetime.fromisoformat(args.asof).replace(tzinfo=TZ_BR)
            if args.asof else datetime.now(TZ_BR))

    cfg = carrega_config(args.config)
    saida = args.saida.expanduser().resolve()
    saida.mkdir(parents=True, exist_ok=True)
    marca = f"{asof:%Y%m%d}"

    caminho_painel = saida / f"painel_{marca}.png"
    caminho_tabela = saida / f"calendario_{marca}.png"

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

    # --- Saída 3: o bloco direcional em texto ------------------------------
    calendario_vazio = args.sem_calendario or eco is None or eco.empty
    eventos = [] if calendario_vazio else eventos_do_dia(eco, asof)

    texto = monta_texto(
        cfg=cfg, metricas=metricas, eventos=eventos, asof=asof,
        indisponiveis=indisponiveis, calendario_vazio=calendario_vazio,
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
