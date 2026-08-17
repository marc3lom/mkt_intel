"""Figure persistence — the single, guarded path to disk.

Saving is allowed ONLY inside the caller-supplied ``allowed_root``. Everything
else in the codebase returns figures for inline display and never writes.
"""

import logging
from pathlib import Path

from matplotlib.figure import Figure

from comentario_matinal.render.estilo import SAVE_KWARGS

logger = logging.getLogger("comentario_matinal")


def save_figure(
    fig: Figure,
    save_path: Path | str,
    allowed_root: Path | str,
) -> Path:
    """Save ``fig`` to ``save_path``, which MUST resolve inside ``allowed_root``.

    ``allowed_root`` is required: this layer draws, it doesn't know where the
    embedding project's output tree lives, so every caller must say so
    explicitly. The guard itself stays in force regardless, so the "never
    write outside a declared output tree" policy travels with the code
    instead of being tied to one checkout.

    Creates the parent directory lazily. Returns the resolved path.
    Raises ValueError if the target is outside the allowed root.
    """
    resolved = Path(save_path).expanduser().resolve()
    root = Path(allowed_root).expanduser().resolve()
    if root not in resolved.parents:
        raise ValueError(
            f"Refusing to save outside the allowed output directory "
            f"({root}): {resolved}"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(resolved, **SAVE_KWARGS)
    logger.info("Figure saved to: %s", resolved)
    return resolved
