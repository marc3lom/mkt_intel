"""O plantão inteiro, do mercado ao documento.

    uv run matinal                      painel, calendário e bloco direcional
    uv run matinal triagem              etapa 1 — inventário de temas
    uv run matinal redacao --temas "…"  etapa 2 — o texto
    uv run matinal revisao              etapa 3 — checagem e texto revisado
    uv run matinal --comentario x.md    o .docx a partir do template
    uv run matinal conferir             .docx contra .md, antes do e-mail
    uv run matinal enviado              arquiva o enviado e limpa o dia

A coleta de mercado é única e serve a todas as saídas: a imagem colada no e-mail
e o texto usado para checar o comentário descrevem, por construção, os mesmos
números. Entre a triagem e a redação a decisão é humana — a redação recebe os
temas escolhidos pelo autor.
"""

# Este módulo é fachada: o plantão está em `plantao.py`, e aqui ficam só as três
# coisas que são de terminal — ler a linha de comando, escrever nas duas saídas
# padrão e traduzir erro em código de saída. Regra de negócio nova entra lá,
# nunca aqui, senão o notebook passa a divergir do comando.
#
# O texto acima é a descrição que o argparse imprime no --help; o que não for
# para o usuário do comando ler fica neste comentário, e não no docstring.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

# Backend sem tela: isto roda em linha de comando, não em notebook.
matplotlib.use("Agg")

from comentario_matinal import plantao  # noqa: E402
from comentario_matinal.config import (  # noqa: E402
    ARQUIVO_PADRAO,
    CONFIG_PADRAO,
    FONTES_PADRAO,
    SAIDA_PADRAO,
    TEMPLATE_PADRAO,
)
from comentario_matinal.plantao import (  # noqa: E402
    Contexto,
    ErroDePlantao,
    ErroNoModelo,
    MontagemFalhou,
    RevisaoIlegivel,
    SemTemas,
)

# Os subcomandos que o plantão expõe, na ordem do runbook.
SUBCOMANDOS = ("triagem", "redacao", "revisao", "conferir", "enviado")


def _erra(mensagem: str) -> None:
    print(mensagem, file=sys.stderr)


class _Voz:
    """O stderr do comando, com memória do que já disse.

    Os passos que demoram mostram cada aviso na hora em que ele aparece, para
    que o autor possa interromper enquanto ainda vale a pena, e ainda assim o
    devolvem inteiro — no resultado ou na exceção. Quem termina em erro traz o
    registro completo, e é este objeto que sabe qual parte dele o autor já leu.

    A memória fica na fachada de propósito: o núcleo entrega sempre tudo, e
    quem tem duas saídas para conciliar é quem escreve na tela.
    """

    def __init__(self) -> None:
        self.ditos: list[str] = []

    def __call__(self, mensagem: str) -> None:
        self.ditos.append(mensagem)
        _erra(mensagem)

    def ineditos(self, avisos: list[str]) -> list[str]:
        return [aviso for aviso in avisos if aviso not in self.ditos]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("comando", nargs="?", default=None,
                        choices=SUBCOMANDOS,
                        help="Etapa a executar. `conferir` compara o .docx com "
                             "o .md, sem arquivar nem limpar — para rodar entre "
                             "o Word e o e-mail. `enviado` fecha o plantão: "
                             "arquiva o comentário e limpa fontes/ e saida/. "
                             "Sem argumento, coleta o mercado e gera painel, "
                             "calendário e texto.")
    parser.add_argument("--forcar", action="store_true",
                        help="Só para `enviado`: contorna as três recusas — "
                             "fora da janela, divergência entre .docx e .md, e "
                             "destino já arquivado. É rombudo de propósito, "
                             "contorna as três de uma vez.")
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

    voz = _Voz()
    try:
        return _despacha(args, voz)
    except SemTemas as e:
        # A falta é do núcleo; a instrução de como suprir é de quem foi chamado
        # pela linha de comando. No notebook a mesma falta ensina outra coisa.
        #
        # O arquivo inexistente só é acusado aqui, e não na hora de ler: as
        # checagens que o núcleo faz antes — bloco direcional, calendário,
        # horário de redação — vêm primeiro, e os avisos delas se perderiam se a
        # fachada abortasse antes de chamá-lo.
        if args.temas_arquivo and not args.temas_arquivo.exists():
            return _falha(e, voz, f"Erro: {args.temas_arquivo} não existe.")
        return _falha(e, voz,
                      "Erro: a redação precisa dos temas escolhidos pelo autor. "
                      "Passar --temas \"dominante | tema 2 | tema 3\" ou "
                      "--temas-arquivo. A decisão editorial entre a triagem e a "
                      "redação é humana.")
    except ErroNoModelo as e:
        return _falha(e, voz, f"Erro na etapa {args.comando}: {e}")
    except RevisaoIlegivel as e:
        # A revisão foi gravada antes de o extrator falhar, e o caminho dela sai
        # como o de qualquer etapa que termina: é o arquivo que o autor precisa
        # abrir para ver o que o modelo devolveu.
        print(f"{args.comando.capitalize():<11} {e.destino}")
        return _falha(e, voz, f"\nErro: {e}\nA revisão completa está em {e.destino}.")
    except MontagemFalhou as e:
        return _falha(e, voz, f"Erro ao montar o documento: {e}")
    except ErroDePlantao as e:
        return _falha(e, voz, f"Erro: {e}")


def _falha(e: ErroDePlantao, voz: _Voz, mensagem: str) -> int:
    """Mostra o que o passo ainda não disse, e então por que ele parou."""
    for aviso in voz.ineditos(e.avisos):
        _erra(aviso)
    _erra(mensagem)
    return 1


def _despacha(args, voz: _Voz) -> int:
    ctx = plantao.contexto(asof=args.asof, saida=args.saida, fontes=args.fontes,
                           arquivo=args.arquivo, config=args.config)
    for aviso in ctx.avisos:
        _erra(aviso)

    if args.comando == "conferir":
        return _conferir(ctx)

    if args.comando == "enviado":
        return _enviado(args, ctx, voz)

    # As etapas de IA consomem o material já gerado pela coleta; nenhuma delas
    # toca no Bloomberg.
    if args.comando:
        return _etapa(args, ctx, voz)

    return _coleta(args, ctx, voz)


def _coleta(args, ctx: Contexto, voz: _Voz) -> int:
    """Painel, calendário e bloco direcional — e o documento, se houver texto."""
    caminho_painel = ctx.saida / f"painel_{ctx.marca}.png"
    caminho_tabela = ctx.saida / f"calendario_{ctx.marca}.png"

    # O comentário é escrito depois do painel. Recoletar aqui produziria um
    # documento com o mercado de agora e um texto redigido contra o de antes —
    # exatamente a divergência que este comando existe para impedir. Havendo as
    # imagens do dia, a montagem as reaproveita e não toca no Bloomberg.
    if args.comentario and caminho_painel.exists() and caminho_tabela.exists():
        return _documento(args, ctx)

    mercado = plantao.coleta_mercado(ctx, progresso=voz)

    painel = plantao.desenha_painel(ctx, mercado)
    print(f"Painel:     {painel.caminho}")

    calendario = None
    if not args.sem_calendario:
        calendario = plantao.prepara_calendario(ctx, progresso=voz)
        for aviso in calendario.avisos:
            _erra(aviso)
        if calendario.caminho_png:
            print(f"Calendário: {calendario.caminho_png}")
        print(f"Calendário: {calendario.caminho_md}")

    bloco = plantao.monta_bloco(ctx, mercado, painel, calendario)
    print(f"Texto:      {bloco.caminho}")

    print()
    print(bloco.texto)

    for aviso in bloco.avisos:
        _erra(aviso)

    if args.comentario:
        if calendario is not None and calendario.caminho_png is None:
            _erra("Erro: sem a tabela do calendário não há como montar o "
                  "documento.")
            return 1
        return _documento(args, ctx)

    return 0


def _documento(args, ctx: Contexto) -> int:
    destino = plantao.monta_documento(ctx, args.comentario, template=args.template)
    print(f"Documento:  {destino}")
    _erra("Abrir no Word para inserir o gráfico do dia, se houver, conferir o "
          "texto e exportar o PDF.")
    return 0


def _etapa(args, ctx: Contexto, voz: _Voz) -> int:
    """Traduz os flags da etapa e mostra o que ela produziu."""
    temas = args.temas
    if args.temas_arquivo:
        # Arquivo ausente vira ausência de temas: quem acusa é o `SemTemas` do
        # núcleo, depois das checagens dele.
        temas = (args.temas_arquivo.read_text(encoding="utf-8")
                 if args.temas_arquivo.exists() else None)
    elif temas:
        temas = "\n".join(f"- {t.strip()}" for t in temas.split("|") if t.strip())

    # Só as etapas que consomem o comentário do dia anterior traduzem os flags
    # dele. Quem decide quais são é o núcleo: avisar sobre um arquivo que a
    # redação nem vai receber engana em vez de informar.
    anterior = plantao.AUTOMATICO
    if args.comando in plantao.COM_ANTERIOR:
        if args.sem_anterior:
            anterior = None
        elif args.anterior:
            anterior = (args.anterior.read_text(encoding="utf-8")
                        if args.anterior.exists() else None)
            if anterior is None:
                _erra(f"Aviso: {args.anterior} não existe; a etapa roda sem o "
                      "comentário do dia anterior.")

    # Os avisos da etapa saem enquanto ela roda, e não no fim: a chamada ao
    # modelo leva minutos, e o que eles dizem — fontes ausentes, comentário
    # anterior sem base — só serve para decidir se vale interromper.
    etapa = plantao.roda_etapa(ctx, args.comando, temas=temas, anterior=anterior,
                               web=args.web, modelo=args.modelo, progresso=voz)

    print(f"{etapa.nome.capitalize():<11} {etapa.caminho}")

    if etapa.comentario:
        print(f"Comentário: {etapa.comentario}")
        _erra(f"\nMontar o documento: uv run matinal --comentario {etapa.comentario}")
    elif etapa.nome == "triagem":
        _erra("\nEscolher os temas e seguir para a redação:\n"
              "  uv run matinal redacao --temas \"dominante | tema 2 | tema 3\"")

    return 0


def _conferir(ctx: Contexto) -> int:
    from comentario_matinal.enviado import relatorio

    div = plantao.confere(ctx)
    if not div:
        print(f"Conferido:  o .docx e o .md dizem a mesma coisa ({ctx.marca}).")
        return 0

    _erra(f"O .docx e o .md divergem em {len(div)} marcador(es).\n")
    for linha in relatorio(div):
        _erra(linha)
    _erra("Se a alteração foi intencional, repetir no .md antes de enviar: é "
          "ele que a triagem de amanhã lê como comentário do dia anterior.")
    return 1


def _enviado(args, ctx: Contexto, voz: _Voz) -> int:
    # O aviso de arquivamento sem conferência sai por `voz`, no instante em que
    # aparece: logo depois dele o `arquiva` escreve o seu direto no stderr, e as
    # duas linhas só fazem sentido na ordem em que os fatos ocorreram.
    fechamento = plantao.fecha_plantao(ctx, forcar=args.forcar, progresso=voz)

    for caminho in fechamento.arquivados:
        print(f"Arquivado:  {caminho}")
    print(f"Limpeza:    {fechamento.removidos} arquivo(s) removidos de "
          f"{ctx.fontes.name}/ e {ctx.saida.name}/")
    print("\nPlantão encerrado. O repositório está pronto para amanhã.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
