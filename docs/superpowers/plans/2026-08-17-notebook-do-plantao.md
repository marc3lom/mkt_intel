# Notebook do plantão — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir rodar o plantão por notebook além do terminal, sem que as duas formas possam divergir.

**Architecture:** A orquestração sai do `cli.py` para um núcleo novo, `plantao.py`. O comando e o notebook viram fachadas finas sobre ele — nenhum é cópia do outro, porque há uma implementação só. A única duplicação inevitável, a sequência dos passos, ganha um teste que fica vermelho quando as duas divergem.

**Tech Stack:** Python 3.14, uv, pytest, matplotlib (Agg), pandas, nbformat, nbstripout, ipykernel.

**Spec:** `docs/superpowers/specs/2026-08-17-notebook-do-plantao-design.md`

## Global Constraints

- Python `>=3.14`. Tudo por `uv run`.
- Nomes, docstrings e comentários em **português**; comentários explicam *por quê*, não *o quê*. Seguir o tom de `enviado.py` e `janela.py`.
- Backend matplotlib `Agg`. Nenhum teste abre janela, nenhum consulta a Bloomberg.
- **Nenhuma mudança de comportamento.** Isto é mudança de lugar mais uma fachada nova. Mesmas saídas, mesmas mensagens, mesmos códigos de saída.
- `plantao.py` não importa `argparse` e não chama `sys.exit`. `cli.py` não contém regra de negócio.
- O `fecha_plantao` **não** entra no notebook: é o único passo destrutivo.
- Ao fim de cada tarefa: `uv run pytest -q` verde e árvore limpa antes de comitar.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/comentario_matinal/plantao.py` | **novo** — o plantão como funções; sem terminal, sem notebook |
| `src/comentario_matinal/cli.py` | fachada de terminal: argumentos → chamada → formatação → código de saída |
| `notebooks/plantao.ipynb` | **novo** — fachada de notebook: mesmas chamadas, objetos na tela |
| `tests/test_orquestracao.py` | **novo** — caracterização do caminho de coleta |
| `tests/test_notebook.py` | **novo** — os dois testes de sincronia |
| `.gitattributes` | **novo** — filtro `nbstripout` para `*.ipynb` |

---

### Task 1: Teste de caracterização

A rede que hoje não existe. Os 101 testes cobrem módulos; a orquestração — que ordem, que argumento, que arquivo — não é exercitada por nenhum, e é exatamente ela que a Tarefa 2 vai mover. Escrito **antes** de mover uma linha, verde contra o `cli.main()` de hoje.

**Files:**
- Create: `tests/test_orquestracao.py`

**Interfaces:**
- Consumes: `comentario_matinal.cli.main`, `carrega_config`, e os três coletores como estão hoje.
- Produces: o teste que as Tarefas 2 e 3 usam como aferição.

- [ ] **Step 1: Escrever o teste**

```python
"""O caminho de coleta produz os mesmos quatro arquivos, com o mesmo conteúdo.

Os demais testes cobrem módulos. A orquestração — que ordem, que argumento, que
arquivo — não é exercitada por nenhum, e é justamente ela que a extração do
`plantao.py` move. Este teste é a rede: verde contra o `cli.main()` de hoje e
verde contra o núcleo extraído depois.
"""

from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

from comentario_matinal.config import TZ_BR, carrega_config

# Onde os coletores estão ligados. ``from … import`` liga o nome no módulo que
# importa, então é lá que o monkeypatch precisa agir — não no módulo de origem.
# A Tarefa 2 muda esta linha, e só ela.
MODULO = "comentario_matinal.cli"

MARCA = "20260817"


def _referencia(cfg) -> pd.DataFrame:
    tickers = [a.ticker for a in cfg.ativos]
    return pd.DataFrame(
        {
            "px_last": [100.0 + i for i in range(len(tickers))],
            "chg_net_1d": [0.5] * len(tickers),
            "chg_pct_1d": [0.5] * len(tickers),
        },
        index=tickers,
    )


def _intraday(cfg) -> dict[str, pd.Series]:
    """Dois ativos com barras, o resto sem — exercita o selo de mercado fechado."""
    tickers = [a.ticker for a in cfg.ativos]
    return {t: pd.Series([100.0, 100.5, 101.0]) for t in tickers[:2]}


def _eco() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "United States", "DATA": "2026-08-17", "HORÁRIO": "09:30",
         "EVENTO": "Empire Manufacturing", "PERÍODO": "Aug",
         "ESTIMATIVA": "10.0", "ATUAL": "-", "ANTERIOR": "15.6", "REVISADO": "-"},
        {"PAÍS": "China", "DATA": "2026-08-17", "HORÁRIO": "04:00",
         "EVENTO": "Retail Sales YoY", "PERÍODO": "Jul",
         "ESTIMATIVA": "1.5", "ATUAL": "0.6", "ANTERIOR": "1.0", "REVISADO": "-"},
    ])


def _bancos() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "Eurozone Aggregate", "DATA": "2026-08-17", "HORÁRIO": "06:30",
         "EVENTO": "ECB's Lane Speaks in Dublin"},
    ])


@pytest.fixture
def bloomberg_falsa(monkeypatch):
    cfg = carrega_config()
    monkeypatch.setattr(f"{MODULO}.coleta_referencia",
                        lambda ativos: (_referencia(cfg), []))
    monkeypatch.setattr(f"{MODULO}.coleta_intraday",
                        lambda ativos, asof, ref: _intraday(cfg))
    monkeypatch.setattr(f"{MODULO}.coleta_calendario",
                        lambda: (_eco(), _bancos()))
    return cfg


def test_coleta_produz_os_quatro_arquivos(bloomberg_falsa, monkeypatch, tmp_path):
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert (tmp_path / f"painel_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"calendario_{MARCA}.png").stat().st_size > 10_000

    md = (tmp_path / f"calendario_{MARCA}.md").read_text(encoding="utf-8")
    assert "CALENDÁRIO ECONÔMICO" in md
    assert "Empire Manufacturing" in md
    assert "ECB's Lane Speaks in Dublin" in md


def test_bloco_direcional_lista_todo_ativo_do_painel(bloomberg_falsa, monkeypatch,
                                                     tmp_path):
    """O bloco é o que as três etapas de IA leem como estado do mercado.

    Um ativo que suma dele some da triagem, da redação e da revisão de uma vez —
    e sem erro, porque nada afirma que ele deveria estar lá.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    texto = (tmp_path / f"painel_{MARCA}.txt").read_text(encoding="utf-8")
    assert "PAINEL DIRECIONAL" in texto
    assert "17/08/2026 07:40" in texto
    for ativo in bloomberg_falsa.ativos:
        assert ativo.rotulo in texto, f"{ativo.rotulo} sumiu do bloco direcional"
```

- [ ] **Step 2: Rodar e ver passar**

Run: `uv run pytest tests/test_orquestracao.py -q`
Expected: `2 passed`

Se falhar, **não é o código de produção que está errado** — é a fixture que não reproduz o que os coletores reais devolvem. Ajustar a fixture, nunca o `cli.py`.

- [ ] **Step 3: Provar que o teste pega regressão**

Comentar temporariamente a linha do `cli.py` que grava o calendário em markdown (`caminho_cal_md.write_text(...)`), rodar, ver vermelho, restaurar, ver verde. Depois o mesmo com a linha que grava `painel_{marca}.txt`.

Um teste de caracterização que não falha quando a orquestração muda não caracteriza nada, e a Tarefa 2 se apoiaria nele.

Run: `uv run pytest tests/test_orquestracao.py -q`
Expected: FAIL nas duas provocações, PASS depois de restaurar.

- [ ] **Step 4: Suíte inteira**

Run: `uv run pytest -q`
Expected: `103 passed` (101 + 2)

- [ ] **Step 5: Comitar**

```bash
git add tests/test_orquestracao.py
git commit -m "Caracteriza o caminho de coleta antes de extraí-lo

Os testes de hoje cobrem módulos. A orquestração — que ordem, que
argumento, que arquivo — não é exercitada por nenhum, e um main()
quebrado passaria verde. É justamente ela que a extração do plantao.py
vai mover.

O teste roda o caminho inteiro com os três coletores falsificados e
afere os quatro arquivos produzidos, incluindo que todo ativo do
painel.toml aparece no bloco direcional — o texto que as três etapas
de IA leem como estado do mercado."
```

---

### Task 2: Extrair `plantao.py`

Move a orquestração do `cli.py` para um núcleo sem vocabulário de terminal. Nenhum comportamento muda.

**Files:**
- Create: `src/comentario_matinal/plantao.py`
- Modify: `src/comentario_matinal/cli.py` (de 559 para perto de 300 linhas)
- Modify: `tests/test_orquestracao.py` (uma linha: `MODULO`)

**Interfaces:**
- Consumes: o teste de caracterização da Tarefa 1.
- Produces: `plantao.PASSOS`, `plantao.contexto`, `plantao.coleta_mercado`, `plantao.desenha_painel`, `plantao.prepara_calendario`, `plantao.monta_bloco`, `plantao.roda_etapa`, `plantao.monta_documento`, `plantao.confere`, `plantao.fecha_plantao`, e as dataclasses `Contexto`, `Mercado`, `Painel`, `Calendario`, `Bloco`, `Etapa`, `Fechamento`. A Tarefa 3 constrói o notebook sobre exatamente esses nomes.

- [ ] **Step 1: Criar o esqueleto do núcleo**

```python
"""O plantão como funções, sem terminal e sem notebook.

O comando e o notebook são fachadas sobre este módulo. Nenhum dos dois
implementa o plantão, e é por isso que não podem divergir: há uma
implementação só.

Três coisas que o ``cli.py`` misturava ficam separadas aqui. Erro levanta
exceção. Aviso — o que não impede seguir, mas o autor precisa ver — viaja na
lista ``avisos`` do resultado, em vez de ir ao stderr e sumir. Código de saída
é vocabulário de terminal e não existe neste módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from comentario_matinal.config import (
    CONFIG_PADRAO, MERCADO_FECHADO, SAIDA_PADRAO, Config, carrega_config,
)
from comentario_matinal.janela import agora, fuso_local, na_janela

# Os passos públicos, na ordem do runbook. É este o contrato que o notebook
# precisa cobrir, e é dele que o teste de sincronia parte.
PASSOS = (
    "contexto",
    "coleta_mercado",
    "desenha_painel",
    "prepara_calendario",
    "monta_bloco",
    "roda_etapa",
    "monta_documento",
    "confere",
    "fecha_plantao",
)


class ErroDePlantao(RuntimeError):
    """Impede seguir. Cada fachada decide como mostrar."""


class SemDadoDeMercado(ErroDePlantao):
    """A consulta de referência voltou vazia — terminal Bloomberg inativo?"""


class FaltaInsumo(ErroDePlantao):
    """Falta material que um passo anterior deveria ter produzido."""
```

Mais a sentinela que resolve o comentário do dia anterior sem obrigar o notebook a
reimplementar a busca:

```python
# Por padrão, `roda_etapa` procura sozinha o comentário do dia anterior em
# ``ctx.arquivo``. O comando passa None quando recebe --sem-anterior, e o texto
# lido quando recebe --anterior. A busca automática é regra de negócio, não
# vocabulário de terminal, e por isso mora aqui.
AUTOMATICO = object()
```

E as dataclasses, com estes campos exatos:

```python
@dataclass(frozen=True)
class Contexto:
    cfg: Config
    asof: datetime
    saida: Path
    fontes: Path
    arquivo: Path
    marca: str          # AAAAMMDD
    dry_run: bool


@dataclass(frozen=True)
class Mercado:
    referencia: pd.DataFrame
    intraday: dict[str, pd.Series]
    indisponiveis: list[str]


@dataclass(frozen=True)
class Painel:
    figura: Figure
    metricas: dict[str, dict]
    caminho: Path


@dataclass(frozen=True)
class Calendario:
    eco: pd.DataFrame | None
    bancos: pd.DataFrame | None
    figura: Figure | None
    caminho_png: Path | None
    caminho_md: Path | None
    avisos: list[str]


@dataclass(frozen=True)
class Bloco:
    texto: str
    caminho: Path
    avisos: list[str]


@dataclass(frozen=True)
class Etapa:
    nome: str
    texto: str
    caminho: Path
    asof: datetime            # o horário de redação efetivamente usado
    comentario: Path | None   # só a revisão produz
    avisos: list[str]


@dataclass(frozen=True)
class Fechamento:
    arquivados: list[Path]
    removidos: int
```

Assinaturas dos passos:

```python
def contexto(asof: datetime | str | None = None,
             saida: Path = SAIDA_PADRAO,
             fontes: Path = FONTES_PADRAO,
             arquivo: Path = ARQUIVO_PADRAO,
             config: Path = CONFIG_PADRAO) -> Contexto
def coleta_mercado(ctx) -> Mercado
def desenha_painel(ctx, mercado) -> Painel
def prepara_calendario(ctx) -> Calendario
def monta_bloco(ctx, mercado, painel, calendario: Calendario | None) -> Bloco
def roda_etapa(ctx, nome, *, temas=None, anterior=AUTOMATICO,
               web=False, modelo=None) -> Etapa
def monta_documento(ctx, comentario, template=TEMPLATE_PADRAO) -> Path
def confere(ctx) -> list[Divergencia]      # Divergencia vem de enviado.py
def fecha_plantao(ctx, forcar=False) -> Fechamento
```

- [ ] **Step 2: Mover a coleta e as três saídas**

`cli.py` linhas 107–134 viram `contexto()`; linhas 154–163 viram `coleta_mercado`; 165–180 viram `desenha_painel`; 182–212 viram `prepara_calendario`; 214–232 viram `monta_bloco`.

Regras da mudança:

- Todo `print(..., file=sys.stderr)` que **avisa** vira item de `avisos`. Todo `print` que **informa caminho gravado** (`Painel: …`, `Calendário: …`, `Texto: …`) some do núcleo: a fachada os deriva dos campos de caminho do resultado.
- O `return 1` de referência vazia vira `raise SemDadoDeMercado(...)`, com a mesma mensagem de hoje.
- `--sem-calendario` **não** vira parâmetro. A fachada não chama `prepara_calendario`, e `monta_bloco` recebe `calendario=None`. O `calendario_vazio` que o `monta_texto` exige passa a ser `calendario is None or calendario.eco is None or calendario.eco.empty`.
- `dry_run` sai de `not na_janela(agora())` dentro de `contexto()` — relógio real, nunca o `asof`, como hoje.

- [ ] **Step 3: Mover as quatro funções que já são funções**

`_roda_etapa` (linha 381), `_monta_documento` (527), `_confere` (282) e `_fecha_plantao` (317) viram `roda_etapa`, `monta_documento`, `confere`, `fecha_plantao`.

`roda_etapa` é a mais densa: mistura conversão de fontes com avisos, leitura de arquivo com erro, resolução de `asof` com aviso, montagem de insumos, mensagem por etapa, chamada ao modelo e gravação. Extrair **preservando a ordem das checagens** — ela é significativa, porque a resolução do `asof` depende do painel já lido.

O que fica na fachada, por ser vocabulário de terminal:

- traduzir `--temas "a | b | c"` em texto de marcadores, e ler `--temas-arquivo`;
- traduzir `--sem-anterior` em `anterior=None` e `--anterior caminho` em `anterior=<texto lido>`. **A busca automática em `ctx.arquivo` fica no núcleo**, sob a sentinela `AUTOMATICO`: ela é regra de negócio — decide o que a triagem julga como ineditismo e o que a revisão compara para achar contradição —, e deixá-la na fachada obrigaria o notebook a reimplementá-la, que é exatamente a divergência que este trabalho existe para impedir;
- o `FaltaInsumo` de temas ausentes é do núcleo; a mensagem que ensina a passar `--temas` é da fachada.

- [ ] **Step 4: Reduzir o `cli.py` a fachada**

`main()` passa a: montar `Contexto`, despachar por subcomando, chamar o núcleo, imprimir avisos e caminhos, traduzir exceção em código de saída.

Um lugar só para a tradução de erro:

```python
try:
    ...
except ErroDePlantao as e:
    print(f"Erro: {e}", file=sys.stderr)
    return 1
```

Extrair também a lista de subcomandos para constante de módulo, que a Tarefa 3 afere:

```python
SUBCOMANDOS = ("triagem", "redacao", "revisao", "conferir", "enviado")
```

e usar `choices=SUBCOMANDOS` no `add_argument`.

- [ ] **Step 5: Apontar o teste de caracterização para o novo módulo**

Em `tests/test_orquestracao.py`, uma linha:

```python
MODULO = "comentario_matinal.plantao"
```

- [ ] **Step 6: Verificar**

Run: `uv run pytest -q`
Expected: `103 passed`. **Se o teste de caracterização falhar, a extração mudou comportamento** — é para isso que ele existe; não relaxar o teste.

Run: `uv run python -c "import comentario_matinal.plantao as p; import inspect; assert 'argparse' not in inspect.getsource(p); assert 'sys.exit' not in inspect.getsource(p); print('núcleo limpo')"`

Conferir à mão que os subcomandos respondem como hoje:

```bash
uv run matinal conferir          # 1, saida/ vazia
uv run matinal enviado           # 1, fora da janela
uv run matinal redacao           # 1, sem temas
```

- [ ] **Step 7: Comitar**

```bash
git add -A
git commit -m "Extrai a orquestração do plantão para plantao.py

O cli.py misturava três coisas: fazer o plantão, avisar o autor e
decidir o código de saída. As três ficam separadas — erro levanta
exceção, aviso viaja no objeto de resultado, código de saída é
vocabulário de terminal e sai do núcleo.

Os avisos ganham com a mudança: hoje vão ao stderr e somem. Como dado,
ficam inspecionáveis pelas duas fachadas e aferíveis por teste.

Nenhum comportamento muda. O teste de caracterização do commit
anterior é a prova, e reverter este commit devolve o cli.py que rodou
em produção em 17/08."
```

---

### Task 3: O notebook e os testes de sincronia

**Files:**
- Create: `notebooks/plantao.ipynb`
- Create: `tests/test_notebook.py`
- Create: `.gitattributes`
- Modify: `pyproject.toml` (grupo `dev`)
- Modify: `README.md`

**Interfaces:**
- Consumes: `plantao.PASSOS` e as funções da Tarefa 2; `cli.SUBCOMANDOS`.
- Produces: nada que outro código use.

- [ ] **Step 1: Dependências**

Ao grupo `dev` do `pyproject.toml`, que o `uv sync` já instala por padrão:

```toml
dev = [
    "pytest>=9.1",
    "ipykernel>=7.1",
    "nbformat>=5.10",
    "nbstripout>=0.9",
]
```

Run: `uv sync`

- [ ] **Step 2: Escrever os testes de sincronia, antes do notebook**

```python
"""As duas formas de rodar o plantão não podem divergir.

O comando e o notebook são fachadas sobre o mesmo núcleo, então nenhum
reimplementa nada. O que sobra de duplicação é a SEQUÊNCIA — a ordem dos passos
existe no argparse e nas células —, e é ela que estes testes prendem.
"""

from pathlib import Path

import pytest

NOTEBOOK = Path(__file__).parent.parent / "notebooks" / "plantao.ipynb"

# O fechamento do plantão fica fora do notebook de propósito: apaga fontes/ e
# saida/, grava o arquivo que a triagem de amanhã lê, e notebook é onde se
# re-executa célula sem querer.
FORA_DO_NOTEBOOK = {"fecha_plantao"}

# Como cada subcomando do terminal aparece no notebook. Nem sempre pelo nome: o
# `conferir` da linha de comando é a função `confere` do núcleo, e as três
# etapas de IA chegam como o nome da etapa passado a `roda_etapa`. Este mapa é
# a correspondência entre as duas fachadas — o lugar onde elas podem divergir
# sem que nada mais perceba.
EQUIVALENTE = {
    "triagem": '"triagem"',
    "redacao": '"redacao"',
    "revisao": '"revisao"',
    "conferir": "plantao.confere",
    # `enviado` fica fora de propósito: é o único passo destrutivo.
}


def _notebook():
    import nbformat

    return nbformat.read(NOTEBOOK, as_version=4)


def _codigo() -> str:
    return "\n".join(c.source for c in _notebook().cells if c.cell_type == "code")


def test_notebook_cobre_todo_passo_do_nucleo():
    from comentario_matinal import plantao

    codigo = _codigo()
    faltando = sorted(p for p in plantao.PASSOS
                      if p not in FORA_DO_NOTEBOOK and f"plantao.{p}" not in codigo)
    assert not faltando, (
        f"O notebook não exercita {faltando}. Passo novo no núcleo precisa de "
        "célula nova: sem isso as duas formas de rodar o plantão divergem, que é "
        "o que este teste existe para impedir."
    )


def test_o_mapa_de_equivalencia_cobre_todo_subcomando():
    """Subcomando novo obriga a decidir se ele existe no notebook, e como."""
    from comentario_matinal.cli import SUBCOMANDOS

    faltando = sorted(set(SUBCOMANDOS) - set(EQUIVALENTE) - {"enviado"})
    assert not faltando, (
        f"{faltando} entrou no terminal sem entrada em EQUIVALENTE. Decidir se "
        "o notebook o cobre e por qual chamada — ou listá-lo como deliberadamente "
        "fora, com o motivo."
    )


def test_notebook_cobre_todo_subcomando_do_terminal():
    from comentario_matinal.cli import SUBCOMANDOS

    codigo = _codigo()
    faltando = sorted(c for c in SUBCOMANDOS
                      if c in EQUIVALENTE and EQUIVALENTE[c] not in codigo)
    assert not faltando, (
        f"O terminal tem {faltando} e o notebook não. Quem aprender o plantão "
        "pelo notebook não saberia que existem."
    )


def test_notebook_comitado_nao_carrega_saida():
    sujas = [i for i, c in enumerate(_notebook().cells, 1)
             if c.cell_type == "code" and (c.get("outputs")
                                           or c.get("execution_count"))]
    assert not sujas, (
        f"As células {sujas} carregam saída de execução. Comitar assim leva dados "
        "de mercado — e possivelmente o texto do comentário antes de ele ter sido "
        "enviado — para o histórico do git. Rodar `uv run nbstripout "
        "notebooks/plantao.ipynb`, ou instalar o filtro com `uv run nbstripout "
        "--install`."
    )
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_notebook.py -q`
Expected: `test_o_mapa_de_equivalencia_cobre_todo_subcomando` passa — ele só lê constantes; os outros três falham por o notebook não existir.

- [ ] **Step 4: Construir o notebook**

Construir com `nbformat` num script descartável — escrever JSON de `.ipynb` à mão é convite a arquivo inválido, e o `nbformat` garante células sem `outputs` desde o começo. Apagar o script depois; só o `.ipynb` é comitado.

Estrutura de células:

| # | Tipo | Conteúdo |
|---|---|---|
| 1 | md | Título; a janela de 7h–9h; que o `enviado` **não** está aqui |
| 2 | code | `ctx = plantao.contexto()` e a faixa de dry run |
| 3 | md | Passo 1 — coleta. Terminal Bloomberg ativo? |
| 4 | code | `mercado = plantao.coleta_mercado(ctx)`; `mercado.referencia.head()` |
| 5 | code | `painel = plantao.desenha_painel(ctx, mercado)`; `painel.figura` |
| 6 | code | `calend = plantao.prepara_calendario(ctx)`; `calend.eco` |
| 7 | code | `bloco = plantao.monta_bloco(ctx, mercado, painel, calend)`; `print(bloco.texto)` |
| 8 | md | Passo 2 — triagem. Largar os PDFs em `fontes/` antes |
| 9 | code | `triagem = plantao.roda_etapa(ctx, "triagem")`; `print(triagem.texto)` |
| 10 | md | Passo 3 — **a decisão é sua**: ler a triagem e escolher os temas |
| 11 | code | `TEMAS = """- …"""` — célula de edição |
| 12 | code | `redacao = plantao.roda_etapa(ctx, "redacao", temas=TEMAS)` |
| 13 | code | `revisao = plantao.roda_etapa(ctx, "revisao")` |
| 14 | md | Passo 7 — montagem do documento |
| 15 | code | `docx = plantao.monta_documento(ctx, revisao.comentario)` |
| 16 | md | Passo 8 — conferência, **antes** do e-mail |
| 17 | code | `divs = plantao.confere(ctx)` e o relato |
| 18 | md | Passo 9 — `uv run matinal enviado`, **no terminal**, depois do envio |

A faixa de dry run, na célula 2:

```python
from IPython.display import HTML, display

from comentario_matinal import plantao
from comentario_matinal.janela import faixa

ctx = plantao.contexto()

if ctx.dry_run:
    display(HTML(
        '<div style="background:#b00020;color:#fff;padding:12px 16px;'
        'border-radius:6px;font-size:15px;font-weight:600">'
        f'DRY RUN — fora da janela de {faixa()}. '
        'Execução de ensaio; não enviar o resultado à diretoria.</div>'
    ))
else:
    display(HTML(
        '<div style="background:#0b6e3a;color:#fff;padding:12px 16px;'
        'border-radius:6px;font-size:15px;font-weight:600">'
        f'Plantão — dentro da janela de {faixa()}.</div>'
    ))
```

No terminal o banner de dry run interrompe a leitura no stderr; numa célula, uma linha de log passa batido. Por isso a faixa, e por isso ela também aparece no caso normal — uma faixa que só existe no erro ensina a ignorar o espaço onde ela apareceria.

Cada célula que produz avisos os mostra:

```python
for aviso in calend.avisos:
    print(f"Aviso: {aviso}")
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_notebook.py -q`
Expected: `4 passed`

Run: `uv run pytest -q`
Expected: `107 passed` (103 da Tarefa 2 mais os 4 deste arquivo)

- [ ] **Step 6: Provar que os três testes pegam o que prometem**

Um a um, restaurando entre eles:

1. Acrescentar `"passo_novo"` a `plantao.PASSOS` → `test_notebook_cobre_todo_passo_do_nucleo` fica vermelho nomeando `passo_novo`.
2. Acrescentar `"foo"` a `cli.SUBCOMANDOS` → `test_o_mapa_de_equivalencia_cobre_todo_subcomando` fica vermelho. Depois acrescentar `"foo": "plantao.foo"` a `EQUIVALENTE` → agora `test_notebook_cobre_todo_subcomando_do_terminal` é que fica vermelho. Os dois testes pegam pontos diferentes da mesma divergência, e ambos precisam ser vistos.
3. Abrir o notebook, executar uma célula, salvar → `test_notebook_comitado_nao_carrega_saida` fica vermelho nomeando a célula. Limpar com `uv run nbstripout notebooks/plantao.ipynb` e ver verde.

Sem isto, os quatro são decoração: a tarefa inteira existe para que a divergência falhe alto, e um teste que nunca foi visto vermelho não prova que falha.

- [ ] **Step 7: O filtro do git**

Criar `.gitattributes`:

```
# Notebooks: as saídas de execução carregam dados de mercado e o texto do
# comentário antes do envio. O filtro as tira no `git add`; o teste de
# tests/test_notebook.py é a rede para o clone onde ele não foi instalado.
*.ipynb filter=nbstripout
```

Instalar: `uv run nbstripout --install`

Provar que funciona: abrir o notebook, executar uma célula, salvar, `git add notebooks/plantao.ipynb`, e conferir que `git diff --cached` não traz `outputs`.

- [ ] **Step 8: README**

Em "Configuração inicial", um passo: `uv run nbstripout --install`, explicando que sem ele um notebook executado leva dados de mercado para o commit.

Em "Runbook do plantão", uma seção curta antes do Passo 1: as duas formas de rodar, o terminal e o `notebooks/plantao.ipynb`, com a nota de que o `enviado` só existe no terminal e por quê.

- [ ] **Step 9: Comitar**

```bash
git add -A
git commit -m "Notebook do plantão, com a sincronia presa por teste

Segunda fachada sobre o plantao.py. Não reimplementa nada: as células
chamam as mesmas funções que o comando chama.

O que sobra de duplicação é a sequência dos passos, que existe no
argparse e nas células. Três testes a prendem: um afere que o notebook
exercita todo passo do núcleo, outro que cobre todo subcomando do
terminal, e o terceiro que o notebook comitado não carrega saída de
execução — sem ele, rodar o plantão de manhã e comitar enfia dados de
mercado e o texto do comentário no histórico.

O enviado fica fora do notebook. É o único passo destrutivo, e
notebook é onde se re-executa célula sem querer.

O dry run vira faixa, não linha de log: no terminal o banner de stderr
interrompe a leitura, numa célula passaria batido."
```

---

## Verificação final

- [ ] `uv run pytest -q` verde
- [ ] `uv run matinal` e cada subcomando se comportam como antes — comparar com o que o README documenta
- [ ] `plantao.py` sem `argparse` e sem `sys.exit`; `cli.py` sem regra de negócio
- [ ] Os três testes de sincronia foram vistos vermelhos, um a um
- [ ] `git add` de um notebook executado não leva `outputs` para o índice
- [ ] Na manhã seguinte, primeira execução real: `uv run matinal` com o terminal Bloomberg ativo. Nenhum teste toca a Bloomberg, então é o primeiro exercício verdadeiro do núcleo extraído
