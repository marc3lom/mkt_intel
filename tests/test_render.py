"""Tests for inline-first render behavior."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.painel import monta_painel
from comentario_matinal.render.tabelas import (
    ESPEC_BC,
    ESPEC_ECO,
    monta_tabela,
    monta_tabelas,
)


def test_render_table_no_save_returns_figure_and_writes_nothing(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.tabelas.grava_figura",
        lambda *a, **k: chamadas.append(a),
    )
    df = pd.DataFrame({"PAÍS": ["US"]})  # _prepare_dataframe fills the rest
    fig = monta_tabela(df, ESPEC_ECO)
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_render_table_empty_returns_none():
    fig = monta_tabela(pd.DataFrame(), ESPEC_ECO)
    assert fig is None


def test_render_table_saves_when_path_given(tmp_path):
    df = pd.DataFrame({"PAÍS": ["US"]})
    target = tmp_path / "test_render_table.png"
    fig = monta_tabela(df, ESPEC_ECO, save_path=target, allowed_root=tmp_path)
    try:
        assert isinstance(fig, Figure)
        assert target.exists()
    finally:
        plt.close(fig)


def test_render_combined_no_save_returns_figure_and_writes_nothing(monkeypatch):
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


def test_render_combined_all_empty_returns_none():
    tables = [
        (pd.DataFrame(), ESPEC_ECO),
        (pd.DataFrame(), ESPEC_BC),
    ]
    assert monta_tabelas(tables) is None


def test_render_combined_saves_when_path_given(tmp_path):
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
