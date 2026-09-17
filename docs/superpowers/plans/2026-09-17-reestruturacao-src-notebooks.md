# Reestruturação `src/` + `notebooks/` — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o workspace uv de `produtos/<nome>/` por um projeto único com `src/`, `notebooks/`, pastas de recurso por tipo e `input/` + `output/` na raiz, sem mudar nome de import, comando ou comportamento do pipeline.

**Architecture:** Primeiro cada pacote ganha uma âncora única de caminhos, com a raiz do repositório como origem e uma variável temporária `_PRODUTO`/`_PRODUCT` apontando para a pasta antiga. Depois as pastas mudam de lugar por `git mv`, uma família por commit, e a cada mudança só a âncora é editada. A variável temporária morre na Task 6. O portão (`uv run pytest`) fica verde em todo commit.

**Tech Stack:** Python 3.14, uv 0.12 (`uv_build`), pytest 9 (`--import-mode=importlib`), ruff, nbformat, git.

**Spec:** `docs/superpowers/specs/2026-09-17-reestruturacao-src-notebooks-design.md`

## Global Constraints

- Só uv; nunca `pip install`. Python `>=3.14`. `blpapi` só pelo índice explícito da Bloomberg.
- Nomes de import não mudam: `comentario_matinal` e `reports`. Scripts `matinal` e `publica-wiki` não mudam.
- **Sigilo:** nunca ler, listar, imprimir, resumir ou comitar o conteúdo de `fontes/`, `saida/`, `input/`, `output/`, `etc/.env`, `src/reports/*/input/`. Essas pastas só são tocadas por `mv`/`git mv` do diretório inteiro. `test -d` é permitido; `ls` dentro delas, não.
- Antes de **todo** commit: `git status --porcelain` não mostra nada sob `input/`, `output/`, `fontes/`, `saida/`, nem `*.pdf`, `*.docx`, `*.xlsx`, `*.xlsm`, `.env`.
- Nunca rodar `uv run matinal` (nenhuma forma) nem executar notebook como verificação. Verificar é `uv run pytest`.
- Commit direto na `main`, **sem push**. Ao fim de cada Task: mostrar `git show --stat HEAD` e a mensagem ao usuário e esperar. Mensagem em português, terceira pessoa do presente, ≤72 caracteres, sem prefixo nem ponto final, corpo em prosa com o porquê; trailers `Co-Authored-By:` e `Claude-Session:`.
- Código do `comentario_matinal`: identificadores e comentários em português. Código do `reports`: identificadores em inglês, comentários e docstrings novas em pt-BR.
- Todo movimento de arquivo versionado é `git mv`. Nada de copiar e apagar.
- `reports` não importa `comentario_matinal` nem o contrário. `reports/_modelo.py` continua cópia.
- Contagens de partida: matinal 181 testes, informes 131. Cada Task diz quantos testes novos acrescenta; a contagem anunciada nos documentos do matinal acompanha.
- Comandos de shell abaixo são bash (Git Bash), rodados da raiz do repositório salvo indicação.

## Mapa de arquivos

| Arquivo | Responsabilidade | Tasks |
|---|---|---|
| `src/reports/_paths.py` (novo) | única âncora de caminhos do `reports` | 1, 3, 5, 6 |
| `src/comentario_matinal/config.py` | única âncora de caminhos do matinal | 1, 3, 5, 6 |
| `src/comentario_matinal/wiki.py` | deixa de calcular raiz; importa de `config` | 1, 5 |
| `reports/fomc/core/{drafting,data_loader,fed_scraper,pdf_parser,word_export,word_report}.py`, `reports/payroll/core/{data_loader,word_report}.py`, `reports/_style.py` | passam a ler `_paths` | 1 |
| `tests/informes_eventos/test_paths.py` (novo) | afere a âncora do `reports` | 1, 5, 6 |
| `tests/comentario_matinal/test_caminhos.py` (novo) | afere a âncora do matinal | 1, 5, 6 |
| `tests/informes_eventos/test_independence.py` | independência nas duas direções | 1, 3, 4 |
| `pyproject.toml` (raiz) | projeto único | 2, 3, 5 |
| `.gitignore` (raiz) | sigilo | 2, 6 |
| `scripts/migra_notebooks.py` (novo, apagado na Task 7) | tira o `sys.path` dos 5 notebooks | 4 |
| `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/**` | instruções e manual | 5, 6, 7 |

---

### Task 0: Pré-condições e linha de base

**Files:** nenhum arquivo muda.

- [ ] **Step 1: Árvore limpa**

Run: `git status --porcelain`
Expected: só `?? docs/` (a spec e este plano). Se aparecer ` M produtos/comentario_matinal/notebooks/imagens.ipynb`, **parar** e perguntar ao usuário se comita, guarda em stash ou descarta — não decidir por ele.

- [ ] **Step 2: Janela e calendário**

Conferir o relógio: fora de 7h00–9h00. Conferir que hoje não é dia de FOMC nem de payroll. Se for, parar.

- [ ] **Step 3: Portão de partida**

Run: `uv sync --all-packages && uv run --directory produtos/comentario_matinal pytest -q 2>&1 | tail -1 && uv run --directory produtos/informes_eventos pytest -q 2>&1 | tail -1`
Expected: `181 passed` e `131 passed`.

- [ ] **Step 4: Linha de base do ruff**

Run:
```bash
cd produtos/informes_eventos
uv run ruff check . > ../../.ruff-check-antes.txt 2>&1; uv run ruff format --check . > ../../.ruff-format-antes.txt 2>&1
cd ../..; tail -1 .ruff-check-antes.txt .ruff-format-antes.txt
```
Guardar as duas últimas linhas; a Task 5 compara. Os dois arquivos `.ruff-*-antes.txt` não são comitados e são apagados na Task 7.

- [ ] **Step 5: Comitar spec e plano** (só se o usuário pedir)

```bash
git add docs/superpowers
git commit -m "Registra a spec e o plano da reestruturação em src e notebooks"
```

---

### Task 1: Âncoras de caminho, sem mover nada

**Files:**
- Create: `produtos/informes_eventos/src/reports/_paths.py`
- Create: `produtos/informes_eventos/tests/test_paths.py`
- Create: `produtos/comentario_matinal/tests/test_caminhos.py`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/drafting.py:20-22,59-68`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/data_loader.py:104-106,115,145,303,426,516-518,591`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/fed_scraper.py:42-44,139,187,226,252`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/pdf_parser.py:577-579`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/word_export.py:56-59,72`
- Modify: `produtos/informes_eventos/src/reports/fomc/core/word_report.py:660-661`
- Modify: `produtos/informes_eventos/src/reports/payroll/core/word_report.py:188-189`
- Modify: `produtos/informes_eventos/src/reports/payroll/core/data_loader.py:11,19-21`
- Modify: `produtos/informes_eventos/src/reports/_style.py:18-19`
- Modify: `produtos/informes_eventos/tests/{test_drafting,test_reports_fomc,test_reports_payroll,test_independence}.py`
- Modify: `produtos/comentario_matinal/src/comentario_matinal/{config,wiki}.py`
- Modify: `produtos/comentario_matinal/tests/{test_notebook,test_documentacao}.py`

**Interfaces:**
- Produces `reports._paths`: `ROOT: Path` (topo do repositório), `INPUT`, `OUTPUT`, `FED_DOCS`, `PROMPTS`, `ENV_FILE` — todos `Path`. `FED_DOCS` é a pasta que contém `committee_meeting_docs/` e `email_info/`. Os módulos leem sempre `_paths.NOME` na hora da chamada (nunca `from reports._paths import NOME`), para que os testes troquem o valor com `monkeypatch.setattr(_paths, "OUTPUT", …)`.
- Produces `comentario_matinal.config`: `RAIZ: Path` passa a ser o **topo do repositório**; novo `MANUAL: Path`. As constantes existentes mantêm nome e valor.

- [ ] **Step 1: Teste de âncora do `reports` (falha)**

Criar `produtos/informes_eventos/tests/test_paths.py`:

```python
"""A âncora de caminhos do `reports` é uma só, e é aferida aqui.

Contar níveis de `__file__` em cada módulo quebra em silêncio quando uma pasta
muda de lugar: o caminho continua válido, só aponta para onde não há nada.
"""

import re
from pathlib import Path

from reports import _paths

PROMPT_FILES = ("00_guia_de_estilo.md", "01_resumo.md", "02_bancos.md", "03_revisao.md")
PACKAGE = Path(_paths.__file__).resolve().parent


def test_root_is_the_repository_top():
    assert (_paths.ROOT / "pyproject.toml").is_file()
    assert (_paths.ROOT / ".git").exists()


def test_prompts_exist():
    for name in PROMPT_FILES:
        assert (_paths.PROMPTS / name).is_file(), name


def test_working_paths_stay_inside_the_repository():
    for path in (_paths.INPUT, _paths.OUTPUT, _paths.FED_DOCS, _paths.ENV_FILE):
        assert path.is_relative_to(_paths.ROOT), path


def test_only_paths_module_reads_dunder_file():
    """Nenhum outro módulo acha pasta por conta própria."""
    offenders = sorted(
        str(f.relative_to(PACKAGE))
        for f in PACKAGE.rglob("*.py")
        if f.name != "_paths.py" and re.search(r"\b__file__\b", f.read_text(encoding="utf-8"))
    )
    assert offenders == []


def test_no_default_depends_on_cwd():
    """`Path("output/...")` cai onde o notebook foi aberto, não na raiz."""
    pattern = re.compile(r"""Path\(\s*["'](?:input|output)/""")
    offenders = sorted(
        str(f.relative_to(PACKAGE))
        for f in PACKAGE.rglob("*.py")
        if pattern.search(f.read_text(encoding="utf-8"))
    )
    assert offenders == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --directory produtos/informes_eventos pytest tests/test_paths.py -q`
Expected: erro de coleta, `ImportError: cannot import name '_paths' from 'reports'`.

- [ ] **Step 3: Criar `_paths.py`**

`produtos/informes_eventos/src/reports/_paths.py`:

```python
"""Âncora única de caminhos do `reports`.

Todo caminho de trabalho sai daqui. Os módulos leem `_paths.NOME` na hora da
chamada, nunca `from reports._paths import NOME`: é o que deixa um teste trocar
a pasta por uma temporária. `tests/test_paths.py` prende o arranjo.
"""

from pathlib import Path

# src/reports/_paths.py dentro de produtos/informes_eventos → parents[4] é o topo.
ROOT: Path = Path(__file__).resolve().parents[4]

# Temporário: a pasta do produto some ao fim da reestruturação.
_PRODUCT: Path = ROOT / "produtos" / "informes_eventos"

INPUT: Path = _PRODUCT / "input"
OUTPUT: Path = _PRODUCT / "output"
# Documentos do Fed (committee_meeting_docs/) e planilhas de e-mail (email_info/).
FED_DOCS: Path = Path(__file__).resolve().parent / "fomc" / "input"
PROMPTS: Path = _PRODUCT / "prompts"
ENV_FILE: Path = _PRODUCT / "etc" / ".env"
```

- [ ] **Step 4: `drafting.py`**

Trocar as linhas 20-22:

```python
# Raiz do produto: a pasta com o pyproject.toml. TestProjectRootAnchors prende.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROMPTS_DIR = PROJECT_ROOT / "prompts"
```

por:

```python
# Nome de módulo, e não leitura direta de `_paths`: os testes o trocam.
PROMPTS_DIR = _paths.PROMPTS
```

e o import `from reports import _modelo` por `from reports import _modelo, _paths`. Trocar os corpos:

```python
def day_folder(meeting_date: str) -> Path:
    """<input>/fomc/<AAAAMMDD>: headlines.txt, coletiva.txt, bancos/."""
    return _paths.INPUT / "fomc" / meeting_date


def output_folder(meeting_date: str) -> Path:
    """<output>/reports/fomc/<AAAAMMDD>, criada se não existir."""
    folder = _paths.OUTPUT / "reports" / "fomc" / meeting_date
    folder.mkdir(parents=True, exist_ok=True)
    return folder
```

- [ ] **Step 5: `data_loader.py`, `fed_scraper.py`, `pdf_parser.py` do FOMC**

Em `data_loader.py` e em `fed_scraper.py`: apagar a função `_get_module_path()` inteira; acrescentar `from reports import _paths` aos imports; trocar **toda** ocorrência de `_get_module_path() / "input"` por `_paths.FED_DOCS` (5 em `data_loader.py`, 4 em `fed_scraper.py`). Em `data_loader.py:518` trocar

```python
        grid_path = Path(__file__).parents[4] / "input" / "grid1.xlsx"
```
por
```python
        grid_path = _paths.INPUT / "grid1.xlsx"
```

Em `pdf_parser.py:577-579` trocar

```python
    from .data_loader import _get_module_path

    docs_path = _get_module_path() / "input" / "committee_meeting_docs"
```
por
```python
    from reports import _paths

    docs_path = _paths.FED_DOCS / "committee_meeting_docs"
```

Conferir: `grep -rn "_get_module_path" produtos/informes_eventos/src` → vazio.

- [ ] **Step 6: `word_export.py`, os dois `word_report.py`, `_style.py`, `payroll/core/data_loader.py`**

`fomc/core/word_export.py`: apagar `_get_project_root()`; importar `from reports import _paths`; em `get_word_export_path` trocar a linha do `output_dir` por `output_dir = _paths.OUTPUT / "reports" / "fomc"`.

`fomc/core/word_report.py:661`: `output_dir = Path("output/reports/fomc")` → `output_dir = _paths.OUTPUT / "reports" / "fomc"` (+ import).

`payroll/core/word_report.py:189`: `output_dir = Path("output/reports/payroll")` → `output_dir = _paths.OUTPUT / "reports" / "payroll"` (+ import).

`_style.py:18-19`:

```python
# src/reports/_style.py → parents[2] é a raiz do produto, como era a do py-bcb
FONT_CACHE_DIR: Path = Path(__file__).resolve().parents[2] / "output" / "fonts"
```
→
```python
FONT_CACHE_DIR: Path = _paths.OUTPUT / "fonts"
```
com `from reports import _paths` nos imports.

`payroll/core/data_loader.py`: apagar `import os` se não houver outro uso (`grep -n "os\." <arquivo>`), e trocar

```python
# Load environment variables from etc/.env
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "etc", ".env")
load_dotenv(_env_path)
```
por
```python
from reports import _paths

# A chave do FRED; o endereço do arquivo é de `_paths`.
load_dotenv(_paths.ENV_FILE)
```
(o `from reports import _paths` sobe para o bloco de imports).

Os dois defaults `Path("output/…")` dependiam do diretório em que o notebook foi aberto; passam a cair sempre na pasta de saída. É a única mudança de comportamento desta Task e é intencional.

- [ ] **Step 7: Ajustar os testes do informes que prendiam a contagem de níveis**

`tests/test_drafting.py`:
- importar `from reports import _paths`;
- linhas 42-46, corpo do teste:
```python
        assert drafting.day_folder("20260916") == _paths.INPUT / "fomc" / "20260916"
```
  (apagar o `assert (drafting.PROJECT_ROOT / "pyproject.toml").is_file()`; `test_paths.py` cobre);
- linhas 49 e 367: `monkeypatch.setattr(drafting, "PROJECT_ROOT", tmp_path)` → `monkeypatch.setattr(_paths, "OUTPUT", tmp_path / "output")`.

`tests/test_reports_fomc.py`: substituir a classe `TestProjectRootAnchors` inteira por

```python
class TestProjectRootAnchors:
    """Quem acha pasta é `reports._paths`; `tests/test_paths.py` o afere."""

    def test_word_export_writes_under_output(self, monkeypatch, tmp_path):
        from reports import _paths

        monkeypatch.setattr(_paths, "OUTPUT", tmp_path)
        assert word_export.get_word_export_path("x.png") == tmp_path / "reports" / "fomc" / "x.png"

    def test_drafting_prompts_come_from_paths(self):
        from reports import _paths
        from reports.fomc.core import drafting

        assert drafting.PROMPTS_DIR == _paths.PROMPTS
```

`tests/test_reports_payroll.py`: substituir `TestProjectRootAnchors` por

```python
class TestProjectRootAnchors:
    def test_env_file_comes_from_paths(self):
        """A chave do FRED é lida do arquivo que `_paths` aponta."""
        from reports import _paths

        assert _paths.ENV_FILE.name == ".env"
        assert not hasattr(data_loader, "_env_path")
```

- [ ] **Step 8: Independência nas duas direções**

Substituir `produtos/informes_eventos/tests/test_independence.py` por:

```python
"""Os pacotes do repositório não se importam, e nenhum importa o py-bcb.

Com os dois num `src/` só, a fronteira deixa de ser uma pasta e passa a ser
este arquivo. Os imports ficam dentro de funções, então nada quebraria no
import do pacote: quebraria na primeira chamada, no dia do informe.
"""

import re
from pathlib import Path

import comentario_matinal
import reports
from reports import _paths

REPORTS = Path(reports.__file__).resolve().parent
MATINAL = Path(comentario_matinal.__file__).resolve().parent
# Os notebooks do informes ainda moram dentro do pacote.
REPORTS_NOTEBOOKS = REPORTS
MATINAL_NOTEBOOKS = _paths.ROOT / "produtos" / "comentario_matinal" / "notebooks"


def _offenders(files: list[Path], module: str) -> list[str]:
    pattern = re.compile(rf"\b(from|import)\s+{module}\b")
    return sorted(str(f) for f in files if pattern.search(f.read_text(encoding="utf-8")))


def _sources(package: Path, notebooks: Path) -> list[Path]:
    files = [*package.rglob("*.py"), *notebooks.rglob("*.ipynb")]
    assert files
    return files


class TestNoPyBcbImports:
    def test_modules_and_notebooks(self):
        """Import de `classes` só resolve com o py-bcb no sys.path — e aqui ele não está."""
        assert _offenders(_sources(REPORTS, REPORTS_NOTEBOOKS), "classes") == []


class TestPackagesDoNotImportEachOther:
    def test_reports_does_not_import_comentario_matinal(self):
        """O backend do modelo é cópia, não import."""
        assert _offenders(_sources(REPORTS, REPORTS_NOTEBOOKS), "comentario_matinal") == []

    def test_comentario_matinal_does_not_import_reports(self):
        assert _offenders(_sources(MATINAL, MATINAL_NOTEBOOKS), "reports") == []
```

Saldo do informes nesta Task: `test_paths.py` +5; `TestProjectRootAnchors` do FOMC 4→2; independência 2→3. Total 131 → 135.

- [ ] **Step 9: Portão do informes**

Run: `uv run --directory produtos/informes_eventos pytest -q 2>&1 | tail -3`
Expected: `135 passed`.
Run: `cd produtos/informes_eventos && uv run ruff check . | tail -1 && uv run ruff format --check . | tail -1; cd ../..`
Expected: mesmas contagens do `.ruff-*-antes.txt`, ou menores. Se o `ruff format --check` acusar arquivo novo, rodar `uv run ruff format src/reports/_paths.py tests/test_paths.py tests/test_independence.py`.

- [ ] **Step 10: Teste de âncora do matinal (falha)**

Criar `produtos/comentario_matinal/tests/test_caminhos.py`:

```python
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
```

Run: `uv run --directory produtos/comentario_matinal pytest tests/test_caminhos.py -q`
Expected: FAIL — `test_a_raiz_e_o_topo_do_repositorio` (não há `.git` na pasta do produto), `AttributeError: MANUAL`, e `wiki.py` em `culpados`.

- [ ] **Step 11: `config.py` e `wiki.py`**

Em `config.py`, trocar o bloco que vai de `RAIZ = …` até `PROMPTS = RAIZ / "prompts"` por:

```python
# O topo do repositório. É a única conta de níveis do pacote; o
# `tests/test_caminhos.py` prende que nenhum outro módulo a repita.
RAIZ = Path(__file__).resolve().parents[4]

# Temporário: a pasta do produto some ao fim da reestruturação.
_PRODUTO = RAIZ / "produtos" / "comentario_matinal"

CONFIG_PADRAO = _PRODUTO / "config" / "painel.toml"
SAIDA_PADRAO = _PRODUTO / "saida"
TEMPLATE_PADRAO = _PRODUTO / "templates" / "comentario.dotx"
MERCADO_FECHADO = _PRODUTO / "templates" / "mercado_fechado.png"
FONTES_PADRAO = _PRODUTO / "fontes"
ARQUIVO_PADRAO = _PRODUTO / "arquivo"
MANUAL = _PRODUTO / "docs" / "plantao"
PROMPTS = _PRODUTO / "prompts"
```

Em `wiki.py`, trocar

```python
RAIZ = Path(__file__).resolve().parent.parent.parent
MANUAL = RAIZ / "docs" / "plantao"
```
por
```python
from comentario_matinal.config import MANUAL, RAIZ
```
(no bloco de imports), e o comentário + `DESTINO_PADRAO` por:

```python
# O clone do wiki fica ao lado do repositório, nunca dentro: é outro repositório
# git. `RAIZ` é o topo deste; o clone vai para a pasta que o contém.
DESTINO_PADRAO = RAIZ.parent / "mkt_intelligence.wiki"
```

Conferir outros usos de `RAIZ` no pacote: `grep -rn "RAIZ" produtos/comentario_matinal/src --include=*.py`. Só `config.py` e `wiki.py` (este usa `RAIZ` como `cwd` do git, o que continua certo no topo).

- [ ] **Step 12: Testes do matinal que achavam a pasta do produto**

`tests/test_notebook.py:15`: `CLI = RAIZ / "src" / "comentario_matinal" / "cli.py"` →

```python
from comentario_matinal import cli as _cli

CLI = Path(_cli.__file__)
```
(o import vai junto dos outros imports do arquivo; `RAIZ` e `NOTEBOOK` ficam como estão nesta Task).

`tests/test_documentacao.py`: nada muda nesta Task além da contagem (Step 13).

- [ ] **Step 13: Contagem anunciada**

`test_caminhos.py` acrescenta 4 testes: 181 → 185. Atualizar o número em `produtos/comentario_matinal/AGENTS.md` (tabela de comandos, "181 testes") e em `produtos/comentario_matinal/CLAUDE.md` ("181 testes"):

Run: `grep -rn "181" produtos/comentario_matinal/AGENTS.md produtos/comentario_matinal/CLAUDE.md produtos/comentario_matinal/README.md produtos/comentario_matinal/docs/plantao`
Trocar cada `181 testes` por `185 testes`.

- [ ] **Step 14: Portão do matinal**

Run: `uv run --directory produtos/comentario_matinal pytest -q 2>&1 | tail -3`
Expected: `185 passed`.

- [ ] **Step 15: Commit**

```bash
git status --porcelain   # conferência de sigilo das Global Constraints
git add produtos
git commit -m "Centraliza os caminhos de cada pacote numa âncora única"
```
Corpo: a reestruturação vai mudar pastas de lugar, e dez pontos do código achavam a raiz contando níveis de `__file__`; cada pacote passa a ter um módulo que faz essa conta, aferido por teste, e os dois defaults que dependiam do cwd do notebook deixam de depender.

---

### Task 2: Projeto único

**Files:**
- Modify: `pyproject.toml` (raiz)
- Create: `.python-version` (raiz)
- Delete: `produtos/comentario_matinal/pyproject.toml`, `produtos/informes_eventos/pyproject.toml`, `produtos/*/.python-version`
- Modify: `.gitignore` (raiz)
- Modify: `produtos/comentario_matinal/tests/test_documentacao.py:128,406-410`

**Interfaces:**
- Produces: `uv run pytest` na raiz roda as duas suítes; `uv sync` sem `--all-packages`.

- [ ] **Step 1: `.gitignore` primeiro — antes de qualquer pasta sair de `produtos/informes_eventos/`**

O `.gitignore` do informes ignora `input/` e `output/` só dentro da pasta dele. Acrescentar ao `.gitignore` da **raiz**, logo abaixo do bloco `fontes/`:

```gitignore
# Dados de trabalho dos informes. Sem âncora durante a reestruturação: vale em
# qualquer profundidade, inclusive para o input/ que mora dentro de src/reports/.
input/
output/
```

Run: `git check-ignore -q produtos/informes_eventos/src/reports/fomc/input && echo ok`
Expected: `ok`.

- [ ] **Step 2: `pyproject.toml` da raiz**

Substituir o arquivo inteiro por:

```toml
[project]
name = "mkt-intelligence"
version = "0.1.0"
description = "Disseminação de informação e inteligência de mercado da Mesa de Investimentos (DEPIN/DIRIN)"
readme = "README.md"
authors = [{ name = "Marcelo Martinelli", email = "mmartinelli@gmail.com" }]
requires-python = ">=3.14"
dependencies = [
    # Sem teto: os informes rodam no pandas 3, aferido pela caracterização, e o
    # comentário matinal anda junto.
    "pandas>=3.0",
    "numpy>=2.0",
    "matplotlib>=3.10",
    "xbbg>=1.4",
    "blpapi>=3.24",
    "python-docx>=1.2.0",
    # --- comentario_matinal ---
    "polars-bloomberg>=0.5.4",
    "pandas-market-calendars>=5.4.0",
    "pypdf>=6.16.1",
    "cryptography>=50.0.0",
    "pyarrow>=25.0.1",
    # --- reports (informes pós-evento) ---
    "fonttools>=4.0",  # _style.outline_font: Calibri sem bitmaps embutidos
    "pdfplumber>=0.11",
    "requests>=2.32",
    "openpyxl>=3.1.5",
    "fredapi>=0.5.2",
    "python-dotenv>=1.0",
    "nest-asyncio>=1.6",  # _bloomberg.run_async dentro do Jupyter
    "narwhals>=2.0",  # fomc.core.data_loader normaliza o retorno do abdib
]

[project.scripts]
matinal = "comentario_matinal.cli:main"
publica-wiki = "comentario_matinal.wiki:main"

[build-system]
requires = ["uv_build>=0.12.4,<0.13.0"]
build-backend = "uv_build"

# Dois pacotes, um projeto. Um não importa o outro: tests/…/test_independence.py.
[tool.uv.build-backend]
module-root = "produtos/comentario_matinal/src"
module-name = "comentario_matinal"

[dependency-groups]
dev = [
    "pytest>=9.1",
    "ruff>=0.16.4",
    "jupyter>=1.0.0",
    "ipykernel>=7.1",
    "nbformat>=5.10",
    "nbstripout>=0.9",
]

[tool.uv.sources]
blpapi = { index = "bloomberg" }

# blpapi não é publicado no PyPI. Explicit: nenhuma outra dependência sai daqui.
[[tool.uv.index]]
name = "bloomberg"
url = "https://blpapi.bloomberg.com/repository/releases/python/simple/"
explicit = true

# O lint é portão só do `reports`; o comentário matinal não tem portão de lint.
[tool.ruff]
line-length = 100
target-version = "py314"
include = ["produtos/informes_eventos/src/**/*.py", "produtos/informes_eventos/tests/**/*.py"]
extend-exclude = ["*.ipynb", ".venv", "build", "dist"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401", "F403", "I001"]
"**/tests/**/*.py" = ["F841"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["produtos/comentario_matinal/tests", "produtos/informes_eventos/tests"]
# importlib: há test_modelo.py nas duas suítes, e sem ele os nomes colidem.
addopts = "-ra --strict-markers --import-mode=importlib"
```

**Problema conhecido desta Task:** com os pacotes ainda em dois `src/` diferentes, o `uv_build` não tem um `module-root` que sirva aos dois. O bloco `[tool.uv.build-backend]` acima instala só o matinal, e o `reports` entra pelo `pythonpath` do pytest. Acrescentar, só nesta Task, ao `[tool.pytest.ini_options]`:

```toml
pythonpath = ["produtos/informes_eventos/src"]
```

A Task 3 junta os dois num `src/` e apaga essa linha.

- [ ] **Step 3: Apagar os manifestos dos produtos e criar o `.python-version` da raiz**

```bash
git rm produtos/comentario_matinal/pyproject.toml produtos/informes_eventos/pyproject.toml
git mv produtos/comentario_matinal/.python-version .python-version
git rm produtos/informes_eventos/.python-version
printf '3.14\n' > .python-version
```

- [ ] **Step 4: Relock e sync**

Run: `uv lock && uv sync`
Expected: sem erro de resolução; o `uv.lock` deixa de listar `comentario-matinal` e `informes-eventos` como membros e ganha `mkt-intelligence`. As versões de terceiros não mudam — conferir com `git diff --stat uv.lock` e, no diff, que nenhuma linha `version =` de pacote de terceiros mudou:
Run: `git diff uv.lock | grep '^[-+]version' | sort | uniq -c`
Expected: só as linhas dos três projetos locais.

- [ ] **Step 5: `test_documentacao.py` lê o `pyproject.toml` da raiz e conta só a suíte do matinal**

Linha 128, em `_executaveis_instalados`: `with (RAIZ / "pyproject.toml").open("rb") as arquivo:` →

```python
    from comentario_matinal.config import RAIZ as TOPO

    with (TOPO / "pyproject.toml").open("rb") as arquivo:
```

Em `test_a_contagem_de_testes_citada_bate_com_a_suite`, trocar a chamada do subprocesso por:

```python
        saida = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider", str(Path(__file__).parent)],
            capture_output=True, cwd=RAIZ, check=True, text=True,
        ).stdout
```

e acrescentar à docstring do teste: `A contagem é a desta suíte — a pasta deste arquivo —, não a do repositório: teste novo no outro pacote não envelhece este documento.`

- [ ] **Step 6: Portão na raiz**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `320 passed` (185 + 135).
Run: `uv run matinal --help > /dev/null && uv run publica-wiki --help > /dev/null && echo ok`
Expected: `ok`. (`--help` não toca a Bloomberg nem grava nada.)
Run: `uv run ruff check | tail -1; uv run ruff format --check | tail -1`
Expected: igual à linha de base.

- [ ] **Step 7: Commit**

```bash
git status --porcelain
git add -A pyproject.toml uv.lock .python-version .gitignore produtos
git commit -m "Troca o workspace uv por um projeto único na raiz"
```
Corpo: o lock já resolvia os dois produtos juntos e a fronteira de dependências era nominal; um projeto só tira a armadilha do `uv sync` sem `--all-packages`. O `pythonpath` do pytest é andaime e sai no commit seguinte.

---

### Task 3: `src/` na raiz

**Files:**
- Move: `produtos/comentario_matinal/src/comentario_matinal/` → `src/comentario_matinal/`
- Move: `produtos/informes_eventos/src/reports/` → `src/reports/`
- Modify: `pyproject.toml`, `src/reports/_paths.py:11`, `src/comentario_matinal/config.py`

**Interfaces:**
- Consumes: `_paths.ROOT`, `config.RAIZ` da Task 1.
- Produces: os dois pacotes instalados em modo editável a partir de `src/`.

- [ ] **Step 1: Mover**

`git mv` de diretório renomeia a pasta no disco, então o que é ignorado dentro dela (`src/reports/*/input/`, `__pycache__/`) vai junto. É o que se quer; o `.gitignore` da Task 2 já cobre.

```bash
mkdir src
git mv produtos/comentario_matinal/src/comentario_matinal src/comentario_matinal
git mv produtos/informes_eventos/src/reports src/reports
rmdir produtos/comentario_matinal/src produtos/informes_eventos/src
git check-ignore -q src/reports/fomc/input && echo ignorado
```
Expected: `ignorado`. Se `rmdir` reclamar de pasta não vazia, **não** usar `rm -rf`: rodar `ls -A` na pasta (ela não é sigilosa) e decidir pelo que aparecer.

- [ ] **Step 2: Âncoras**

`src/reports/_paths.py`: comentário e linha do `ROOT` →

```python
# src/reports/_paths.py → parents[2] é o topo do repositório.
ROOT: Path = Path(__file__).resolve().parents[2]
```

`src/comentario_matinal/config.py`: `RAIZ = Path(__file__).resolve().parents[4]` → `parents[2]`.

- [ ] **Step 3: `pyproject.toml`**

```toml
[tool.uv.build-backend]
module-root = "src"
module-name = ["comentario_matinal", "reports"]
```
Apagar a linha `pythonpath = [...]` do pytest. No `[tool.ruff]`:
```toml
include = ["src/reports/**/*.py", "produtos/informes_eventos/tests/**/*.py"]
```

- [ ] **Step 4: Sync**

Run: `uv sync`
Expected: sem erro. A instalação editável passa pelo mesmo backend, então é aqui que se descobre se o `uv_build` aceita a lista em `module-name`.

**Não rodar `uv build` nesta Task.** O `src/reports/*/input/` ainda está dentro do pacote, e um wheel copiaria material sigiloso para fora do repositório. A conferência do wheel é da Task 7, depois que o dado saiu de `src/`.

Se o `uv_build` recusar a lista: trocar o `[build-system]` por `requires = ["hatchling"]`, `build-backend = "hatchling.build"`, e o bloco `[tool.uv.build-backend]` por
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/comentario_matinal", "src/reports"]
```
e repetir o `uv sync`.

- [ ] **Step 5: `test_independence.py`**

Nada muda: `REPORTS_NOTEBOOKS = REPORTS` segue certo (os notebooks ainda estão no pacote) e `MATINAL_NOTEBOOKS` segue em `produtos/`.

- [ ] **Step 6: Portão**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `320 passed`.
Run: `uv run python -c "import reports, comentario_matinal, pathlib; print(pathlib.Path(reports.__file__).parent.parent.name, pathlib.Path(comentario_matinal.__file__).parent.parent.name)"`
Expected: `src src`.

- [ ] **Step 7: Commit**

```bash
git status --porcelain
git add -A pyproject.toml uv.lock src produtos
git commit -m "Leva os dois pacotes para o src da raiz"
```

---

### Task 4: `notebooks/` na raiz

**Files:**
- Move: `produtos/comentario_matinal/notebooks/*.ipynb` → `notebooks/comentario_matinal/`
- Move: `src/reports/fomc/notebooks/*.ipynb` → `notebooks/informes_eventos/fomc/`
- Move: `src/reports/payroll/notebooks/*.ipynb` → `notebooks/informes_eventos/payroll/`
- Create: `scripts/migra_notebooks.py`
- Modify: `produtos/comentario_matinal/tests/test_notebook.py:13-14,245,328`
- Modify: `produtos/informes_eventos/tests/test_reports_fomc.py:285`
- Modify: `produtos/informes_eventos/tests/test_independence.py`
- Create: `produtos/informes_eventos/tests/test_notebooks.py`

**Interfaces:**
- Consumes: `reports._paths.INPUT`, `reports._paths.OUTPUT`.
- Produces: nenhum notebook com `sys.path` nem `project_root`.

- [ ] **Step 1: Teste dos notebooks do informes (falha)**

Criar `produtos/informes_eventos/tests/test_notebooks.py`:

```python
"""Os notebooks são a interface do informe: importam o pacote instalado e
acham pasta por `reports._paths`, nunca pelo diretório em que foram abertos."""

import json

import pytest

from reports import _paths

NOTEBOOKS = sorted((_paths.ROOT / "notebooks" / "informes_eventos").rglob("*.ipynb"))


def _code(path) -> list[str]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_all_five_are_here():
    assert [p.name for p in NOTEBOOKS] == [
        "fomc_analysis.ipynb",
        "market_reaction_grid.ipynb",
        "market_reaction_grid.ipynb",
        "payroll_analysis.ipynb",
        "payroll_report.ipynb",
    ]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_path_hack_and_every_cell_compiles(path):
    for i, source in enumerate(_code(path)):
        assert "sys.path" not in source, f"cell {i}"
        assert "project_root" not in source, f"cell {i}"
        assert "Path.cwd()" not in source, f"cell {i}"
        # `%matplotlib inline` e afins não são Python.
        clean = "\n".join(l for l in source.splitlines() if not l.lstrip().startswith(("%", "!")))
        compile(clean, f"{path.name} cell {i}", "exec")
```

Run: `uv run pytest produtos/informes_eventos/tests/test_notebooks.py -q`
Expected: FAIL em `test_all_five_are_here` (lista vazia).

- [ ] **Step 2: Mover**

```bash
mkdir -p notebooks/informes_eventos
git mv produtos/comentario_matinal/notebooks notebooks/comentario_matinal
git mv src/reports/fomc/notebooks notebooks/informes_eventos/fomc
git mv src/reports/payroll/notebooks notebooks/informes_eventos/payroll
```

- [ ] **Step 3: Script que tira o `sys.path`**

Criar `scripts/migra_notebooks.py`. Ele edita só o `source` das células; saídas que existam na cópia de trabalho ficam como estão e **não são impressas**.

```python
"""Uso único: tira dos notebooks do informes o `sys.path` e o `project_root`.

Roda uma vez na reestruturação e é apagado no fim dela.
"""

import re
import sys
from pathlib import Path

import nbformat

ALVO = Path(__file__).resolve().parents[1] / "notebooks" / "informes_eventos"

LINHAS_FORA = (
    re.compile(r"^# Adiciona o diret[óo]rio raiz ao path\s*$"),
    re.compile(r"^project_root = Path\.cwd\(\)\.parents\[3\]\s*$"),
    re.compile(r"^if str\(project_root / 'src'\) not in sys\.path:\s*$"),
    re.compile(r"^\s+sys\.path\.insert\(0, str\(project_root / 'src'\)\)\s*$"),
)
IMPORT_NOVO = "from reports._paths import INPUT, OUTPUT"


def _migra(fonte: str, usa_sys_alhures: bool) -> str:
    linhas = [l for l in fonte.split("\n") if not any(r.match(l) for r in LINHAS_FORA)]
    if not usa_sys_alhures:
        linhas = [l for l in linhas if l.strip() != "import sys"]
    texto = "\n".join(linhas)
    texto = texto.replace("project_root / 'output'", "OUTPUT")
    texto = texto.replace("project_root / 'input'", "INPUT")
    return re.sub(r"\n{3,}", "\n\n", texto)


def main() -> int:
    for caminho in sorted(ALVO.rglob("*.ipynb")):
        nb = nbformat.read(caminho, as_version=nbformat.NO_CONVERT)
        codigo = [c for c in nb.cells if c.cell_type == "code"]
        resto = "\n".join(c.source for c in codigo)
        usa_sys = bool(re.search(r"\bsys\.(?!path\b)", resto))
        for celula in codigo:
            tinha = "project_root = Path.cwd()" in celula.source
            celula.source = _migra(celula.source, usa_sys)
            if tinha:
                celula.source = celula.source.replace(
                    "from pathlib import Path", f"from pathlib import Path\n\n{IMPORT_NOVO}", 1)
        if "project_root" in "\n".join(c.source for c in codigo):
            print(f"sobrou project_root em {caminho.name}", file=sys.stderr)
            return 1
        nbformat.write(nb, caminho)
        print(f"ok {caminho.relative_to(ALVO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `uv run python scripts/migra_notebooks.py`
Expected: cinco linhas `ok …`, código de saída 0. Se sair `sobrou project_root em X`, abrir só a célula acusada (o `source`, nunca o `outputs`) e acrescentar a substituição que faltou ao script — não editar o notebook à mão.

- [ ] **Step 4: Conferir o diff sem ver saída de célula**

Run: `git diff --stat -- notebooks/ && git diff -- notebooks/informes_eventos | grep '^[-+]' | grep -v '^[-+][-+]' | grep -ci '"outputs"\|"image/png"\|"text/plain"'`
Expected: a segunda conta é `0` — o diff só tem linhas de `source`. (O filtro `nbstripout` tira as saídas no `git add`; este passo confere que o script não as mexeu.)

- [ ] **Step 5: Testes que prendiam o endereço dos notebooks**

`produtos/informes_eventos/tests/test_reports_fomc.py:285`:

```python
    NB = Path(__file__).resolve().parents[1] / "src/reports/fomc/notebooks/fomc_analysis.ipynb"
```
→
```python
    NB = _paths.ROOT / "notebooks" / "informes_eventos" / "fomc" / "fomc_analysis.ipynb"
```
com `from reports import _paths` nos imports do arquivo.

`produtos/informes_eventos/tests/test_independence.py`: trocar as duas constantes por

```python
REPORTS_NOTEBOOKS = _paths.ROOT / "notebooks" / "informes_eventos"
MATINAL_NOTEBOOKS = _paths.ROOT / "notebooks" / "comentario_matinal"
```
e apagar o comentário `# Os notebooks do informes ainda moram dentro do pacote.`

`produtos/comentario_matinal/tests/test_notebook.py`:
- linhas 13-14:
```python
from comentario_matinal.config import RAIZ

NOTEBOOKS = RAIZ / "notebooks" / "comentario_matinal"
NOTEBOOK = NOTEBOOKS / "plantao.ipynb"
```
  (apagar o `RAIZ = Path(__file__).parent.parent`);
- linha 245: `caminho = RAIZ / "notebooks" / "imagens.ipynb"` → `caminho = NOTEBOOKS / "imagens.ipynb"`;
- linhas 325-329: o comentário sobre `:./caminho` e a chamada →
```python
        # `:caminho` resolve a partir do topo do repositório, que é onde os
        # notebooks moram agora.
        bruto = subprocess.run(
            ["git", "show", ":notebooks/comentario_matinal/plantao.ipynb"],
            capture_output=True, cwd=RAIZ, check=True,
        ).stdout.decode("utf-8")
```
- linha ~344, na mensagem do assert: `notebooks/plantao.ipynb` → `notebooks/comentario_matinal/plantao.ipynb`.

Run: `grep -n "RAIZ" produtos/comentario_matinal/tests/test_notebook.py` e conferir que todo uso restante faz sentido com `RAIZ` = topo.

- [ ] **Step 6: Portão**

Saldo: informes +6 (`test_all_five_are_here` + 5 parametrizados). Matinal não muda.
Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `326 passed`.

- [ ] **Step 7: Commit**

```bash
git status --porcelain
git add -A notebooks src produtos scripts
git commit -m "Reúne os notebooks na raiz e tira deles o sys.path"
```
Corpo: os cinco notebooks do informes moravam dentro do pacote e achavam o código por `Path.cwd().parents[3]`; com o projeto instalado em modo editável o import resolve sozinho, e as pastas de entrada e saída vêm de `reports._paths`.

---

### Task 5: Recursos versionados, testes e docs na raiz

**Files:**
- Move (matinal): `config/`, `prompts/`, `templates/`, `arquivo/`, `exemplos/`, `tests/`, `docs/`, `README.md`, `AGENTS.md`, `CLAUDE.md`
- Move (informes): `prompts/`, `tests/`, `docs/`, `README.md`, `AGENTS.md`, `etc/.env.tpl`
- Modify: `src/comentario_matinal/config.py`, `src/comentario_matinal/wiki.py:31`, `src/reports/_paths.py`, `pyproject.toml`
- Modify: `tests/comentario_matinal/{test_documentacao,test_wiki,test_caminhos}.py`, `tests/informes_eventos/test_paths.py`
- Modify: `docs/comentario_matinal/plantao/{README,01-primeiro-dia,02-instalacao}.md` (três links)

**Interfaces:**
- Produces: constantes finais de tudo o que é versionado. `_PRODUTO`/`_PRODUCT` sobrevivem só para `FONTES_PADRAO`, `SAIDA_PADRAO`, `INPUT`, `OUTPUT`, `ENV_FILE`.

- [ ] **Step 1: Mover**

```bash
mkdir -p config prompts templates arquivo exemplos tests
for d in config prompts templates arquivo exemplos tests; do
  git mv produtos/comentario_matinal/$d $d/comentario_matinal
done
git mv produtos/informes_eventos/prompts prompts/informes_eventos
git mv produtos/informes_eventos/tests tests/informes_eventos

# docs/ já existe na raiz (docs/superpowers).
git mv produtos/comentario_matinal/docs docs/comentario_matinal
git mv produtos/informes_eventos/docs docs/informes_eventos
for f in README.md AGENTS.md CLAUDE.md; do
  git mv produtos/comentario_matinal/$f docs/comentario_matinal/$f
done
git mv produtos/informes_eventos/README.md docs/informes_eventos/README.md
git mv produtos/informes_eventos/AGENTS.md docs/informes_eventos/AGENTS.md
git rm produtos/informes_eventos/CLAUDE.md
git mv produtos/informes_eventos/etc/.env.tpl .env.tpl
```

O `.gitignore` da raiz tem `.env.*`, que pegaria o template: acrescentar `!.env.tpl` logo abaixo de `!.env.example` **antes** do `git mv` acima, e conferir com `git check-ignore -q .env.tpl || echo versionavel`.

`.pytest_cache/` e `.ruff_cache/` ficam para trás em `produtos/`; a Task 7 cuida.

- [ ] **Step 2: `config.py`**

```python
RAIZ = Path(__file__).resolve().parents[2]
PRODUTO = "comentario_matinal"

# Temporário: as duas pastas de trabalho ainda não foram para input/ e output/.
_PRODUTO = RAIZ / "produtos" / PRODUTO

CONFIG_PADRAO = RAIZ / "config" / PRODUTO / "painel.toml"
SAIDA_PADRAO = _PRODUTO / "saida"
TEMPLATE_PADRAO = RAIZ / "templates" / PRODUTO / "comentario.dotx"
MERCADO_FECHADO = RAIZ / "templates" / PRODUTO / "mercado_fechado.png"
FONTES_PADRAO = _PRODUTO / "fontes"
ARQUIVO_PADRAO = RAIZ / "arquivo" / PRODUTO
MANUAL = RAIZ / "docs" / PRODUTO / "plantao"
PROMPTS = RAIZ / "prompts" / PRODUTO
```

- [ ] **Step 3: `_paths.py`**

```python
ROOT: Path = Path(__file__).resolve().parents[2]
PRODUCT: str = "informes_eventos"

# Temporário: input/ e output/ ainda não foram para a raiz.
_PRODUCT: Path = ROOT / "produtos" / PRODUCT

INPUT: Path = _PRODUCT / "input"
OUTPUT: Path = _PRODUCT / "output"
# Documentos do Fed (committee_meeting_docs/) e planilhas de e-mail (email_info/).
FED_DOCS: Path = Path(__file__).resolve().parent / "fomc" / "input"
PROMPTS: Path = ROOT / "prompts" / PRODUCT
ENV_FILE: Path = _PRODUCT / "etc" / ".env"
```

- [ ] **Step 4: `pyproject.toml`**

```toml
[tool.ruff]
include = ["src/reports/**/*.py", "tests/informes_eventos/**/*.py"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401", "F403", "I001"]
"tests/**/*.py" = ["F841"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
(`addopts` fica como está.) `readme = "README.md"` segue apontando para o da raiz.

- [ ] **Step 5: `wiki.py` e `test_wiki.py`**

`wiki.py`, constante `FAIXA`: `` "> Gerado a partir de `docs/plantao/{origem}` no commit `{sha}`.\n" `` → `` "> Gerado a partir de `docs/comentario_matinal/plantao/{origem}` no commit `{sha}`.\n" ``. Docstring do módulo: `docs/plantao/` → `docs/comentario_matinal/plantao/`.

`tests/comentario_matinal/test_wiki.py`:
- `assert conteudo.startswith("> Gerado a partir de `docs/plantao/")` → ``…`docs/comentario_matinal/plantao/")``;
- `assert "docs/plantao/03-runbook.md" in texto` → `"docs/comentario_matinal/plantao/03-runbook.md"`;
- em `test_link_para_fora_do_manual_nao_e_tocado`: o texto de exemplo e a docstring passam de `../../README.md` para `../README.md`.

- [ ] **Step 6: Os três links do manual para o README do produto**

Em `docs/comentario_matinal/plantao/README.md:17`, `01-primeiro-dia.md:71` e `02-instalacao.md:51`: `](../../README.md)` → `](../README.md)`. Conferir em `wiki.py` que `_reescreve_links` deixa passar o que começa com `../` — deixa (`destino.startswith(("../", "/", "#"))`).

Os links do `docs/comentario_matinal/README.md` para o manual (`docs/plantao/…`) passam a relativos à pasta nova: `](docs/plantao/` → `](plantao/` (linhas 3, 16, 111, 142).

- [ ] **Step 7: `test_documentacao.py`**

Cabeçalho (linhas 15-30):

```python
from comentario_matinal.config import MANUAL, PRODUTO, RAIZ

DOCS = RAIZ / "docs" / PRODUTO
# …(o comentário sobre os arquivos de agente fica)…
DOCUMENTOS = sorted(MANUAL.glob("*.md")) + [
    DOCS / "README.md",
    DOCS / "AGENTS.md",
    DOCS / "CLAUDE.md",
]

GUIA = RAIZ / "prompts" / PRODUTO / "00_guia_de_estilo.md"
```
Apagar `RAIZ = Path(__file__).parent.parent` e `MANUAL = RAIZ / "docs" / "plantao"`. Em `_executaveis_instalados` o `TOPO` da Task 2 vira `RAIZ`.

`_pastas_conhecidas`: `.name` de uma constante agora é `comentario_matinal`; o que a prosa cita é o primeiro nível a partir do topo. Trocar o bloco `declaradas = {…}` por:

```python
    def _primeiro_nivel(caminho: Path) -> str:
        return caminho.relative_to(RAIZ).parts[0]

    declaradas = {_primeiro_nivel(c) for c in (
        SAIDA_PADRAO, FONTES_PADRAO, ARQUIVO_PADRAO, PROMPTS,
        CONFIG_PADRAO, TEMPLATE_PADRAO,
    )}
```
Nesta Task `SAIDA_PADRAO` e `FONTES_PADRAO` ainda dão `produtos`; como a prosa ainda diz `saida/` e `fontes/`, acrescentar **temporariamente** a `CAMINHOS_QUE_SAO_MOLDE`:

```python
    "saida": "TEMPORÁRIO — sai na Task 6 da reestruturação, com a prosa",
    "fontes": "TEMPORÁRIO — sai na Task 6 da reestruturação, com a prosa",
```

`test_o_readme_aponta_para_o_manual`: `"docs/plantao/" in (RAIZ / "README.md")…` → `"plantao/" in (DOCS / "README.md")…`.

Todo `caminho.relative_to(RAIZ)` do arquivo continua válido (tudo está sob o topo).

- [ ] **Step 8: Testes de âncora**

`tests/comentario_matinal/test_caminhos.py` e `tests/informes_eventos/test_paths.py` não mudam de conteúdo. `tests/informes_eventos/test_notebooks.py` e `test_independence.py` também não.

- [ ] **Step 9: Portão e lint**

Run: `uv sync && uv run pytest -q 2>&1 | tail -3`
Expected: `326 passed`. Se `test_toda_pasta_citada_existe` ou `test_toda_ancora_do_manual_resolve` falhar, a mensagem nomeia arquivo e linha: corrigir a prosa apontada, não o teste.
Run: `uv run pytest tests/comentario_matinal -q | tail -1 && uv run pytest tests/informes_eventos -q | tail -1`
Expected: `185 passed`, `141 passed`.
Run: `uv run ruff check | tail -1; uv run ruff format --check | tail -1`
Expected: igual à linha de base da Task 0 (mais os arquivos novos, já formatados).

- [ ] **Step 10: Histórico preservado**

Run: `git log --follow --oneline -3 -- arquivo/comentario_matinal | head -3; git log --follow --oneline -3 -- src/reports/fomc/core/drafting.py | head -3`
Expected: commits anteriores à reestruturação nas duas listas (o `--follow` de diretório pode pedir um arquivo: usar o `.md` mais antigo de `arquivo/comentario_matinal/`, pelo nome, sem abri-lo).

- [ ] **Step 11: Commit**

```bash
git status --porcelain
git add -A
git status --porcelain | grep -i "input/\|output/\|fontes/\|saida/\|\.pdf\|\.docx\|\.xls\|\.env$" && echo "PARAR: material sigiloso no índice"
git commit -m "Distribui recursos, testes e docs por tipo na raiz"
```

---

### Task 6: `input/` e `output/`

**Files:**
- Disk only (fora do git): `produtos/comentario_matinal/{fontes,saida}`, `produtos/informes_eventos/{input,output,etc}`, `src/reports/{fomc,payroll}/input`
- Modify: `.gitignore`; Delete: `produtos/informes_eventos/.gitignore`
- Modify: `src/comentario_matinal/config.py`, `src/reports/_paths.py`
- Modify: `tests/comentario_matinal/{test_caminhos,test_documentacao,test_notebook}.py`, `tests/informes_eventos/test_paths.py`
- Modify (prosa): `docs/comentario_matinal/{AGENTS,README}.md`, `docs/comentario_matinal/plantao/*.md`, `docs/informes_eventos/AGENTS.md`, `notebooks/comentario_matinal/*.ipynb` (células markdown), docstrings e ajuda de `src/comentario_matinal/{cli,enviado,etapas}.py`

**Interfaces:**
- Produces: `config.FONTES_PADRAO = RAIZ/"input"/PRODUTO`, `config.SAIDA_PADRAO = RAIZ/"output"/PRODUTO`; `_paths.INPUT = ROOT/"input"/PRODUCT`, `_paths.OUTPUT = ROOT/"output"/PRODUCT`, `_paths.FED_DOCS = INPUT/"fed"`, `_paths.ENV_FILE = ROOT/".env"`. `_PRODUTO` e `_PRODUCT` deixam de existir.

- [ ] **Step 1: Testes de âncora finais (falham)**

Acrescentar a `tests/informes_eventos/test_paths.py`:

```python
def test_final_layout():
    assert _paths.INPUT == _paths.ROOT / "input" / "informes_eventos"
    assert _paths.OUTPUT == _paths.ROOT / "output" / "informes_eventos"
    assert _paths.FED_DOCS == _paths.INPUT / "fed"
    assert _paths.ENV_FILE == _paths.ROOT / ".env"
    assert not hasattr(_paths, "_PRODUCT")


def test_no_data_folder_inside_the_package():
    assert not any(p.name in {"input", "output"} for p in PACKAGE.rglob("*") if p.is_dir())
```

Acrescentar a `tests/comentario_matinal/test_caminhos.py`:

```python
def test_o_arranjo_final():
    assert config.FONTES_PADRAO == config.RAIZ / "input" / config.PRODUTO
    assert config.SAIDA_PADRAO == config.RAIZ / "output" / config.PRODUTO
    assert not hasattr(config, "_PRODUTO")
```

Run: `uv run pytest tests/informes_eventos/test_paths.py tests/comentario_matinal/test_caminhos.py -q | tail -3`
Expected: 3 falhas.

- [ ] **Step 2: `.gitignore` — trocar antes de mover**

Na raiz: apagar os blocos `saida/` e `fontes/` (com seus comentários) e o bloco temporário `input/` `output/` da Task 2; pôr no lugar:

```gitignore
# --- Entrada e saída do dia --------------------------------------------------
# Tudo o que entra (PDFs das fontes, documentos do Fed, planilhas de e-mail) e
# tudo o que sai (painel, calendário, etapas, .docx, gráficos). Ancoradas: só as
# duas pastas da raiz, inteiras, sem exceção. O registro versionado do que foi
# enviado é arquivo/, que não mora aqui de propósito.
/input/
/output/
```
```bash
git rm produtos/informes_eventos/.gitignore
```

- [ ] **Step 3: Mover no disco, sem ler**

Nenhum `ls`, `find`, `cat` ou `du` dentro dessas pastas. Só `test -d`, `mkdir`, `mv`, `rmdir`.

```bash
mkdir -p input output
mv produtos/comentario_matinal/fontes input/comentario_matinal
mv produtos/comentario_matinal/saida  output/comentario_matinal
mv produtos/informes_eventos/input    input/informes_eventos
mv produtos/informes_eventos/output   output/informes_eventos

test -e input/informes_eventos/fed     && echo "PARAR: fed já existe"
test -e input/informes_eventos/payroll && echo "PARAR: payroll já existe"
mv src/reports/fomc/input    input/informes_eventos/fed
mv src/reports/payroll/input input/informes_eventos/payroll

test -f produtos/informes_eventos/etc/.env && mv produtos/informes_eventos/etc/.env .env
rmdir produtos/informes_eventos/etc
```
Se qualquer `PARAR` aparecer, não sobrescrever: perguntar ao usuário. Se `rmdir etc` falhar, há arquivo além do `.env`: perguntar, não listar.

- [ ] **Step 4: Conferência de sigilo**

```bash
for p in input/comentario_matinal output/comentario_matinal input/informes_eventos/fed output/informes_eventos .env; do
  git check-ignore -q "$p" && echo "ignorado $p" || echo "EXPOSTO  $p"
done
git status --porcelain | grep -v "^ M \|^M  \|^D  \|^R  " 
```
Expected: cinco `ignorado`; o segundo comando não mostra nenhum `??` sob `input/`, `output/`, `src/reports/`, nem `.env`. Qualquer `EXPOSTO` → parar.

- [ ] **Step 5: Âncoras finais**

`config.py`: apagar `_PRODUTO` e seu comentário;
```python
SAIDA_PADRAO = RAIZ / "output" / PRODUTO
FONTES_PADRAO = RAIZ / "input" / PRODUTO
```

`_paths.py`, corpo final:
```python
# src/reports/_paths.py → parents[2] é o topo do repositório.
ROOT: Path = Path(__file__).resolve().parents[2]
PRODUCT: str = "informes_eventos"

INPUT: Path = ROOT / "input" / PRODUCT
OUTPUT: Path = ROOT / "output" / PRODUCT
# Documentos do Fed (committee_meeting_docs/) e planilhas de e-mail (email_info/).
FED_DOCS: Path = INPUT / "fed"
PROMPTS: Path = ROOT / "prompts" / PRODUCT
# A chave do FRED: `op inject -i .env.tpl -o .env`, na raiz.
ENV_FILE: Path = ROOT / ".env"
```

Conferir que quem grava cria a pasta: `grep -n "mkdir" src/comentario_matinal/*.py src/comentario_matinal/render/*.py | head` — o comando já cria a `saida/` (o manual diz isso); confirmar que usa `parents=True`. Se algum `mkdir(exist_ok=True)` sobre `SAIDA_PADRAO` não tiver `parents=True`, acrescentar: num clone novo `output/` não existe.

- [ ] **Step 6: Prosa — a tabela de substituição**

Aplicar em `docs/comentario_matinal/**/*.md`, nas células **markdown** de `notebooks/comentario_matinal/*.ipynb`, e nas docstrings/ajuda de `src/comentario_matinal/{cli,enviado,etapas}.py`:

| De | Para |
|---|---|
| `` `fontes/` `` | `` `input/comentario_matinal/` `` |
| `` `saida/` `` | `` `output/comentario_matinal/` `` |
| `saida/comentario_AAAAMMDD.md` | `output/comentario_matinal/comentario_AAAAMMDD.md` |
| `` `arquivo/AAAA/MM/` `` | `` `arquivo/comentario_matinal/AAAA/MM/` `` |
| `` `config/painel.toml` `` | `` `config/comentario_matinal/painel.toml` `` |
| `` `templates/comentario.dotx` `` | `` `templates/comentario_matinal/comentario.dotx` `` |
| `uv sync --all-packages` | `uv sync` |
| `uv run pytest` anunciando contagem | `uv run pytest tests/comentario_matinal` |

Nos `.ipynb`, editar com `nbformat` (como no script da Task 4) ou pelo editor de notebook — nunca por `sed` no JSON. Só células markdown.

Trechos que a tabela não resolve e são reescritos por inteiro:

`docs/comentario_matinal/plantao/02-instalacao.md`, o parágrafo "O repositório reúne vários produtos…" e o bloco `cd`:

````markdown
O repositório reúne vários produtos da divisão. O comentário matinal é um deles, e
**todos os comandos abaixo rodam da raiz do clone**:

```
cd mkt_intelligence
```
````

Os três comandos de instalação:

```markdown
1. Instalar as dependências: `uv sync`.
2. Instalar o filtro de notebook: `uv run nbstripout --install`.
3. Criar a pasta das fontes: `mkdir input\comentario_matinal` (ver abaixo por que ela não vem no clone).
```

O parágrafo "O `uv sync --all-packages` cria a `.venv`…" começa por "O `uv sync` cria a `.venv` — uma só, na raiz, para todos os produtos — e instala tudo…".

A seção "As pastas que não vêm no clone":

```markdown
`input/` e `output/` estão no `.gitignore` e **não existem depois de clonar**. É de
propósito: uma guarda os PDFs da Bloomberg, que não entram no repositório, e a outra
guarda as saídas do dia, que são refeitas toda manhã.

Isso importa porque o Passo 1 manda salvar os PDFs do dia **dentro de
`input/comentario_matinal/`**, e a pasta não está lá. Criá-la à mão, na raiz do
repositório — ao lado de `prompts/` — não dentro de `notebooks/`, que é o engano
fácil de quem roda pelo notebook: os caminhos padrão são ancorados na raiz do
repositório, e uma pasta de fontes no lugar errado faz a etapa avisar que não
aproveitou PDF algum, sem dizer por quê. A `output/comentario_matinal/` o próprio
comando cria.
```

`notebooks/comentario_matinal/plantao.ipynb`, célula markdown "Passo 1 — Coleta", o parágrafo "Reunir antes as fontes…":

```markdown
Reunir antes as fontes do dia em `input/comentario_matinal/`, **só em PDF**: as etapas
recebem texto, nunca anexo nem imagem. É a `input/` da **raiz do repositório** — ao
lado de `prompts/` —, não uma pasta dentro de `notebooks/`: os caminhos padrão são
ancorados na raiz, em `config.py`, e uma `notebooks/…/input/` faria a etapa avisar
"nenhum PDF aproveitado" sem dizer por quê.
```

`docs/comentario_matinal/README.md`, a árvore de pastas (linhas ~50-65): redesenhar com a árvore-alvo da spec §4, só o que é do matinal.

`docs/informes_eventos/AGENTS.md`: "Tudo roda de dentro desta pasta." → "Tudo roda da raiz do repositório."; `uv sync --all-packages` → `uv sync`; `uv run pytest` → `uv run pytest tests/informes_eventos`; `etc/.env` e o `op inject` → `.env` e `op inject -i .env.tpl -o .env`; "Todo caminho se ancora na raiz deste produto…" → "Todo caminho sai de `src/reports/_paths.py`: `input/informes_eventos/`, `output/informes_eventos/`, `.env` na raiz, e `input/informes_eventos/fed/` para os documentos do Fed. `tests/informes_eventos/test_paths.py` prende isso."; pasta do dia `input/fomc/<AAAAMMDD>/` → `input/informes_eventos/fomc/<AAAAMMDD>/`; `src/reports/fomc/input/committee_meeting_docs/` → `input/informes_eventos/fed/committee_meeting_docs/`; saídas `output/reports/fomc/<AAAAMMDD>/` → `output/informes_eventos/reports/fomc/<AAAAMMDD>/`; a seção "Não mexer" inteira:

```markdown
Nunca ler, imprimir, comitar ou resumir `.env`, `input/informes_eventos/` (pasta do
dia do FOMC, `fed/` com os PDFs do Fed e o `email_info/`, `payroll/`, `grid1.xlsx`,
`emailPayroll.xlsx`) e `output/informes_eventos/`. Referir por caminho apenas. As
respostas do modelo gravadas ali são minuta de informe: nunca ler nem resumir na
conversa.
```

- [ ] **Step 7: Testes que citam as pastas**

`tests/comentario_matinal/test_documentacao.py`: apagar as duas entradas `TEMPORÁRIO` de `CAMINHOS_QUE_SAO_MOLDE`; em `BANDEIRAS_FORA_DO_MANUAL`, os motivos de `--saida`, `--fontes`, `--arquivo`, `--config` passam pela tabela do Step 6; o comentário do `RE_CAMINHO` e a docstring de `_pastas_conhecidas` trocam `saida/` e `fontes/` por `output/` e `input/`.

`tests/comentario_matinal/test_notebook.py`, `PARAMETROS_FORA_DO_NOTEBOOK`: os quatro motivos (`saida`, `fontes`, `arquivo`, `config`) passam pela mesma tabela; "na pasta do produto" → "na raiz do repositório".

Os `tmp_path / "saida"` e `tmp_path / "fontes"` dos testes de pipeline **não mudam**: são nomes de pasta temporária, não o endereço do repositório.

- [ ] **Step 8: Contagem anunciada**

Matinal: +1 (`test_o_arranjo_final`) → 186. Atualizar `185 testes` → `186 testes` em `docs/comentario_matinal/AGENTS.md` e `docs/comentario_matinal/CLAUDE.md`.

- [ ] **Step 9: Portão**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `329 passed` (186 + 143).
Run: `grep -rn "_PRODUTO\|_PRODUCT\b" src tests` → vazio.
Run: `grep -rln "\`saida/\|\`fontes/" docs/comentario_matinal notebooks/comentario_matinal src/comentario_matinal` → vazio.

- [ ] **Step 10: Commit**

```bash
git status --porcelain
git add -A
git status --porcelain | grep -i "^?? \|^A .*\(input/\|output/\|\.pdf\|\.docx\|\.xls\|\.env$\)" && echo "PARAR"
git commit -m "Reúne o que entra e o que sai em input e output na raiz"
```
Corpo: cinco pastas de trabalho com nomes diferentes, uma delas dentro do pacote, viram duas na raiz, ignoradas inteiras por regra ancorada; o `arquivo/` fica fora delas de propósito, porque é versionado.

---

### Task 7: Instruções, README, limpeza

**Files:**
- Modify: `AGENTS.md`, `CLAUDE.md`, `README.md` (raiz)
- Modify: `docs/comentario_matinal/{AGENTS,CLAUDE}.md` (seções de ambiente, comandos, "Não mexer")
- Delete: `scripts/migra_notebooks.py`, `.ruff-check-antes.txt`, `.ruff-format-antes.txt`, `produtos/`
- Modify: memória `repo-mkt-intelligence.md`

- [ ] **Step 1: `AGENTS.md` da raiz**

Substituir as seções "Estrutura" e o cabeçalho por:

```markdown
# AGENTS.md — mkt_intelligence

Regras que valem para todos os produtos. As de cada produto estão em
`docs/<produto>/AGENTS.md`, e prevalecem no que for específico. Antes de mexer num
produto, ler o dele.

## Estrutura

- Um projeto uv só: um `pyproject.toml`, um `uv.lock` e uma `.venv`, os três na raiz. **Instalar é `uv sync`, na raiz.**
- As pastas da raiz são por tipo, com subpasta por produto onde couber: `src/` (pacotes `comentario_matinal` e `reports`), `notebooks/`, `tests/`, `config/`, `prompts/`, `templates/`, `arquivo/`, `exemplos/`, `docs/`.
- `input/<produto>/` é tudo o que entra e `output/<produto>/` é tudo o que sai; as duas ficam fora do git, inteiras. `arquivo/` não é saída: é o registro versionado do que foi enviado.
- Um pacote não importa o outro. Código igual nos dois é cópia (`reports/_modelo.py`), e `tests/informes_eventos/test_independence.py` cobra. Se uma mudança num produto pedir mexer no outro, é sinal de acoplamento — parar e perguntar.
- Caminho se acha num lugar por pacote: `comentario_matinal/config.py` e `reports/_paths.py`. Nenhum outro módulo lê `__file__`; os testes de âncora cobram.
- O portão é `uv run pytest`, na raiz. Para um produto só: `uv run pytest tests/<produto>`.
```

Em "Ambiente": a linha dos notebooks passa a "instalar por clone com `uv run nbstripout --install`, na raiz"; acrescentar "Notebooks: `uv run jupyter lab` na raiz, ou o kernel `.venv` no VS Code."

Em "Sigilo", primeira linha: "Nunca comitar, ler, imprimir ou resumir: `input/`, `output/` e `.env`."

- [ ] **Step 2: `CLAUDE.md` da raiz**

```markdown
# CLAUDE.md — mkt_intelligence

@AGENTS.md

As regras de cada produto valem junto com estas, e prevalecem no que for específico:

@docs/comentario_matinal/CLAUDE.md
@docs/informes_eventos/AGENTS.md
```
(`docs/comentario_matinal/CLAUDE.md` já importa o `AGENTS.md` vizinho com `@AGENTS.md`, que resolve relativo a ele.)

- [ ] **Step 3: `docs/comentario_matinal/{AGENTS,CLAUDE}.md`**

Passar a tabela de substituição da Task 6 no que sobrar. No `AGENTS.md`: §2 — o índice da Bloomberg está "no `pyproject.toml` da raiz" (sai a frase sobre workspace); instalação `uv sync`; §3, tabela de comandos — "Verificar" vira `uv run pytest tests/comentario_matinal`, com "186 testes"; §9 "Não mexer" — `fontes/` → `input/comentario_matinal/`, `saida/` → `output/comentario_matinal/`, `arquivo/AAAA/MM/` → `arquivo/comentario_matinal/AAAA/MM/`; §10 — `notebooks/plantao.ipynb` → `notebooks/comentario_matinal/plantao.ipynb`, `tests/test_notebook.py` → `tests/comentario_matinal/test_notebook.py`, `docs/plantao/` → `docs/comentario_matinal/plantao/`. No `CLAUDE.md`: os exemplos de `uv run pytest tests/test_temas.py` ganham o `comentario_matinal/` no caminho.

- [ ] **Step 4: `README.md` da raiz**

Reescrever a tabela "Produtos" (coluna "Pasta" → "Pacote" / "Notebooks" / "Docs": `src/comentario_matinal` · `notebooks/comentario_matinal/` · `docs/comentario_matinal/`; `src/reports` · `notebooks/informes_eventos/` · `docs/informes_eventos/`), o parágrafo abaixo dela (projeto único, `uv sync`, `uv run jupyter lab`, tudo roda da raiz, manual em `docs/comentario_matinal/plantao/`), acrescentar a árvore da spec §4 e reescrever "Um produto novo":

```markdown
## Um produto novo

1. Informe pós-evento de mesma natureza (CPI, BCE, Copom…) → subpacote de `src/reports/`, notebooks em `notebooks/informes_eventos/<evento>/`.
2. Produto de outra natureza → pacote novo em `src/<nome>/`, acrescentado a `module-name` no `pyproject.toml`, com um módulo único de caminhos e o teste de âncora correspondente; subpasta `<nome>/` em `notebooks/`, `tests/`, `docs/` (com `AGENTS.md`, importado pelo `CLAUDE.md` da raiz) e no que mais usar.
3. Dados de trabalho em `input/<nome>/` e `output/<nome>/`, que já estão fora do git. Segredo no `.env` da raiz.
4. O pacote novo não importa os outros: acrescentar a direção nova a `tests/informes_eventos/test_independence.py`.
5. Linha nova na tabela acima.
```

- [ ] **Step 5: Limpeza de `produtos/`**

```bash
git ls-files produtos | head      # esperado: vazio
find produtos -type f -not -path "*/.pytest_cache/*" -not -path "*/.ruff_cache/*" -not -path "*/__pycache__/*" | head
```
Expected: os dois vazios. Só então:
```bash
rm -rf produtos
rm -f .ruff-check-antes.txt .ruff-format-antes.txt
git rm scripts/migra_notebooks.py && rmdir scripts
```
Se o `find` mostrar qualquer arquivo, **não apagar**: mostrar o caminho (só o caminho) ao usuário e perguntar.

- [ ] **Step 6: Critérios de aceite da spec (§11)**

```bash
test ! -e produtos && echo "1 ok"
git ls-files input output | wc -l                      # 0
uv sync && uv run pytest -q 2>&1 | tail -1             # 329 passed
(cd notebooks && uv run matinal --help >/dev/null && uv run publica-wiki --help >/dev/null && echo "4 ok")
grep -rl "sys.path" notebooks | wc -l                  # 0
git log --follow --oneline -- src/comentario_matinal/config.py | tail -1   # commit antigo
uv run ruff check | tail -1; uv run ruff format --check | tail -1
```

O wheel, agora que não há dado dentro de `src/`:
```bash
uv build --wheel -o "$TMPDIR/mkt-wheel" 2>&1 | tail -1
unzip -l "$TMPDIR"/mkt-wheel/*.whl | grep -c "comentario_matinal/\|reports/"          # > 40
unzip -l "$TMPDIR"/mkt-wheel/*.whl | grep -ci "\.pdf\|\.xls\|\.ipynb\|/input/"        # 0
rm -rf "$TMPDIR/mkt-wheel"
```

Clone limpo, sem Bloomberg e sem rede além do uv:
```bash
git clone . "$TMPDIR/mkt-clone" && cd "$TMPDIR/mkt-clone" && uv sync && uv run pytest -q 2>&1 | tail -1
```
Expected: `329 passed` (ou os mesmos `skipped` do repositório de origem — comparar as duas linhas). É este passo que prova que nenhum teste depende de `input/` ou `output/` existirem.

A conferência manual com o terminal logado (`uv run matinal imagens`, primeira célula de dados do `fomc_analysis.ipynb`) é do usuário, fora do plantão: avisar que falta e não executar.

- [ ] **Step 7: Memória**

Reescrever `C:\Users\mmart\.claude\projects\C--Users-mmart-Github-marc3lom-mkt-intelligence\memory\repo-mkt-intelligence.md`: projeto uv único; `uv sync` na raiz; pacotes `comentario_matinal` e `reports` em `src/`; notebooks em `notebooks/<produto>/`; `input/` e `output/` fora do git; regras de produto em `docs/<produto>/AGENTS.md`. Atualizar a linha correspondente do `MEMORY.md`.

- [ ] **Step 8: Commit**

```bash
git status --porcelain
git add -A
git commit -m "Reescreve as instruções e o README para o layout novo"
```
Depois: mostrar ao usuário `git log --oneline -8` e o `git show --stat` de cada commit da reestruturação, e **esperar** antes de qualquer push. Lembrar que a wiki publicada ainda cita os caminhos antigos: `uv run publica-wiki` fica a pedido, fora do plantão.

---

## Se algo der errado

- **Portão vermelho depois de um `git mv`:** quase sempre é caminho. `uv run pytest tests/informes_eventos/test_paths.py tests/comentario_matinal/test_caminhos.py -q` primeiro — se a âncora está verde, o erro é de um teste que ainda monta caminho por conta própria; `grep -rn "__file__" tests`.
- **Desfazer uma Task não comitada:** `git restore --staged . && git restore .` desfaz o que é versionado, mas **não** traz de volta pasta ignorada que foi movida por `mv` (Task 6, Step 3) nem por `git mv` de diretório (Task 3). Desfazer essas à mão, com o `mv` inverso, antes do `git restore`.
- **Desfazer uma Task comitada:** `git revert`, nunca `reset --hard` — e o mesmo cuidado com as pastas ignoradas.
