"""Âncora única de caminhos do `reports`.

Todo caminho de trabalho sai daqui. Os módulos leem `_paths.NOME` na hora da
chamada, nunca `from reports._paths import NOME`: é o que deixa um teste trocar
a pasta por uma temporária. `tests/test_paths.py` prende o arranjo.
"""

from pathlib import Path

# src/reports/_paths.py → parents[2] é o topo do repositório.
ROOT: Path = Path(__file__).resolve().parents[2]
PRODUCT: str = "informes_eventos"

INPUT: Path = ROOT / "input" / PRODUCT
OUTPUT: Path = ROOT / "output" / PRODUCT
# Documentos do Fed (committee_meeting_docs/) e planilhas de e-mail (email_info/).
FED_DOCS: Path = INPUT / "fed"
PROMPTS: Path = ROOT / "prompts" / PRODUCT
# Segredos locais (a chave do FRED), um arquivo por máquina, fora do git. Cada
# um administra o seu; o formato está em etc/env.exemplo.
ENV_FILE: Path = ROOT / "etc" / ".env"
