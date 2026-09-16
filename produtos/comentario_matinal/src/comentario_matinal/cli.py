"""O plantão inteiro, do mercado ao documento.

    uv run matinal                      painel, calendário e bloco direcional
    uv run matinal triagem              etapa 1 — inventário de temas
    uv run matinal redacao --temas-numeros "1,3,2"   etapa 2 — o texto
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
SUBCOMANDOS = ("imagens", "triagem", "redacao", "revisao", "conferir", "enviado")

# O núcleo diz o que falta e para aí; a frase que ensina a suprir é de quem foi
# chamado. Estas são as do terminal — falam em `uv run matinal` e em flags, que
# é o que o autor tem à mão quando lê o erro.
#
# O separador de cada frase faz parte dela. O fato do núcleo termina onde
# termina, e é aqui que se decide se a instrução continua a linha ou abre outra.
REMEDIO = {
    plantao.COLETA_AUSENTE: " Rodar `uv run matinal` antes das etapas.",
    plantao.TRIAGEM_AUSENTE: " Rodar `uv run matinal triagem` antes.",
    plantao.TRIAGEM_ILEGIVEL:
        " Escolher os temas à mão, com --temas ou --temas-arquivo.",
    plantao.REDACAO_AUSENTE: " Rodar `uv run matinal redacao` antes.",
    plantao.FORCAR_FORA_DA_JANELA:
        "\nSe o envio ocorreu mesmo e o plantão atrasou, repetir com --forcar.",
    plantao.FORCAR_DIVERGENCIA:
        " Corrigir o .md para refletir o que foi enviado, ou --forcar para "
        "arquivar o .md como está.",
    plantao.FORCAR_DESTINO_OCUPADO:
        " Conferir se a data está certa; --forcar sobrescreve.",
}

# `SemTemas` é o único cuja instrução não cabe no fim: ela entra no meio, entre
# a falta e a razão dela. Por isso o seu handler reescreve a mensagem inteira em
# vez de completá-la, e por isso o código não está no REMEDIO acima.
REMEDIO_NO_MEIO = frozenset({plantao.TEMAS_AUSENTES})

# Os avisos que o terminal diz com o seu próprio vocabulário. O núcleo entrega
# um texto que não nomeia flag alguma, porque numa célula de notebook não há
# flag; aqui eles voltam a falar de linha de comando.
AVISO = {
    plantao.ASOF_DIVERGE_DO_PAINEL:
        "Aviso: --asof ({asof}) diverge da referência do painel ({painel}). O "
        "painel é o material que a etapa analisa; conferir se é mesmo o do dia.",
}

# O banner de dry run já sai do núcleo na forma que o terminal usa — asteriscos
# e linha em branco em volta, para interromper a leitura do stderr. Aqui não há
# o que reescrever; o notebook é que o troca por uma faixa.
AVISO_INTACTO = frozenset({plantao.DRY_RUN})


def _erra(mensagem: str) -> None:
    print(_no_vocabulario_do_terminal(mensagem), file=sys.stderr)


def _no_vocabulario_do_terminal(mensagem: str) -> str:
    """Reescreve o aviso que o núcleo deixou em forma neutra.

    Passa por aqui tudo o que o comando escreve no stderr, e não só os avisos:
    o que não tiver código atravessa intacto, e assim nenhum ponto de saída
    precisa lembrar de traduzir.
    """
    codigo = getattr(mensagem, "codigo", None)
    if codigo in AVISO:
        return AVISO[codigo].format(**mensagem.dados)
    return mensagem


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
                        help="Etapa a executar. `imagens` coleta o mercado e "
                             "grava só o painel e o calendário, para quem "
                             "escreve o texto por fora. `conferir` compara o "
                             ".docx com o .md, sem arquivar nem limpar — para "
                             "rodar entre o Word e o e-mail. `enviado` fecha o "
                             "plantão: arquiva o comentário e limpa fontes/ e "
                             "saida/. Sem argumento, coleta o mercado e gera "
                             "painel, calendário e texto.")
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
    parser.add_argument("--temas-numeros", type=str, default=None,
                        help="Números da tabela da triagem, separados por "
                             "vírgula e com o dominante primeiro: \"1,3,2\". "
                             "O texto sai da própria triagem, sem transcrição.")
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
        # Aqui a mensagem é reescrita inteira, e não completada no fim: ver
        # REMEDIO_NO_MEIO.
        #
        # O arquivo inexistente só é acusado aqui, e não na hora de ler: as
        # checagens que o núcleo faz antes — bloco direcional, calendário,
        # horário de redação — vêm primeiro, e os avisos delas se perderiam se a
        # fachada abortasse antes de chamá-lo.
        if args.temas_arquivo and not args.temas_arquivo.exists():
            return _falha(e, voz, f"Erro: {args.temas_arquivo} não existe.")
        return _falha(e, voz,
                      "Erro: a redação precisa dos temas escolhidos pelo autor. "
                      "Passar --temas-numeros \"1,3,2\", com os números da "
                      "triagem e o dominante primeiro, ou --temas / "
                      "--temas-arquivo para escrevê-los. A decisão editorial "
                      "entre a triagem e a redação é humana.")
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
    """Mostra o que o passo ainda não disse, e então por que ele parou.

    A instrução de como suprir a falta é acrescentada aqui, e não no núcleo:
    lá ela seria a mesma nas duas fachadas, e no notebook mandaria o autor
    digitar um comando que não existe na célula que ele está olhando.
    """
    for aviso in voz.ineditos(e.avisos):
        _erra(aviso)
    _erra(mensagem + REMEDIO.get(e.remedio, ""))
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

    if args.comando == "imagens":
        return _imagens(args, ctx, voz)

    # As etapas de IA consomem o material já gerado pela coleta; nenhuma delas
    # toca no Bloomberg.
    if args.comando:
        return _etapa(args, ctx, voz)

    return _coleta(args, ctx, voz)


def _imagens(args, ctx: Contexto, voz: _Voz) -> int:
    """Só o painel e o calendário, para quem escreve o texto por fora.

    Para antes do bloco direcional de propósito: ele é insumo das etapas de IA
    — é dele que a revisão tira a direção de cada ativo para cobrar acordo com o
    texto —, e quem não vai rodar etapa alguma não tem o que fazer com um
    arquivo a mais em `saida/`. Foi este o caminho que o repositório `daily`
    servia, com outro código e as mesmas duas imagens.
    """
    mercado = plantao.coleta_mercado(ctx, progresso=voz)

    painel = plantao.desenha_painel(ctx, mercado)
    print(f"Painel:     {painel.caminho}")

    if not args.sem_calendario:
        calendario = plantao.prepara_calendario(ctx, progresso=voz)
        for aviso in calendario.avisos:
            _erra(aviso)
        if calendario.caminho_png:
            print(f"Calendário: {calendario.caminho_png}")
        print(f"Calendário: {calendario.caminho_md}")

    return 0


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

    # A recusa por falta da tabela do calendário é do núcleo: sem ela o template
    # fica com um dos dois lugares de imagem vazio, e isso vale nas duas fachadas.
    # A linha que o autor lê aqui continua a mesma — o "Erro: " sai do handler.
    if args.comentario:
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
    if args.temas_numeros:
        # A escolha por número parte da tabela que a triagem acabou de
        # produzir, e o núcleo é quem a lê — o notebook chama a mesma função.
        # Erro de leitura sobe como `FaltaInsumo` e é tratado com os demais.
        temas = plantao.temas_da_triagem(
            ctx, [int(n) for n in args.temas_numeros.replace(",", " ").split()]
        )
    elif args.temas_arquivo:
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
        # Esta é a linha que o autor lê logo depois de ler a triagem, e é por ela
        # que ele decide o que digitar. Ensinar aqui o que o manual já não ensina
        # — os temas escritos à mão — é reintroduzir a transcrição pelo caminho
        # que ninguém revisa. Os números saem da tabela que ele acabou de ler.
        _erra("\nEscolher os temas e seguir para a redação, pelos números da "
              "tabela e com o dominante primeiro:\n"
              "  uv run matinal redacao --temas-numeros \"1,3,2\"")

    return 0


def _conferir(ctx: Contexto) -> int:
    """O relatório vem pronto do núcleo; daqui saem só o destino e o código.

    O texto era escrito aqui e repetido no notebook, palavra por palavra. Agora
    ele tem um dono só — `enviado.relatorio_da_conferencia` —, e o que continua
    sendo de terminal é a divisão entre stdout e stderr e o código de saída.
    """
    from comentario_matinal.enviado import relatorio_da_conferencia

    div = plantao.confere(ctx)
    linhas = relatorio_da_conferencia(div, ctx.marca)
    if not div:
        print("\n".join(linhas))
        return 0

    for linha in linhas:
        _erra(linha)
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
