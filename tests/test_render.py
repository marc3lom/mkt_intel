"""Tests for inline-first render behavior."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.monitor import build_monitor_panel
from comentario_matinal.render.tables import (
    CB_TABLE_SPEC_COMBINED,
    ECO_TABLE_SPEC,
    render_combined_tables,
    render_table,
)


def test_render_table_no_save_returns_figure_and_writes_nothing(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.tables.save_figure",
        lambda *a, **k: chamadas.append(a),
    )
    df = pd.DataFrame({"PAÍS": ["US"]})  # _prepare_dataframe fills the rest
    fig = render_table(df, ECO_TABLE_SPEC)
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_render_table_empty_returns_none():
    fig = render_table(pd.DataFrame(), ECO_TABLE_SPEC)
    assert fig is None


def test_render_table_saves_when_path_given(tmp_path):
    df = pd.DataFrame({"PAÍS": ["US"]})
    target = tmp_path / "test_render_table.png"
    fig = render_table(df, ECO_TABLE_SPEC, save_path=target, allowed_root=tmp_path)
    try:
        assert isinstance(fig, Figure)
        assert target.exists()
    finally:
        plt.close(fig)


def test_render_combined_no_save_returns_figure_and_writes_nothing(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.tables.save_figure",
        lambda *a, **k: chamadas.append(a),
    )
    tables = [
        (pd.DataFrame({"PAÍS": ["US"]}), ECO_TABLE_SPEC),
        (pd.DataFrame({"PAÍS": ["BR"]}), CB_TABLE_SPEC_COMBINED),
    ]
    fig = render_combined_tables(tables)
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_render_combined_all_empty_returns_none():
    tables = [
        (pd.DataFrame(), ECO_TABLE_SPEC),
        (pd.DataFrame(), CB_TABLE_SPEC_COMBINED),
    ]
    assert render_combined_tables(tables) is None


def test_render_combined_saves_when_path_given(tmp_path):
    tables = [
        (pd.DataFrame({"PAÍS": ["US"]}), ECO_TABLE_SPEC),
        (pd.DataFrame({"PAÍS": ["BR"]}), CB_TABLE_SPEC_COMBINED),
    ]
    target = tmp_path / "test_render_combined.png"
    fig = render_combined_tables(tables, save_path=target, allowed_root=tmp_path)
    try:
        assert isinstance(fig, Figure)
        assert target.exists()
    finally:
        plt.close(fig)


def _itens_minimos():
    from comentario_matinal.render.tickers import TickerInfo

    return [TickerInfo("AA Index", "aa", "Taxa 10a", "rate")]


def test_monitor_sem_save_devolve_figura_e_nao_grava(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "comentario_matinal.render.monitor.save_figure",
        lambda *a, **k: chamadas.append(a),
    )
    fig, _ = build_monitor_panel(_itens_minimos(), pd.DataFrame(), {}, grid=(1, 1))
    try:
        assert isinstance(fig, Figure)
        assert chamadas == []
    finally:
        plt.close(fig)


def test_monitor_grava_quando_recebe_caminho(tmp_path):
    alvo = tmp_path / "painel.png"
    fig, _ = build_monitor_panel(
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
