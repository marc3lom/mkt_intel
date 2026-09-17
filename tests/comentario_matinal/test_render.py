"""A renderização devolve figura por padrão e só toca o disco sob pedido."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from comentario_matinal.render.gravacao import grava_figura
from comentario_matinal.render.painel import monta_painel
from comentario_matinal.render.tabelas import (
    ESPEC_BC,
    ESPEC_ECO,
    LARGURA_UTIL,
    _compute_x_positions,
    monta_tabelas,
)


@pytest.mark.parametrize("espec", [ESPEC_ECO, ESPEC_BC], ids=["eco", "bc"])
def test_colunas_cabem_dentro_da_faixa(espec):
    """A última coluna não pode passar da faixa desenhada atrás das linhas.

    A faixa vai de 0,01 a 0,99 e as colunas começam em 0,02. Uma soma de
    larguras maior que LARGURA_UTIL empurra a última coluna para fora do eixo, e
    o cabeçalho dela — centralizado — sai cortado na borda direita. O sintoma
    aparece só na imagem, que nenhum outro teste olha.
    """
    assert len(espec.col_widths) == len(espec.columns), (
        f"{espec.title}: {len(espec.col_widths)} larguras para "
        f"{len(espec.columns)} colunas."
    )
    assert sum(espec.col_widths) == pytest.approx(LARGURA_UTIL), (
        f"{espec.title}: as larguras somam {sum(espec.col_widths):.3f}, "
        f"e precisam somar {LARGURA_UTIL}."
    )
    fim = _compute_x_positions(espec.col_widths)[-1] + espec.col_widths[-1]
    assert fim <= 0.99, f"{espec.title}: a última coluna termina em {fim:.3f}."


def test_tabelas_combinadas_sem_caminho_devolvem_figura_e_nao_gravam(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.tabelas.grava_figura",
        lambda *a, **k: chamadas.append(a),
    )
    tables = [
        (pd.DataFrame({"PAÍS": ["US"]}), ESPEC_ECO),
        (pd.DataFrame({"PAÍS": ["BR"]}), ESPEC_BC),
    ]
    fig = monta_tabelas(tables)
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_tabelas_combinadas_todas_vazias_devolvem_none():
    tables = [
        (pd.DataFrame(), ESPEC_ECO),
        (pd.DataFrame(), ESPEC_BC),
    ]
    assert monta_tabelas(tables) is None


def test_tabelas_combinadas_gravam_quando_recebem_caminho(tmp_path):
    tables = [
        (pd.DataFrame({"PAÍS": ["US"]}), ESPEC_ECO),
        (pd.DataFrame({"PAÍS": ["BR"]}), ESPEC_BC),
    ]
    target = tmp_path / "test_render_combined.png"
    fig = monta_tabelas(tables, save_path=target, allowed_root=tmp_path)
    try:
        assert isinstance(fig, Figure)
        assert target.exists()
    finally:
        plt.close(fig)


def _itens_minimos():
    from comentario_matinal.render.ativos import ItemDaGrade

    return [ItemDaGrade("AA Index", "aa", "Taxa 10a", "rate")]


def test_monitor_sem_save_devolve_figura_e_nao_grava(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.painel.grava_figura",
        lambda *a, **k: chamadas.append(a),
    )
    fig, _ = monta_painel(_itens_minimos(), pd.DataFrame(), {}, grid=(1, 1))
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_monitor_grava_quando_recebe_caminho(tmp_path):
    alvo = tmp_path / "painel.png"
    fig, _ = monta_painel(
        _itens_minimos(),
        pd.DataFrame(),
        {},
        save_path=alvo,
        allowed_root=tmp_path,
        grid=(1, 1),
    )
    try:
        assert alvo.exists()
    finally:
        plt.close(fig)


def test_monitor_recusa_caminho_sem_raiz_permitida(tmp_path):
    """Pedir gravação sem dizer onde é erro do chamador, e a mensagem diz qual."""
    with pytest.raises(ValueError, match="allowed_root"):
        monta_painel(
            _itens_minimos(), pd.DataFrame(), {},
            save_path=tmp_path / "painel.png", grid=(1, 1),
        )


def test_monitor_recusa_selo_inexistente(tmp_path):
    """Selo informado e ausente sairia como painel sem carimbo, sem aviso nenhum."""
    ausente = tmp_path / "nao_existe.png"
    with pytest.raises(FileNotFoundError, match="nao_existe.png"):
        monta_painel(
            _itens_minimos(), pd.DataFrame(), {},
            grid=(1, 1), selo_fechado=ausente,
        )


# --- a guarda de gravação ---------------------------------------------------


def test_grava_figura_escreve_dentro_da_raiz_permitida(tmp_path):
    fig = plt.figure()
    try:
        alvo = tmp_path / "sub" / "figura.png"
        gravado = grava_figura(fig, alvo, allowed_root=tmp_path)
        assert gravado == alvo.resolve()
        assert alvo.exists() and alvo.stat().st_size > 0
    finally:
        plt.close(fig)


def test_grava_figura_recusa_destino_fora_da_raiz(tmp_path):
    """A razão de existir do módulo: nada é escrito fora da árvore declarada.

    O caminho abaixo passa por dentro da raiz permitida e sobe de novo com "..",
    que é como um destino montado por concatenação escapa sem parecer que
    escapou. Quem resolve isso é o ``resolve()``, e a checagem tem de vir depois
    dele — daí o teste usar essa forma, e não um caminho obviamente externo.
    """
    raiz = tmp_path / "saida"
    raiz.mkdir()
    fora = raiz / ".." / "vizinho.png"
    fig = plt.figure()
    try:
        with pytest.raises(ValueError, match="Recusando gravar"):
            grava_figura(fig, fora, allowed_root=raiz)
        assert not (tmp_path / "vizinho.png").exists()
    finally:
        plt.close(fig)
