"""Estilo COPOM dos gráficos dos informes.

Cópia do subconjunto de `classes.config` do py-bcb que os informes usam, feita
para que rodem sem o py-bcb no sys.path. As cópias podem divergir.
"""

import locale
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from fontTools.ttLib import TTFont
from matplotlib import font_manager

from reports import _paths

DPI: int = 96  # Resolução padrão de tela (para impressão usar 150-300)
FIGSIZE: tuple[float, float] = (19.2, 8)
FONT: str = "calibri"
FONT_CACHE_DIR: Path = _paths.OUTPUT / "fonts"
LOCALE_BR: str = "pt_BR.UTF-8"

DEFAULT_STYLE: dict[str, Any] = {
    "font.family": "sans-serif",
    "font.sans-serif": [FONT],
    "font.size": 14,
    "axes.titlesize": 18,
    "axes.labelsize": 14,
    "legend.fontsize": 12,
    "lines.linewidth": 3,
}

COPOM: list[str] = [
    "#2E4C59",
    "#F2B557",
    "#6BAEBF",
    "#804C29",
    "#87007C",
    "#D46C6B",
    "#088492",
    "#D295BE",
    "#ECCAB1",
    "#AEAEAE",
    "#736063",
    "#C3A061",
]


def outline_font(family: str, cache_dir: Path = FONT_CACHE_DIR) -> str | None:
    """Registra no matplotlib cópias da fonte sem bitmaps embutidos; devolve o novo nome.

    A Calibri embute bitmaps para alguns tamanhos em pixels (ppem 12, 13, 15, 16, 17 e
    19) e o matplotlib 3.11 desenha esses bitmaps em branco: o texto some só nesses
    tamanhos. A cópia, só com contornos, chama-se "<família> Outline" e fica em
    `cache_dir`. Devolve None se a fonte não está instalada ou não tem bitmaps.
    """
    registered = {entry.fname for entry in font_manager.fontManager.ttflist}
    faces = sorted(
        {e.fname for e in font_manager.fontManager.ttflist if e.name.lower() == family.lower()}
    )
    new_family = None
    for fname in faces:
        font = TTFont(fname)
        if "EBLC" not in font:
            continue
        new_family = f"{font['name'].getDebugName(1)} Outline"
        out = Path(cache_dir) / f"{Path(fname).stem}_outline.ttf"
        if not out.exists():
            for tag in ("EBDT", "EBLC"):
                del font[tag]
            # Nome novo: com o mesmo nome, o matplotlib continuaria escolhendo a original
            for record in font["name"].names:
                if record.nameID in (1, 16):
                    record.string = new_family
            out.parent.mkdir(parents=True, exist_ok=True)
            font.save(out)
        if str(out) not in registered:
            font_manager.fontManager.addfont(str(out))
    return new_family


def apply_style() -> None:
    """Aplica o estilo padrão do COPOM aos gráficos matplotlib."""
    plt.rcParams.update(DEFAULT_STYLE)
    outline = outline_font(FONT)
    if outline is not None:
        plt.rcParams["font.sans-serif"] = [outline, FONT]
    plt.rcParams["figure.figsize"] = FIGSIZE
    plt.rcParams["figure.dpi"] = DPI
    try:
        locale.setlocale(locale.LC_TIME, LOCALE_BR)
    except locale.Error:
        pass  # Fallback se locale não estiver disponível


def plot_config(n_colors: int = 6) -> None:
    """Configura estilo de gráfico com n cores da paleta COPOM."""
    apply_style()
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=COPOM[:n_colors])


def clean_axes(ax) -> None:
    """Remove spines superiores e direitos do eixo."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
