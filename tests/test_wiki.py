"""As transformações puras do publicador do Wiki.

A trama de git — clonar, comitar, empurrar — não vale testar: não há como
aferir por teste uma cópia que mora noutro repositório git, e ensaiá-la é
questão de rodar `uv run publica-wiki --sem-push` contra um `git init --bare`
descartável, à mão, uma vez. O que vale testar é o que quebra em silêncio: o
nome que cada página ganha no wiki, o banner que denuncia a cópia e o SHA de
origem, e a reescrita de link — sobretudo a âncora com hífen duplo, que uma
reescrita "arrumadinha" colapsaria sem avisar ninguém.
"""

import pytest

from comentario_matinal import wiki
from comentario_matinal.wiki import FAIXA, _nome_no_wiki, _reescreve_links


def _caminho(nome: str):
    """Um `Path` com o nome certo, sem precisar que o arquivo exista no disco.

    `_nome_no_wiki` só olha `.name` e `.stem` — não abre o arquivo — então
    testar com um caminho que não existe é fiel ao que a função faz.
    """
    return wiki.Path(nome)


def test_o_indice_vira_a_capa_do_wiki():
    assert _nome_no_wiki(_caminho("README.md")) == "Home.md"


@pytest.mark.parametrize(
    "origem, esperado",
    [
        ("01-primeiro-dia.md", "Primeiro-dia.md"),
        ("02-instalacao.md", "Instalacao.md"),
        ("03-runbook.md", "Runbook.md"),
        ("04-decisoes.md", "Decisoes.md"),
        ("05-quando-da-errado.md", "Quando-da-errado.md"),
    ],
)
def test_pagina_numerada_perde_o_numero_e_ganha_maiuscula(origem, esperado):
    assert _nome_no_wiki(_caminho(origem)) == esperado


def test_nome_errado_e_pego_pelo_teste():
    """Prova que o teste acima falharia se `_nome_no_wiki` regredisse.

    Sem este caso, um erro de digitação no valor esperado (por exemplo
    aceitar `primeiro-dia.md`, sem maiúscula) passaria despercebido — o
    teste de cima só prova que a função bate com o que eu disse que ela
    deveria fazer, não que essa expectativa está certa.
    """
    assert _nome_no_wiki(_caminho("01-primeiro-dia.md")) != "primeiro-dia.md"


def test_a_faixa_leva_a_origem_e_o_sha():
    texto = FAIXA.format(origem="03-runbook.md", sha="ec86860")
    assert "docs/plantao/03-runbook.md" in texto
    assert "ec86860" in texto
    assert texto.startswith(">")


def test_a_faixa_avisa_para_nao_editar_ali():
    """O aviso de "não editar aqui" é o que impede a edição feita direto no
    wiki de se perder em silêncio na próxima publicação, sem que quem editou
    entenda por quê."""
    texto = FAIXA.format(origem="03-runbook.md", sha="ec86860")
    assert "não editar" in texto.lower()


# As seis páginas do manual, no mapeamento que `monta()` monta de fato — usado
# em vários testes de _reescreve_links abaixo.
_PAGINAS = {
    "README.md": "Home",
    "01-primeiro-dia.md": "Primeiro-dia",
    "02-instalacao.md": "Instalacao",
    "03-runbook.md": "Runbook",
    "04-decisoes.md": "Decisoes",
    "05-quando-da-errado.md": "Quando-da-errado",
}


def test_link_entre_paginas_troca_o_nome_de_arquivo_pelo_nome_do_wiki():
    texto = "Veja [o runbook](03-runbook.md)."
    assert _reescreve_links(texto, _PAGINAS) == "Veja [o runbook](Runbook)."


def test_ancora_com_hifen_duplo_atravessa_sem_ser_recalculada():
    """O caso que já mordeu uma vez: "Passo 8 — Conferência, antes do e-mail"
    vira, pela regra do GitHub, `passo-8--conferência-antes-do-e-mail` — hífen
    duplo, porque o travessão some e sobram as duas espaços ao redor dele. Um
    recalculo "arrumadinho", que colapsa espaços repetidos antes de virar
    hífen, produziria `passo-8-conferência-antes-do-e-mail` — hífen simples,
    parece certo, não bate com página alguma."""
    origem = "[Passo 8](03-runbook.md#passo-8--conferência-antes-do-e-mail)."
    esperado = "[Passo 8](Runbook#passo-8--conferência-antes-do-e-mail)."
    assert _reescreve_links(origem, _PAGINAS) == esperado


def test_uma_reescrita_que_colapsasse_o_hifen_duplo_seria_pega():
    """Prova que o teste acima de fato distingue os dois resultados: se a
    implementação algum dia "normalizar" a âncora, colapsando o hífen duplo,
    o resultado passa a ser outro texto — e o `assert` de cima, que compara
    string exata, fica vermelho."""
    origem = "[Passo 8](03-runbook.md#passo-8--conferência-antes-do-e-mail)."
    hifen_simples = "[Passo 8](Runbook#passo-8-conferência-antes-do-e-mail)."
    assert _reescreve_links(origem, _PAGINAS) != hifen_simples


def test_link_para_ancora_da_propria_pagina_nao_e_tocado():
    texto = "Veja [mais abaixo](#o-project-do-claude)."
    assert _reescreve_links(texto, _PAGINAS) == texto


def test_link_para_fora_do_manual_nao_e_tocado():
    """`../../README.md` sai do manual e vai para a raiz do repositório — não
    é página do wiki, e reescrevê-lo produziria um link que não existe ali."""
    texto = "Ver [`README.md`](../../README.md) da raiz."
    assert _reescreve_links(texto, _PAGINAS) == texto


def test_url_externa_nao_e_tocada():
    texto = "Baixar de [git-scm.com](https://git-scm.com/download/win)."
    assert _reescreve_links(texto, _PAGINAS) == texto


def test_link_para_pagina_desconhecida_do_manual_e_erro():
    """Um link para um `.md` do manual que não bate com página alguma vira,
    no wiki, uma página vazia que o leitor cria sem querer ao clicar — por
    isso é erro na montagem, não um link que atravessa quieto."""
    texto = "Veja [um passo que não existe](06-inexistente.md)."
    with pytest.raises(ValueError, match="06-inexistente.md"):
        _reescreve_links(texto, _PAGINAS)


def test_todo_link_entre_paginas_do_manual_de_verdade_sobrevive_a_montagem():
    """Ensaio de ponta a ponta com o manual real: cada uma das seis páginas,
    reescrita com o mapeamento de verdade, não pode disparar o erro acima. Se
    disparasse, seria uma página nova com link para outra que `_nome_no_wiki`
    não sabe nomear — o que os testes de unidade, isolados por página, não
    veem."""
    paginas = {
        fonte.name: wiki.Path(_nome_no_wiki(fonte)).stem
        for fonte in sorted(wiki.MANUAL.glob("*.md"))
    }
    for fonte in sorted(wiki.MANUAL.glob("*.md")):
        _reescreve_links(fonte.read_text(encoding="utf-8"), paginas)


def test_monta_escreve_as_seis_paginas_com_faixa_e_sha(tmp_path):
    """`monta()` é a única peça que toca disco, e o único jeito de testá-la
    sem repositório de wiki algum é apontar `destino` para uma pasta comum —
    ela não sabe, nem precisa saber, que normalmente esse destino é um clone
    git."""
    sha = "abc1234"
    escritas = wiki.monta(tmp_path, sha)

    nomes = {caminho.name for caminho in escritas}
    assert nomes == {
        "Home.md", "Primeiro-dia.md", "Instalacao.md",
        "Runbook.md", "Decisoes.md", "Quando-da-errado.md",
    }
    for caminho in escritas:
        conteudo = caminho.read_text(encoding="utf-8")
        assert conteudo.startswith("> Gerado a partir de `docs/plantao/")
        assert sha in conteudo.splitlines()[0]


def test_monta_com_sha_diferente_muda_a_primeira_linha(tmp_path):
    """Prova que o teste acima de fato olha o SHA, e não só a presença de
    alguma faixa: SHAs diferentes produzem primeiras linhas diferentes."""
    wiki.monta(tmp_path, "1111111")
    linha_um = (tmp_path / "Home.md").read_text(encoding="utf-8").splitlines()[0]
    wiki.monta(tmp_path, "2222222")
    linha_dois = (tmp_path / "Home.md").read_text(encoding="utf-8").splitlines()[0]
    assert linha_um != linha_dois
