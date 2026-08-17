"""As duas formas de rodar o plantão não podem divergir.

O comando e o notebook são fachadas sobre o mesmo núcleo, então nenhum
reimplementa nada. O que sobra de duplicação é a SEQUÊNCIA — a ordem dos passos
existe no argparse e nas células —, e é ela que estes testes prendem.
"""

from pathlib import Path

NOTEBOOK = Path(__file__).parent.parent / "notebooks" / "plantao.ipynb"

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
    "triagem": '"triagem"',
    "redacao": '"redacao"',
    "revisao": '"revisao"',
    "conferir": "plantao.confere",
    # `enviado` fica fora de propósito: é o único passo destrutivo.
}


def _notebook():
    import nbformat

    return nbformat.read(NOTEBOOK, as_version=4)


def _codigo() -> str:
    return "\n".join(c.source for c in _notebook().cells if c.cell_type == "code")


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


def test_o_mapa_de_equivalencia_cobre_todo_subcomando():
    """Subcomando novo obriga a decidir se ele existe no notebook, e como."""
    from comentario_matinal.cli import SUBCOMANDOS

    faltando = sorted(set(SUBCOMANDOS) - set(EQUIVALENTE) - {"enviado"})
    assert not faltando, (
        f"{faltando} entrou no terminal sem entrada em EQUIVALENTE. Decidir se "
        "o notebook o cobre e por qual chamada — ou listá-lo como deliberadamente "
        "fora, com o motivo."
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


def test_notebook_comitado_nao_carrega_saida():
    sujas = [i for i, c in enumerate(_notebook().cells, 1)
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
