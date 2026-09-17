"""A âncora de caminhos do matinal é o `config.py`, e só ele.

Contar níveis de `__file__` em mais de um módulo quebra em silêncio quando uma
pasta muda de lugar: o caminho segue válido e aponta para onde não há nada.
"""

import re
from pathlib import Path

import comentario_matinal
from comentario_matinal import config

PACOTE = Path(comentario_matinal.__file__).resolve().parent


def test_a_raiz_e_o_topo_do_repositorio():
    assert (config.RAIZ / "pyproject.toml").is_file()
    assert (config.RAIZ / ".git").exists()


def test_o_que_e_versionado_existe():
    for caminho in (config.CONFIG_PADRAO, config.TEMPLATE_PADRAO,
                    config.MERCADO_FECHADO, config.GUIA_DE_ESTILO,
                    *config.PROMPT_ETAPA.values()):
        assert caminho.is_file(), caminho
    assert config.ARQUIVO_PADRAO.is_dir()
    assert config.MANUAL.is_dir()


def test_as_pastas_de_trabalho_ficam_dentro_do_repositorio():
    for caminho in (config.FONTES_PADRAO, config.SAIDA_PADRAO):
        assert caminho.is_relative_to(config.RAIZ), caminho


def test_so_o_config_le_dunder_file():
    culpados = sorted(
        str(f.relative_to(PACOTE))
        for f in PACOTE.rglob("*.py")
        if f.name != "config.py" and re.search(r"\b__file__\b", f.read_text(encoding="utf-8"))
    )
    assert culpados == []
