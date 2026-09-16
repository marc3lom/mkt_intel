"""As duas formas de rodar o plantão não podem divergir.

O comando e o notebook são fachadas sobre o mesmo núcleo, então nenhum
reimplementa nada. O que sobra de duplicação é a SEQUÊNCIA — a ordem dos passos
existe no argparse e nas células —, e é ela que estes testes prendem.
"""

import inspect
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
NOTEBOOK = RAIZ / "notebooks" / "plantao.ipynb"
CLI = RAIZ / "src" / "comentario_matinal" / "cli.py"

# O fechamento do plantão fica fora do notebook de propósito: apaga fontes/ e
# saida/, grava o arquivo que a triagem de amanhã lê, e notebook é onde se
# re-executa célula sem querer.
FORA_DO_NOTEBOOK = {"fecha_plantao"}

# Os códigos de remédio que o notebook deliberadamente não traduz, com o motivo
# de cada um. Todos são recusas do `fecha_plantao`: sem o passo, o autor não tem
# como esbarrar na recusa, e uma frase para ela seria instrução para o que não se
# faz neste arquivo.
CODIGOS_FORA_DO_NOTEBOOK = {
    "FORCAR_FORA_DA_JANELA": "recusa do fechamento fora da janela de plantão",
    "FORCAR_DIVERGENCIA": "recusa do fechamento com o .docx divergindo do .md",
    "FORCAR_DESTINO_OCUPADO": "recusa do fechamento com a data já arquivada",
}

# Como cada subcomando do terminal aparece no notebook. Nem sempre pelo nome: o
# `conferir` da linha de comando é a função `confere` do núcleo, e as três
# etapas de IA chegam como o nome da etapa passado a `roda_etapa`. Este mapa é
# a correspondência entre as duas fachadas — o lugar onde elas podem divergir
# sem que nada mais perceba.
EQUIVALENTE = {
    # `imagens` para antes do bloco direcional, e no notebook do plantão isso é
    # parar antes da célula dele — daí a equivalência ser o passo do painel, e
    # não um nome próprio. Quem quer só as duas imagens tem fachada dedicada em
    # `notebooks/imagens.ipynb`, que o teste do ponto de parada prende.
    "imagens": "plantao.desenha_painel",
    "triagem": '"triagem"',
    "redacao": '"redacao"',
    "revisao": '"revisao"',
    "conferir": "plantao.confere",
    # `enviado` fica fora de propósito: é o único passo destrutivo.
}

# Os parâmetros dos passos que o notebook deliberadamente não exercita, cada um
# com o motivo. Todos existem no terminal como flag; o que os une é serem
# conserto, ensaio ou investigação — coisa de quem já sabe o processo —, e não
# passo do plantão. O notebook ensina o plantão, e o terminal é onde se sai dele.
PARAMETROS_FORA_DO_NOTEBOOK = {
    "saida": "as saídas do dia vão para a pasta padrão do repositório; apontar "
             "outra é reprocessar um dia antigo sem misturá-lo com o de hoje",
    "fontes": "os PDFs da manhã ficam em `fontes/`, na pasta do produto — a célula "
              "do Passo 1 diz isso, e apontar outra pasta é caso de teste",
    "arquivo": "o comentário do dia anterior sai de `arquivo/`, que é onde o "
               "`uv run matinal enviado` o grava; não há o que escolher aqui",
    "config": "a lista de ativos do painel é canônica e única — `config/painel.toml`",
    "template": "o documento sai do template da mesa; outro template é ensaio de "
                "formatação, e nele o interesse é o .docx, não o plantão",
    "asof": "reproduzir um horário antigo é ensaio por definição, e ensaio se faz "
            "no terminal; aqui o horário vem do relógio e, nas etapas, do carimbo "
            "do painel, que é o que a etapa de fato analisa",
    "anterior": "o comentário do dia anterior entra sozinho, do arquivado mais "
                "recente; forçar outro, ou nenhum, é conserto de exceção",
    "modelo": "vale o modelo configurado na CLI do Claude Code. Fixá-lo por "
              "execução é investigação de backend, e trocá-lo no meio do plantão "
              "faria as três etapas rodarem em modelos diferentes",
}


def _notebook():
    import nbformat

    return nbformat.read(NOTEBOOK, as_version=4)


def _celulas_de_codigo() -> list[tuple[int, str]]:
    """As células de código, numeradas como o notebook as mostra na tela.

    A contagem é 1-based e inclui as de markdown, porque é assim que se aponta
    uma célula para alguém — e é o número que a mensagem de falha precisa dar.
    """
    return [(i, c.source) for i, c in enumerate(_notebook().cells, 1)
            if c.cell_type == "code"]


def _codigo() -> str:
    return "\n".join(fonte for _, fonte in _celulas_de_codigo())


def _parametros_dos_passos(plantao):
    """Os parâmetros opcionais de cada passo público, com o passo a que pertencem.

    Opcional aqui é o que uma fachada escolhe passar ou não: os posicionais
    obrigatórios são o material que o passo anterior produziu, e neles não há
    decisão alguma a tomar.
    """
    for passo in plantao.PASSOS:
        if passo in FORA_DO_NOTEBOOK:
            continue
        for nome, p in inspect.signature(getattr(plantao, passo)).parameters.items():
            if p.kind is p.KEYWORD_ONLY or p.default is not inspect.Parameter.empty:
                yield passo, nome


def _nome_da_constante(plantao, valor: str) -> str:
    """O nome da constante que guarda ``valor`` — é como as fachadas a escrevem.

    ``REMEDIOS`` e ``AVISOS`` carregam os valores; as células e o ``cli.py``
    escrevem ``plantao.COLETA_AUSENTE``. Sem constante correspondente, devolve o
    próprio valor, para que um código solto seja acusado em vez de estourar aqui.
    """
    for nome in dir(plantao):
        if nome.isupper() and getattr(plantao, nome) == valor:
            return nome
    return valor


def test_notebook_cobre_todo_passo_do_nucleo():
    from comentario_matinal import plantao

    codigo = _codigo()
    faltando = sorted(p for p in plantao.PASSOS
                      if p not in FORA_DO_NOTEBOOK and f"plantao.{p}" not in codigo)
    assert not faltando, (
        f"O notebook não exercita {faltando}. Passo novo no núcleo precisa de "
        "célula nova: sem isso as duas formas de rodar o plantão divergem, que é "
        "o que este teste existe para impedir."
    )


def test_o_notebook_segue_a_ordem_dos_passos_do_nucleo():
    """O que o README promete: é a SEQUÊNCIA que este arquivo prende.

    Procurar cada passo no código concatenado só provava presença — trocar duas
    células de lugar mantinha tudo verde. E a ordem é o que distingue um runbook
    de uma lista de funções: quem lê o notebook de cima para baixo está lendo o
    processo, e um passo fora de lugar ensina o processo errado.
    """
    from comentario_matinal import plantao

    celulas = _celulas_de_codigo()
    # Passo ausente é assunto do teste de cobertura. Aqui ele é pulado, e não
    # contado como fora de ordem: uma falta só precisa de um vermelho.
    presentes = [
        (passo, celula)
        for passo, celula in (
            (p, next((n for n, fonte in celulas if f"plantao.{p}" in fonte), None))
            for p in plantao.PASSOS if p not in FORA_DO_NOTEBOOK
        )
        if celula is not None
    ]

    fora = [
        f"`{depois}` (célula {n_depois}) aparece antes de `{antes}` (célula {n_antes})"
        for (antes, n_antes), (depois, n_depois) in zip(presentes, presentes[1:])
        if n_antes > n_depois
    ]
    assert not fora, (
        "As células saíram da ordem do runbook: " + "; ".join(fora) + ". A ordem "
        "dos passos é `plantao.PASSOS`, e cada célula consome o que a anterior "
        "gravou em `saida/` — trocá-las de lugar ensina o processo errado a quem "
        "aprende o plantão por aqui."
    )


def test_o_notebook_decide_sobre_todo_parametro_dos_passos():
    """Parâmetro novo obriga a decidir se o notebook o exercita, e como.

    `roda_etapa` sozinha tem cinco, e o notebook usava dois; os demais existem no
    terminal como flag e não têm contrapartida aqui. Não ter é decisão legítima —
    o que não pode é ser omissão. Sem este teste, um parâmetro acrescentado amanhã
    ficaria invisível numa das duas fachadas sem nada ficar vermelho, que é o
    mesmo buraco que `EQUIVALENTE` fechou para os subcomandos.

    A busca é pelo nome seguido de `=`, que é como um argumento nomeado aparece
    numa célula. É grosseira de propósito: prender a chamada exata obrigaria a
    mexer no teste a cada edição do notebook, e o que ele afere é a decisão.
    """
    from comentario_matinal import plantao

    codigo = _codigo()
    faltando = sorted(
        f"{passo}({nome})"
        for passo, nome in _parametros_dos_passos(plantao)
        if nome not in PARAMETROS_FORA_DO_NOTEBOOK and f"{nome}=" not in codigo
    )
    assert not faltando, (
        f"O notebook não exercita {faltando}, e nada diz que isso é de propósito. "
        "Ou uma célula passa o parâmetro, ou ele entra em "
        "PARAMETROS_FORA_DO_NOTEBOOK com o motivo escrito ao lado — como os flags "
        "de conserto e de ensaio, que só existem no terminal."
    )


def test_o_relatorio_da_conferencia_tem_um_dono_so():
    """O texto do `confere` não pode voltar a existir em duas cópias.

    Ele existia palavra por palavra no `cli.py` e numa célula. A frase que explica
    por que a divergência importa amanhã — é o `.md` que a triagem lê — é
    justamente a que uma das cópias esqueceria de atualizar, e ninguém notaria:
    as duas fachadas continuariam verdes, dizendo coisas diferentes.
    """
    frase = "Se a alteração foi intencional"
    for onde, fonte in (("o notebook", _codigo()),
                        ("o cli.py", CLI.read_text(encoding="utf-8"))):
        assert frase not in fonte, (
            f"{onde} voltou a escrever o relatório da conferência. Ele sai de "
            "`enviado.relatorio_da_conferencia`; a fachada escolhe só onde "
            "mostrar cada linha."
        )
        assert "relatorio_da_conferencia" in fonte, (
            f"{onde} deixou de usar `enviado.relatorio_da_conferencia`, que é o "
            "que impede as duas fachadas de divergirem no texto."
        )


def test_o_mapa_de_equivalencia_cobre_todo_subcomando():
    """Subcomando novo obriga a decidir se ele existe no notebook, e como."""
    from comentario_matinal.cli import SUBCOMANDOS

    faltando = sorted(set(SUBCOMANDOS) - set(EQUIVALENTE) - {"enviado"})
    assert not faltando, (
        f"{faltando} entrou no terminal sem entrada em EQUIVALENTE. Decidir se "
        "o notebook o cobre e por qual chamada — ou listá-lo como deliberadamente "
        "fora, com o motivo."
    )


def test_o_notebook_das_imagens_para_onde_o_subcomando_para():
    """`imagens.ipynb` é a fachada de notebook do `uv run matinal imagens`.

    O que as duas fachadas não podem divergir é o ponto de parada: as duas
    imagens saem, o bloco direcional não. Um `monta_bloco` acrescentado aqui
    transformaria este notebook no Passo 1 do plantão com outro nome — e quem o
    rodasse acharia que gerou só imagens, deixando em `saida/` um texto que
    ninguém escreveu.
    """
    import json

    caminho = RAIZ / "notebooks" / "imagens.ipynb"
    assert caminho.is_file(), (
        "O `uv run matinal imagens` existe no terminal e está sem fachada de "
        "notebook. Ou o notebook nasce, ou o subcomando sai."
    )

    codigo = "\n".join(
        "".join(celula["source"])
        for celula in json.loads(caminho.read_text(encoding="utf-8"))["cells"]
        if celula["cell_type"] == "code"
    )

    faltando = sorted(
        passo for passo in ("contexto", "coleta_mercado", "desenha_painel",
                            "prepara_calendario")
        if f"plantao.{passo}" not in codigo
    )
    assert not faltando, (
        f"O notebook das imagens não chama {faltando}, que o subcomando chama. "
        "As duas fachadas deixariam de produzir o mesmo."
    )

    assert "monta_bloco" not in codigo, (
        "O notebook das imagens monta o bloco direcional, e o subcomando para "
        "antes dele."
    )


def test_notebook_cobre_todo_subcomando_do_terminal():
    from comentario_matinal.cli import SUBCOMANDOS

    codigo = _codigo()
    faltando = sorted(c for c in SUBCOMANDOS
                      if c in EQUIVALENTE and EQUIVALENTE[c] not in codigo)
    assert not faltando, (
        f"O terminal tem {faltando} e o notebook não. Quem aprender o plantão "
        "pelo notebook não saberia que existem."
    )


def test_as_saidas_das_etapas_saem_renderizadas():
    """Triagem, redação e revisão são documentos Markdown; `print` os despeja crus.

    Na primeira rodada de verdade a tabela de temas candidatos saiu como uma
    parede de pipes, ilegível. A correção pegou a triagem e a revisão e esqueceu
    a redação — que é o meio da sequência, e o único texto das três que o autor
    lê inteiro antes de decidir se aceita.

    O bloco direcional fica de fora de propósito: é texto de largura fixa, e o
    Markdown desmancharia o alinhamento das colunas.
    """
    sem_renderizar = [
        n for n, fonte in _celulas_de_codigo()
        if "roda_etapa(" in fonte and "Markdown(" not in fonte
    ]
    assert not sem_renderizar, (
        f"As células {sem_renderizar} rodam uma etapa e mostram a saída sem "
        "renderizar. O que as três etapas devolvem é Markdown — tabela, títulos, "
        "citação —, e `print` entrega isso como texto cru."
    )


def _notebook_no_indice():
    """O notebook como o git o guardaria, e não como ele está em disco.

    Com o filtro `nbstripout` instalado, rodar o notebook suja a árvore de
    trabalho e não suja o commit — é exatamente para isso que o filtro existe.
    Ler o disco deixaria este teste vermelho toda manhã em que alguém usasse o
    notebook, e teste que fica vermelho todo dia vira teste que ninguém lê.

    O índice é o que de fato entraria no commit: com o filtro ele é limpo mesmo
    com a árvore suja; sem o filtro ele carrega o que a árvore carrega, e é aí
    que este teste precisa acusar.
    """
    import subprocess

    import nbformat

    try:
        # `:./caminho`, não `:caminho`: o produto mora numa subpasta do
        # repositório, e o `:caminho` puro do git resolve a partir do topo do
        # repositório, não do cwd — aqui apontaria para fora de `RAIZ`.
        bruto = subprocess.run(
            ["git", "show", ":./notebooks/plantao.ipynb"],
            capture_output=True, cwd=RAIZ, check=True,
        ).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip(f"não consegui ler o índice do git: {e}")
    return nbformat.reads(bruto, as_version=4)


def test_notebook_comitado_nao_carrega_saida():
    sujas = [i for i, c in enumerate(_notebook_no_indice().cells, 1)
             if c.cell_type == "code" and (c.get("outputs")
                                           or c.get("execution_count"))]
    assert not sujas, (
        f"As células {sujas} carregam saída de execução. Comitar assim leva dados "
        "de mercado — e possivelmente o texto do comentário antes de ele ter sido "
        "enviado — para o histórico do git. Rodar `uv run nbstripout "
        "notebooks/plantao.ipynb`, ou instalar o filtro com `uv run nbstripout "
        "--install`."
    )


def test_o_fechamento_do_plantao_nao_entra_no_notebook():
    """A restrição mais dura do projeto, aferida em vez de combinada.

    O `FORA_DO_NOTEBOOK` só dispensa o `fecha_plantao` da cobertura; nada impedia
    alguém de acrescentar a célula amanhã. Ele apaga fontes/ e saida/, grava o
    arquivo que a triagem de amanhã lê como comentário do dia anterior, e
    notebook é onde se re-executa célula sem querer.
    """
    assert "fecha_plantao" not in _codigo(), (
        "`fecha_plantao` apareceu numa célula. É o único passo destrutivo do "
        "processo: apaga fontes/ e saida/ e grava o arquivo que a triagem de "
        "amanhã lê como comentário do dia anterior. Ele fica no terminal. Se a "
        "decisão mudou, mudar junto o FORA_DO_NOTEBOOK e o motivo escrito ali."
    )


def test_o_notebook_tem_frase_para_todo_codigo_do_nucleo():
    """O outro lado do `test_o_terminal_tem_frase_para_todo_codigo_do_nucleo`.

    O `REMEDIO.get(..., "")` da célula 2 não falha quando um código novo aparece:
    ele mostra o fato e engole a instrução. Sem este teste, um código novo
    deixaria o notebook mudo com o terminal verde — a divergência exata que esta
    tarefa existe para fazer falhar alto.
    """
    from comentario_matinal import plantao

    codigo = _codigo()
    faltando = sorted(
        nome
        for nome in (_nome_da_constante(plantao, valor)
                     for valor in (*plantao.REMEDIOS, *plantao.AVISOS))
        if nome not in CODIGOS_FORA_DO_NOTEBOOK and f"plantao.{nome}" not in codigo
    )
    assert not faltando, (
        f"O notebook não diz nada sobre {faltando}. Código novo no núcleo precisa "
        "de frase nas duas fachadas — ou de entrada em CODIGOS_FORA_DO_NOTEBOOK, "
        "com o motivo, como as recusas do fechamento têm."
    )


def test_o_passo_3_para_o_run_all():
    """A única decisão humana do processo não pode ser atravessada por um Run All.

    O terminal tem a parada de graça: `matinal triagem` e `matinal redacao` são
    dois comandos, e entre eles há necessariamente uma pessoa. O notebook não tem
    essa fronteira — "executar tudo" é um item de menu —, e sem uma parada
    explícita a redação sairia sobre a lista que ficou na célula desde ontem, com
    minutos de modelo gastos antes de alguém notar.

    A parada vem ANTES da célula do `ESCOLHA`, e é por isso que a ordem é aferida
    aqui: depois dela, o `TEMAS` já teria sido montado com a escolha velha, e o
    Passo 4 rodado sozinho o consumiria sem que nada tivesse sido decidido.
    """
    celulas = _celulas_de_codigo()
    # A célula que *chama* a parada, não a que a define: o bootstrap escreve
    # `def parada(` e não é ele que interrompe coisa alguma.
    n_parada = next((n for n, fonte in celulas
                     if "parada(" in fonte and "def parada(" not in fonte), None)
    n_escolha = next((n for n, fonte in celulas
                      if "temas_da_triagem" in fonte), None)

    assert n_parada is not None, (
        "Nenhuma célula interrompe o notebook antes do Passo 3. Sem ela, um Run "
        "All atravessa a escolha dos temas — a única decisão que o processo não "
        "toma sozinho — e redige sobre a lista que estava na célula."
    )
    assert n_escolha is not None, (
        "Nenhuma célula monta os temas com `temas_da_triagem`. Se o Passo 3 mudou "
        "de forma, este teste precisa mudar junto."
    )
    assert n_parada < n_escolha, (
        f"A parada (célula {n_parada}) ficou depois do `ESCOLHA` (célula "
        f"{n_escolha}). Nessa ordem o `TEMAS` já existe no kernel montado com a "
        "escolha anterior, e parar ali deixa de proteger o que a parada existe "
        "para proteger."
    )
