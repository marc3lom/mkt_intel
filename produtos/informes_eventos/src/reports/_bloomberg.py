"""Ponte assíncrona para o xbbg.

Cópia de `classes.functions.bloomberg._run_async` do py-bcb, feita para que os
informes rodem sem o py-bcb no sys.path. As cópias podem divergir: a daqui só
muda por necessidade dos informes.
"""

import asyncio


def run_async(coro):
    """Executa coroutine em qualquer contexto (sync ou async/Jupyter).

    xbbg 1.0 bloqueia chamadas sync (bdh, bdp, bdib) dentro de event loops.
    Esta função usa abdh/abdp/abdib (async) e garante execução em ambos
    os contextos.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Sem event loop ativo — pode usar asyncio.run()
        return asyncio.run(coro)

    # Dentro de event loop (Jupyter) — usar nest_asyncio
    import nest_asyncio

    nest_asyncio.apply()
    return loop.run_until_complete(coro)
