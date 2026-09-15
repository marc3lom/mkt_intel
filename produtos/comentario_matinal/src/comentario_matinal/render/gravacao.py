"""Persistência de figura — o único caminho, guardado, até o disco.

Gravar só é permitido dentro do ``allowed_root`` informado pelo chamador. Todo
o resto do código devolve figuras para exibição inline e nunca escreve.
"""

import logging
from pathlib import Path

from matplotlib.figure import Figure

from comentario_matinal.render.estilo import SAVE_KWARGS

logger = logging.getLogger("comentario_matinal")


def grava_figura(
    fig: Figure,
    save_path: Path | str,
    allowed_root: Path | str,
) -> Path:
    """Grava ``fig`` em ``save_path``, que PRECISA resolver dentro de ``allowed_root``.

    ``allowed_root`` é obrigatório: esta camada desenha, não sabe onde fica a
    árvore de saída do projeto que a incorpora, então todo chamador precisa
    dizê-lo explicitamente. A guarda continua valendo de qualquer forma, para
    que a política de "nunca gravar fora de uma árvore de saída declarada"
    viaje com o código em vez de ficar presa a um checkout.

    Cria o diretório pai sob demanda. Retorna o caminho resolvido.
    Levanta ValueError se o destino estiver fora da raiz permitida.
    """
    resolved = Path(save_path).expanduser().resolve()
    root = Path(allowed_root).expanduser().resolve()
    if root not in resolved.parents:
        raise ValueError(
            f"Recusando gravar fora do diretório de saída permitido "
            f"({root}): {resolved}"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(resolved, **SAVE_KWARGS)
    logger.info("Figura gravada em: %s", resolved)
    return resolved
