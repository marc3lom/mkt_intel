# Absorver o `daily` — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trazer a camada de renderização do `daily` para dentro do `comentario_matinal`, traduzida, e eliminar a dependência de caminho `../daily`.

**Architecture:** Sete módulos vão para `src/comentario_matinal/render/`, exceto o de consulta BQL, que vira `bql.py` na raiz do pacote por ser coleta e não desenho. A mudança acontece em dois commits — mudança de lugar, depois tradução — para que uma quebra diga qual dos dois a causou. Um teste de imagem de referência, escrito antes de tudo, é a única prova de que o painel entregue à mesa continua idêntico.

**Tech Stack:** Python 3.14, uv, pytest, matplotlib (Agg), pandas, numpy, polars-bloomberg, pandas-market-calendars.

**Spec:** `docs/superpowers/specs/2026-08-17-absorver-daily-design.md`

## Global Constraints

- Python `>=3.14`. O piso vinha do `daily`; passa a ser deste projeto.
- Nomes de módulo, função, classe e constante em **português**, como o resto do pacote — exceto no Commit da Tarefa 2, que move sem traduzir.
- Docstrings e comentários em português, explicando **por quê**, não o quê. Seguir o tom dos módulos existentes (`enviado.py`, `janela.py`).
- Backend matplotlib `Agg`. Nenhum teste pode abrir janela.
- Nenhum teste pode consultar o Bloomberg. Dados sintéticos e determinísticos.
- `asof` sempre explícito nos testes de imagem: o painel estampa "Atualizado em …" e sem `asof` fixo a imagem muda a cada execução.
- Ao fim de cada tarefa: `uv run pytest -q` verde e árvore limpa antes de comitar.

---

### Task 1: Teste de imagem de referência

Estabelece a linha de base **antes** de qualquer movimentação. Os 13 testes que vêm do `daily` são de fumaça — verificam que sai uma `Figure` — e não pegariam o painel saindo diferente. Este pega.

**Files:**
- Create: `tests/test_referencia.py`
- Create: `tests/referencia/painel.png` (gerado no Step 3, versionado)

**Interfaces:**
- Consumes: `daily.monitor.build_monitor_panel`, `daily.tickers.TickerInfo` — os nomes atuais, ainda em inglês. A Tarefa 2 troca o caminho do import; a Tarefa 3 troca os nomes.
- Produces: `tests/referencia/painel.png`, a imagem contra a qual as Tarefas 2 e 3 se verificam.

- [ ] **Step 1: Escrever o teste**

Criar `tests/test_referencia.py`:

```python
"""O painel entregue à mesa continua idêntico?

Os demais testes de renderização verificam que sai uma figura e que o arquivo
é gravado. Nenhum olha a imagem. Como a saída desta camada é o que chega ao
e-mail, este teste compara o desenho com uma referência versionada — é o que
pega mudança silenciosa numa renomeação de mil e trezentas linhas.
"""

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.testing.compare import compare_images

REFERENCIA = Path(__file__).parent / "referencia" / "painel.png"

# O painel carimba o horário. Sem asof fixo a imagem muda a cada execução e a
# comparação nunca fecha.
ASOF = datetime(2026, 8, 17, 7, 54)

TICKERS = ["AA Index", "BB Index", "CC Curncy", "DD Comdty"]


def _itens():
    from daily.tickers import TickerInfo

    return [
        TickerInfo("AA Index", "aa", "Taxa 10a", "rate"),
        TickerInfo("BB Index", "bb", "Bolsa Fut", "equity"),
        TickerInfo("CC Curncy", "cc", "Moeda", "fx"),
        TickerInfo("DD Comdty", "dd", "Petróleo", "commodity"),
    ]


def _referencia() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "px_last": [4.250, 5300.0, 5.4321, 88.75],
            "chg_net_1d": [0.035, 42.0, -0.0123, 1.20],
            "chg_pct_1d": [0.83, 0.80, -0.23, 1.37],
        },
        index=TICKERS,
    )


def _intraday() -> dict[str, pd.Series]:
    """Dois ativos com barras, dois sem.

    Os sem barras exercitam o selo de mercado fechado, que carrega uma imagem
    de disco — o item mais fácil de esquecer na mudança de lugar, e o que não
    quebra teste algum quando some.
    """
    passo = np.linspace(0.0, 1.0, 40)
    return {
        "AA Index": pd.Series(4.20 + 0.05 * passo),
        "BB Index": pd.Series(5260.0 + 40.0 * passo),
    }


def _desenha(destino: Path):
    from daily.monitor import build_monitor_panel

    fig, _ = build_monitor_panel(
        _itens(),
        _referencia(),
        _intraday(),
        save_path=destino,
        allowed_root=destino.parent,
        grid=(1, 4),
        asof=ASOF,
        column_headers=["Taxas", "Bolsas", "Moedas", "Commodities"],
    )
    plt.close(fig)
    return destino


def test_painel_bate_com_a_referencia(tmp_path):
    saida = _desenha(tmp_path / "painel.png")

    assert REFERENCIA.exists(), (
        f"Referência ausente. Gerar uma vez com:\n"
        f'  uv run python -c "'
        f"import sys; sys.path.insert(0,'tests'); "
        f"from test_referencia import _desenha, REFERENCIA; "
        f"REFERENCIA.parent.mkdir(exist_ok=True); _desenha(REFERENCIA)\""
    )

    # tol em unidades de RMS por pixel. Zero seria frágil demais entre
    # execuções; 1.0 pega qualquer mudança visível e ignora ruído de
    # antialiasing.
    diferenca = compare_images(str(REFERENCIA), str(saida), tol=1.0)
    assert diferenca is None, diferenca
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_referencia.py -q`
Expected: FAIL com `Referência ausente. Gerar uma vez com: …`

- [ ] **Step 3: Gerar a referência**

```bash
mkdir -p tests/referencia
uv run python -c "import sys; sys.path.insert(0,'tests'); from test_referencia import _desenha, REFERENCIA; _desenha(REFERENCIA)"
```

- [ ] **Step 4: Olhar a imagem gerada**

Abrir `tests/referencia/painel.png` e conferir a olho: quatro tiles, os dois primeiros com sparkline, os dois últimos com o selo de mercado fechado, cabeçalhos de coluna no topo, carimbo "Atualizado em 17/08/26 - 07:54".

Se o selo não aparecer nos dois últimos, **parar**: significa que o `input/market_closed.png` não está sendo encontrado já hoje, e a referência gravaria o defeito como se fosse o esperado.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_referencia.py -q`
Expected: PASS

- [ ] **Step 6: Provar que o teste pega mudança**

Alterar `ASOF` no teste para `datetime(2026, 8, 17, 7, 55)`. O painel carimba o horário, então um minuto a mais muda a imagem.

Run: `uv run pytest tests/test_referencia.py -q`
Expected: FAIL, com caminho para o PNG de diferença.

Desfazer a alteração e confirmar que volta a passar. **Sem este passo o teste não vale nada** — um teste de imagem que passa incondicionalmente é pior que nenhum, porque dá confiança falsa.

- [ ] **Step 7: Comitar**

```bash
git add tests/test_referencia.py tests/referencia/painel.png
git commit -m "Teste de imagem de referência para o painel

Os testes de renderização que vêm do daily verificam que sai uma
Figure e que o arquivo é gravado. Nenhum olha o desenho. Como a saída
desta camada é o que vai no e-mail, uma renomeação pode mudá-la sem
quebrar teste algum.

A referência fixa asof, porque o painel carimba o horário, e deixa
dois ativos sem barras intradiárias para exercitar o selo de mercado
fechado — que carrega imagem de disco e, quando o arquivo some, o
código trata como caso normal e desenha sem o selo."
```

---

### Task 2: Mudança de lugar, sem tradução

Move os sete módulos com os nomes em inglês e corta a dependência. Nada é renomeado aqui.

**Files:**
- Create: `src/comentario_matinal/render/__init__.py`
- Create: `src/comentario_matinal/render/{monitor,tables,tickers,calendars,output,estilo}.py` (de `../daily/src/daily/`)
- Create: `src/comentario_matinal/bloomberg.py` (de `../daily/src/daily/bloomberg.py`)
- Create: `templates/mercado_fechado.png` (de `../daily/input/market_closed.png`)
- Create: `tests/test_render.py` (de `../daily/tests/test_render.py`)
- Modify: `src/comentario_matinal/config.py:15,115-122`
- Modify: `src/comentario_matinal/cli.py:165,186-189`
- Modify: `src/comentario_matinal/calendario.py:55`
- Modify: `tests/test_referencia.py` (dois imports)
- Modify: `pyproject.toml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `tests/referencia/painel.png` da Tarefa 1.
- Produces: `comentario_matinal.render.monitor.build_monitor_panel`, `comentario_matinal.render.tickers.TickerInfo`, `comentario_matinal.render.tables.{render_combined_tables, ECO_TABLE_SPEC, CB_TABLE_SPEC_COMBINED}`, `comentario_matinal.bloomberg.{fetch_eco_calendar, fetch_central_banks}`. Nomes inalterados; só o caminho muda.

- [ ] **Step 1: Copiar os módulos**

```bash
mkdir -p src/comentario_matinal/render
D=../daily/src/daily
cp $D/monitor.py $D/tables.py $D/tickers.py $D/calendars.py $D/output.py src/comentario_matinal/render/
cp $D/config.py src/comentario_matinal/render/estilo.py
cp $D/bloomberg.py src/comentario_matinal/bloomberg.py
cp ../daily/input/market_closed.png templates/mercado_fechado.png
cp ../daily/tests/test_render.py tests/test_render.py
printf '"""Camada de desenho: painel, tabelas e o que elas precisam."""\n' > src/comentario_matinal/render/__init__.py
```

- [ ] **Step 2: Reescrever os imports internos do `render/`**

Em cada arquivo de `src/comentario_matinal/render/`, trocar:

| De | Para |
|---|---|
| `from daily.config import` | `from comentario_matinal.render.estilo import` |
| `from daily.calendars import` | `from comentario_matinal.render.calendars import` |
| `from daily.output import` | `from comentario_matinal.render.output import` |
| `from daily.tickers import` | `from comentario_matinal.render.tickers import` |

E em `src/comentario_matinal/bloomberg.py`: `from daily.config import BQL_COUNTRIES, BQL_DATE_RANGE` → `from comentario_matinal.render.estilo import BQL_COUNTRIES, BQL_DATE_RANGE`.

- [ ] **Step 3: Reapontar o ativo de disco**

Em `src/comentario_matinal/render/estilo.py`, apagar `PROJECT_ROOT`, `OUTPUT_DIR` e `INPUT_DIR`.

Em `src/comentario_matinal/config.py`, acrescentar junto das outras constantes de caminho:

```python
MERCADO_FECHADO = RAIZ / "templates" / "mercado_fechado.png"
```

Em `src/comentario_matinal/render/monitor.py`, trocar o parâmetro e as duas linhas que usam `INPUT_DIR`. Acrescentar à assinatura de `build_monitor_panel`, depois de `column_headers`:

```python
    market_closed_path: Path | None = None,
```

e substituir as linhas 178-181 por:

```python
    # O selo vem por parâmetro, não de uma raiz de projeto: esta camada
    # desenha, não sabe onde o repositório começa.
    market_closed_img = None
    if market_closed_path is not None and market_closed_path.exists():
        market_closed_img = plt.imread(str(market_closed_path))
```

Em `src/comentario_matinal/render/output.py`, o `save_figure` usava `OUTPUT_DIR` como padrão de `allowed_root` (linha 33 — é o único uso em código). Tornar o parâmetro obrigatório: todos os chamadores daqui já passam um.

Três docstrings afirmam esse padrão e passam a mentir no mesmo commit que o remove. Corrigir as três, dizendo que a raiz permitida é obrigatória: `monitor.py:156`, `tables.py:145` e `tables.py:254`. Corrigir também o cabeçalho de `output.py`, que abre com "Saving is allowed ONLY inside OUTPUT_DIR".

- [ ] **Step 4: Reapontar os quatro consumidores**

`src/comentario_matinal/config.py:15`:
```python
from comentario_matinal.render.tickers import TickerInfo
```

`src/comentario_matinal/cli.py:165`:
```python
    from comentario_matinal.render.monitor import build_monitor_panel
```
e passar o selo na chamada, acrescentando ao final dos argumentos de `build_monitor_panel`:
```python
        market_closed_path=MERCADO_FECHADO,
```
importando `MERCADO_FECHADO` de `comentario_matinal.config` junto das outras constantes no topo.

`src/comentario_matinal/cli.py:186`:
```python
        from comentario_matinal.render.tables import (
```

`src/comentario_matinal/calendario.py:55`:
```python
    from comentario_matinal.bloomberg import fetch_central_banks, fetch_eco_calendar
```

`tests/test_referencia.py`: `from daily.tickers import TickerInfo` → `from comentario_matinal.render.tickers import TickerInfo`; `from daily.monitor import build_monitor_panel` → `from comentario_matinal.render.monitor import build_monitor_panel`. Acrescentar `market_closed_path=MERCADO_FECHADO` à chamada em `_desenha`, importando de `comentario_matinal.config`.

- [ ] **Step 5: Adaptar o `test_render.py` que veio junto**

Trocar os imports de `daily.*` para `comentario_matinal.render.*`. Substituir `OUTPUT_DIR` e o helper `_output_snapshot` pelo `tmp_path` do pytest — a pasta `output/` do `daily` não existe aqui.

Dois testes dependem de `create_monitor_panel` e `MONITOR_TICKERS`, que não vieram: `test_monitor_no_save_returns_figure_and_writes_nothing` (linha 97) e `test_monitor_saves_when_path_given` (linha 107). Substituir os dois por:

```python
def _itens_minimos():
    from comentario_matinal.render.tickers import TickerInfo

    return [TickerInfo("AA Index", "aa", "Taxa 10a", "rate")]


def test_monitor_sem_save_devolve_figura_e_nao_grava(tmp_path):
    fig, _ = build_monitor_panel(_itens_minimos(), pd.DataFrame(), {}, grid=(1, 1))
    try:
        assert isinstance(fig, Figure)
        assert list(tmp_path.iterdir()) == []
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
```

`build_monitor_panel` devolve tupla, enquanto o `create_monitor_panel` que sumiu devolvia só a figura — daí o `fig, _`.

- [ ] **Step 6: Trocar as dependências**

Em `pyproject.toml`, remover `"daily"` de `dependencies` e a seção `[tool.uv.sources]` que a aponta para `../daily` (preservando a linha do `blpapi`). Acrescentar:

```toml
    "numpy>=2.0",
    "polars-bloomberg>=0.5.4",
    "pandas-market-calendars>=5.4.0",
```

Atualizar o comentário acima de `requires-python`, que hoje diz que o piso vem do `daily`.

Run: `uv sync`

- [ ] **Step 7: Rodar tudo**

Run: `uv run pytest -q`
Expected: PASS — 83 anteriores, mais o de referência, mais os que sobraram do `test_render.py`.

Run: `grep -rn "daily" src/ tests/ pyproject.toml`
Expected: nenhuma saída.

Se o teste de imagem falhar aqui, o culpado quase certo é o selo de mercado fechado: comparar o PNG de diferença que o `compare_images` grava.

- [ ] **Step 8: Atualizar o README**

Remover, da seção "Configuração inicial", o passo que manda clonar o `daily` em `../daily` e o parágrafo que explica que ele é dependência de instalação. Remover a tabela de repositórios e a seção sobre alterar renderização em `../daily-dev`. Acrescentar, em "Estrutura", uma linha sobre `src/comentario_matinal/render/`.

- [ ] **Step 9: Comitar**

```bash
git add -A
git commit -m "Traz a camada de renderização para dentro do repositório

A dependência de caminho para ../daily obrigava o repositório irmão a
existir ao lado deste, e existia por um motivo que caducou: os
notebooks que também consumiam o daily produzem as mesmas saídas que
o \`uv run matinal\` produz hoje, e foram aposentados.

Sete módulos vêm como estão, em inglês. A tradução é o commit
seguinte: separadas, uma quebra diz qual das duas mudanças a causou.

O input/market_closed.png vem como templates/mercado_fechado.png e
passa a ser localizado por parâmetro, não por uma raiz de projeto que
esta camada não deveria conhecer. As dependências que chegavam de
carona pelo daily — polars-bloomberg, pandas-market-calendars,
numpy — entram por nome."
```

---

### Task 3: Tradução

Renomeia módulos, funções, classes e constantes. O teste de imagem é a rede.

**Files:**
- Rename + Modify: todos os de `src/comentario_matinal/render/`, `src/comentario_matinal/bloomberg.py`
- Modify: `src/comentario_matinal/{config,cli,calendario}.py`, `tests/test_referencia.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: tudo o que a Tarefa 2 produziu.
- Produces: `render.painel.monta_painel(itens, referencia, intraday, save_path=None, figsize=…, grid=…, allowed_root=None, asof=None, cabecalhos=None, selo_fechado=None) -> tuple[Figure, dict]`; `render.ativos.ItemDaGrade(ticker, nome, rotulo, tipo)`; `render.tabelas.monta_tabelas(tabelas, save_path=None, fig_width=14, allowed_root=None) -> Figure | None`; `render.tabelas.EspecDeTabela`; `render.feriados.e_feriado_de_mercado(ticker, dia=None) -> bool`; `render.gravacao.grava_figura(fig, destino, allowed_root)`; `bql.busca_calendario() -> pd.DataFrame`; `bql.busca_bancos_centrais() -> pd.DataFrame`.

- [ ] **Step 1: Renomear os arquivos**

```bash
cd src/comentario_matinal/render
git mv monitor.py painel.py
git mv tables.py tabelas.py
git mv tickers.py ativos.py
git mv calendars.py feriados.py
git mv output.py gravacao.py
cd ../../..
git mv src/comentario_matinal/bloomberg.py src/comentario_matinal/bql.py
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest -q`
Expected: FAIL com `ModuleNotFoundError: comentario_matinal.render.monitor`

- [ ] **Step 3: Traduzir, módulo a módulo, na ordem das dependências**

Ordem: `estilo` → `ativos` → `feriados` → `gravacao` → `tabelas` → `painel` → `bql`. Cada um só depende dos anteriores, então cada passo deixa a suíte mais perto do verde sem depender do que ainda não foi feito.

Aplicar a tabela de renomeações do spec, seção "Renomeações". Além dela, traduzir os parâmetros que aparecem nas assinaturas públicas:

| De | Para |
|---|---|
| `tickers_info` | `itens` |
| `ref_data` | `referencia` |
| `price_data` | `intraday` |
| `column_headers` | `cabecalhos` |
| `market_closed_path` | `selo_fechado` |
| `TickerInfo.name` | `ItemDaGrade.nome` |
| `TickerInfo.display` | `ItemDaGrade.rotulo` |
| `TickerInfo.type` | `ItemDaGrade.tipo` |

`save_path`, `allowed_root`, `figsize`, `grid` e `asof` **ficam como estão** — são vocabulário de matplotlib e de caminho, já usados assim em `cli.py`, e traduzi-los criaria atrito com a biblioteca.

Ao traduzir `ItemDaGrade.tipo`, notar que os valores continuam em inglês (`"rate"`, `"equity"`, `"fx"`, `"commodity"`, `"vol"`), porque é para eles que `Ativo.tipo_render` converte a partir do português do `painel.toml`. Trocar os valores exigiria mexer no `config.py` e no `painel.toml`, e isso é fora de escopo.

- [ ] **Step 4: Reapontar os consumidores**

`config.py`: `from comentario_matinal.render.ativos import ItemDaGrade`; `para_ticker_info` vira `para_itens_da_grade` e constrói `ItemDaGrade(ticker=…, nome=…, rotulo=…, tipo=…)`. Atualizar a docstring do módulo, que cita "os `TickerInfo` que a camada de renderização do `daily` consome".

`cli.py`: `from comentario_matinal.render.painel import monta_painel`; a chamada passa a usar `cfg.para_itens_da_grade(...)`, `cabecalhos=` e `selo_fechado=`. `from comentario_matinal.render.tabelas import ESPEC_BC, ESPEC_ECO, monta_tabelas`.

`calendario.py`: `from comentario_matinal.bql import busca_bancos_centrais, busca_calendario`.

`tests/test_referencia.py` e `tests/test_render.py`: idem.

- [ ] **Step 5: Rodar tudo**

Run: `uv run pytest -q`
Expected: PASS, **incluindo o teste de imagem**. Se ele falhar e os outros passarem, a tradução mudou o desenho: abrir o PNG de diferença antes de qualquer outra coisa.

Run: `grep -rniE "\b(monitor_panel|ticker_info|render_table|save_figure|is_market_holiday|fetch_eco|fetch_central|TableSpec|COLORS|FONT_SIZES)\b" src/ tests/`
Expected: nenhuma saída.

- [ ] **Step 6: Comitar**

```bash
git add -A
git commit -m "Traduz a camada de renderização

Segunda metade da absorção. O commit anterior moveu o código como
estava; este alinha os nomes ao português do resto do pacote, com o
teste de imagem provando que o painel entregue não mudou.

TickerInfo vira ItemDaGrade, não Ativo: já existe um Ativo em
config.py, mais rico, e é dele que sai a conversão para esta camada.
ItemDaGrade diz o que a coisa é — a visão que o desenho tem do ativo,
um tile da grade.

save_path, allowed_root, figsize, grid e asof ficam em inglês: são
vocabulário de matplotlib, e traduzi-los criaria atrito com a
biblioteca sem ganho de clareza."
```

---

### Task 4: Congelar o `daily`

**Files:**
- Modify: `../daily/README.md`

**Interfaces:**
- Consumes: nada. Independente das anteriores; só faz sentido depois delas.
- Produces: nada que o código use.

- [ ] **Step 1: Escrever a nota**

No topo do `../daily/README.md`, logo abaixo do título:

```markdown
> **Congelado em 17/08/2026.** A camada de renderização — painel, tabelas,
> calendário BQL e detecção de feriado — passou para o repositório
> `comentario_matinal`, que é onde ela recebe correções a partir de agora.
> Este repositório fica como está, para que os notebooks de `notebooks/` e
> `drafts/` continuem rodando. Não espelhar aqui mudanças feitas lá.
```

- [ ] **Step 2: Comitar e empurrar**

```bash
cd ../daily
git add README.md
git commit -m "Congela o repositório

A camada de renderização passou para o comentario_matinal. Este repo
fica como está para os notebooks continuarem rodando; correções vão
para lá."
git push
```

- [ ] **Step 3: Remover o worktree de desenvolvimento**

O `../daily-dev` existia para desenvolver a renderização sem mexer no que o plantão consome. Sem plantão consumindo, perdeu a função.

```bash
git -C ../daily worktree list
git -C ../daily worktree remove ../daily-dev
```

Confirmar com o autor antes de rodar o `remove`: há trabalho não comitado ali?

---

## Verificação final

Depois da Tarefa 4, contra os critérios de aceitação do spec:

- [ ] `grep -rn "daily" src/ tests/ pyproject.toml` não devolve nada
- [ ] `uv run pytest -q` verde
- [ ] `uv run matinal conferir` responde (exercita a cadeia de import inteira sem Bloomberg)
- [ ] Renomear `../daily` temporariamente para `../daily-x`, rodar `uv sync` e a suíte, e desfazer — prova que a dependência de caminho morreu de verdade
- [ ] O README não menciona mais `../daily` nem `../daily-dev`
- [ ] Na manhã seguinte, primeira execução real: `uv run matinal` produz painel e calendário com o Bloomberg ativo. É o único passo que exercita `bql.py` e `feriados.py` de verdade — nenhum teste os cobre contra dado real.
