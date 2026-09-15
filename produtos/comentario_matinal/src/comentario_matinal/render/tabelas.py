"""Motor genérico de renderização de tabelas, para PNGs no estilo calendário."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.render.estilo import CORES, FONTES
from comentario_matinal.render.gravacao import grava_figura

logger = logging.getLogger("comentario_matinal")


# ---------------------------------------------------------------------------
# Formatação de valor e ajudantes de destaque
# ---------------------------------------------------------------------------


def formata_valor(val) -> str:
    """Formata um valor para exibição na tabela."""
    if pd.isna(val):
        return "-"
    if isinstance(val, (int, float)):
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"
    return str(val)


def destaca_atual(row) -> bool:
    """Retorna True se ATUAL > ESTIMATIVA (destaque em verde)."""
    try:
        atual = row.get("ATUAL")
        estimativa = row.get("ESTIMATIVA")
        if pd.notna(atual) and pd.notna(estimativa):
            return float(atual) > float(estimativa)
    except (ValueError, TypeError):
        pass
    return False


def destaca_revisado(row) -> bool:
    """Retorna True se REVISADO != ANTERIOR (destaque em verde)."""
    try:
        revisado = row.get("REVISADO")
        anterior = row.get("ANTERIOR")
        if pd.notna(revisado) and revisado != "-":
            if pd.notna(anterior):
                return float(revisado) != float(anterior)
    except (ValueError, TypeError):
        pass
    return False


# ---------------------------------------------------------------------------
# EspecDeTabela e specs pré-montados
# ---------------------------------------------------------------------------


@dataclass
class EspecDeTabela:
    """Especificação de uma seção de tabela."""

    title: str
    columns: list[str]
    col_widths: list[float]
    highlight_rules: dict[str, Callable] = field(default_factory=dict)
    left_align_col: str | None = None


# As larguras somam LARGURA_UTIL, e não 1,0: as faixas de cabeçalho e de linha
# são desenhadas de 0,01 a 0,99, e as colunas começam em 0,02 (ver
# _compute_x_positions). Somando 1,0, a última coluna terminava em 1,02 — fora
# da faixa e fora do eixo —, e o cabeçalho REVISADO, que é centralizado nela,
# saía encostado na borda direita. O teste em tests/test_render.py trava a soma.
LARGURA_UTIL = 0.96

ESPEC_ECO = EspecDeTabela(
    title="CALENDÁRIO ECONÔMICO",
    columns=[
        "PAÍS", "DATA", "HORÁRIO", "EVENTO", "PERÍODO",
        "ESTIMATIVA", "ATUAL", "ANTERIOR", "REVISADO",
    ],
    # Os 0,04 que sobravam saíram das colunas numéricas e de PAÍS/DATA, que
    # tinham folga; EVENTO mantém 0,25 porque é onde o texto é mais longo.
    col_widths=[0.11, 0.09, 0.08, 0.25, 0.08, 0.09, 0.08, 0.09, 0.09],
    highlight_rules={
        "ATUAL": destaca_atual,
        "REVISADO": destaca_revisado,
    },
)

ESPEC_BC = EspecDeTabela(
    title="BANCOS CENTRAIS",
    columns=["PAÍS", "DATA", "HORÁRIO", "EVENTO"],
    col_widths=[0.12, 0.10, 0.08, 0.66],
    left_align_col="EVENTO",
)


# ---------------------------------------------------------------------------
# Ajudantes internos
# ---------------------------------------------------------------------------


def _prepare_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Garante que todas as colunas existam e formata datas."""
    for col in columns:
        if col not in df.columns:
            df[col] = "-"
    df = df[columns].copy()
    if "DATA" in df.columns:
        df["DATA"] = df["DATA"].apply(
            lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x)
        )
    return df


def _compute_x_positions(col_widths: list[float]) -> list[float]:
    """Calcula as posições x iniciais de cada coluna."""
    positions = [0.02]
    for w in col_widths[:-1]:
        positions.append(positions[-1] + w)
    return positions


# ---------------------------------------------------------------------------
# Renderização de tabelas combinadas (empilhadas)
# ---------------------------------------------------------------------------


def monta_tabelas(
    tables: list[tuple[pd.DataFrame, EspecDeTabela]],
    save_path: Path | None = None,
    fig_width: float = 14,
    allowed_root: Path | None = None,
) -> Figure | None:
    """Renderiza N tabelas empilhadas verticalmente numa única figura.

    Retorna a Figure para exibição inline. Só grava um PNG quando
    ``save_path`` é informado, e só dentro de ``allowed_root``, que
    ``grava_figura`` exige sempre que um PNG é de fato gravado.
    """
    # Sem a raiz permitida, gravar falharia com ``TypeError`` de ``Path(None)``
    # só no fim, depois de desenhar tudo.
    if save_path is not None and allowed_root is None:
        raise ValueError(
            "save_path foi informado sem allowed_root: gravar exige a raiz "
            "permitida de saída."
        )
    non_empty = [(df, spec) for df, spec in tables if not df.empty]
    if not non_empty:
        logger.warning("Todos os DataFrames vazios, não é possível renderizar a tabela combinada")
        return None

    prepared = [(_prepare_dataframe(df, spec.columns), spec) for df, spec in non_empty]

    # Constantes de dimensionamento (pixels)
    row_height_px = 28
    header_height_px = 35
    title_height_px = 45
    spacing_px = 30

    section_heights = []
    for df, _spec in prepared:
        h = title_height_px + header_height_px + len(df) * row_height_px
        section_heights.append(h)

    total_height_px = sum(section_heights) + spacing_px * (len(prepared) - 1) + 40
    fig_height = max(4, total_height_px / 80)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    total_content = sum(section_heights) + spacing_px * (len(prepared) - 1)
    current_y = 0.95

    for sec_idx, (df, spec) in enumerate(prepared):
        n_rows = len(df)
        section_ratio = section_heights[sec_idx] / total_content if total_content > 0 else 0.5
        row_height = 0.8 * section_ratio / (n_rows + 2)

        is_eco = len(spec.columns) > 4
        title_fs = FONTES["combined_title"]
        header_fs = FONTES["combined_header_eco"] if is_eco else FONTES["combined_header_cb"]
        cell_fs = FONTES["combined_cell_eco"] if is_eco else FONTES["combined_cell_cb"]

        x_positions = _compute_x_positions(spec.col_widths)

        # Título
        ax.text(
            0.5, current_y, spec.title,
            fontsize=title_fs, fontweight="bold", color=CORES["title"],
            ha="center", va="top", transform=ax.transAxes,
        )
        current_y -= row_height * 1.2

        # Cabeçalho
        header_rect = mpatches.FancyBboxPatch(
            (0.01, current_y - row_height), 0.98, row_height,
            boxstyle="round,pad=0.01", facecolor=CORES["header_bg"],
            edgecolor="none", transform=ax.transAxes,
        )
        ax.add_patch(header_rect)

        for i, col in enumerate(spec.columns):
            ax.text(
                x_positions[i] + spec.col_widths[i] / 2, current_y - row_height / 2,
                col, fontsize=header_fs, fontweight="bold",
                color=CORES["header_text"], ha="center", va="center",
                transform=ax.transAxes,
            )

        current_y -= row_height

        # Linhas de dado
        for row_idx, (_, row) in enumerate(df.iterrows()):
            y = current_y - row_height

            bg_color = CORES["row_odd"] if row_idx % 2 == 0 else CORES["row_even"]
            row_rect = mpatches.FancyBboxPatch(
                (0.01, y), 0.98, row_height,
                boxstyle="round,pad=0.01", facecolor=bg_color,
                edgecolor="none", transform=ax.transAxes,
            )
            ax.add_patch(row_rect)

            for col_idx, col in enumerate(spec.columns):
                value = formata_valor(row[col])

                text_color = CORES["text_normal"]
                if col in spec.highlight_rules and spec.highlight_rules[col](row):
                    text_color = CORES["text_positive"]

                if col == spec.left_align_col:
                    ha = "left"
                    x_offset = 0.01
                else:
                    ha = "center"
                    x_offset = spec.col_widths[col_idx] / 2

                ax.text(
                    x_positions[col_idx] + x_offset, y + row_height / 2,
                    value, fontsize=cell_fs, color=text_color,
                    ha=ha, va="center", transform=ax.transAxes,
                )

            current_y = y

        # Espaçamento entre seções
        if sec_idx < len(prepared) - 1:
            spacing_ratio = spacing_px / total_content if total_content > 0 else 0.05
            current_y -= spacing_ratio * 0.5

    plt.tight_layout()

    if save_path is not None:
        grava_figura(fig, save_path, allowed_root=allowed_root)

    return fig
