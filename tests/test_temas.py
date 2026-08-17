"""A escolha de temas parte dos números da triagem.

A triagem entrega uma tabela numerada; reescrever a descrição à mão é
transcrição, e transcrição erra. O que o autor acrescenta de seu não é a lista —
é a ressalva dentro do marcador, e essa continua sendo texto que ele escreve.
"""

import pytest

from comentario_matinal import plantao

TABELA = """\
### A) TEMAS CANDIDATOS

| # | Tema | Movimento observado | Relevância |
|---|------|---------------------|------------|
| 1 | Venda nos vencimentos longos de Treasuries | Treasury 10a em alta | Alta |
| 2 | Recrudescimento do conflito no Oriente Médio | Brent em alta | Alta |
| 3 | Precificação de política monetária do Fed | Não coberto | Alta |

### B) TEMA DOMINANTE PROPOSTO

Tema 1 — venda nos vencimentos longos.
"""


@pytest.fixture
def ctx(tmp_path):
    c = plantao.contexto(asof="2026-08-18T07:40", saida=tmp_path)
    (tmp_path / f"triagem_{c.marca}.md").write_text(TABELA, encoding="utf-8")
    return c


def test_os_numeros_viram_marcadores_na_ordem_pedida(ctx):
    """A ordem é a do autor, não a da tabela: o primeiro é o tema dominante."""
    assert plantao.temas_da_triagem(ctx, [3, 1]) == (
        "- Precificação de política monetária do Fed\n"
        "- Venda nos vencimentos longos de Treasuries\n"
    )


def test_numero_fora_da_tabela_falha_nomeando_o_numero(ctx):
    with pytest.raises(plantao.FaltaInsumo, match="9"):
        plantao.temas_da_triagem(ctx, [1, 9])


def test_sem_triagem_manda_rodar_a_etapa_anterior(tmp_path):
    c = plantao.contexto(asof="2026-08-18T07:40", saida=tmp_path)
    with pytest.raises(plantao.FaltaInsumo) as erro:
        plantao.temas_da_triagem(c, [1])
    assert erro.value.remedio == plantao.TRIAGEM_AUSENTE


def test_tabela_ilegivel_manda_escrever_a_mao(ctx):
    """O modelo já desobedeceu formato uma vez — o `partes_da_redacao` existe por isso.

    Devolver lista vazia em silêncio seria o pior resultado possível: a redação
    rodaria sem tema nenhum, e o autor descobriria isso lendo o comentário.
    """
    (ctx.saida / f"triagem_{ctx.marca}.md").write_text(
        "### A) TEMAS CANDIDATOS\n\nsem tabela alguma.\n", encoding="utf-8")

    with pytest.raises(plantao.FaltaInsumo) as erro:
        plantao.temas_da_triagem(ctx, [1])
    assert erro.value.remedio == plantao.TRIAGEM_ILEGIVEL
