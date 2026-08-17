# Absorver a camada de renderização e aposentar o `daily`

Data: 17/08/2026

## Contexto

O `comentario_matinal` depende do `daily` por caminho — `{ path = "../daily",
editable = true }` no `pyproject.toml` —, o que obriga o repositório irmão a existir
literalmente ao lado deste. Clonar só o `comentario_matinal` numa máquina nova não
funciona.

A separação foi feita porque o `daily` tinha outros consumidores: os notebooks
`monitor_matinal.ipynb` e `calendario_economico.ipynb`, as variantes de `drafts/`, e o
`tests/test_render.py`. Duplicar o código criaria duas cópias divergindo com o tempo.

Esse motivo caducou. Os notebooks produzem as mesmas duas saídas que o
`uv run matinal` produz hoje — são o antecessor manual deste pipeline, e foram
aposentados. Com eles fora, não há segunda cópia a divergir.

O custo da separação é concreto. A correção do acento em "Gráficos" no rodapé do painel,
feita em 17/08, custou três passos para um caractere: editar em `../daily-dev`, comitar
na `develop`, mesclar em `../daily` na `main`.

## Decisão

Mover para este repositório os sete módulos do `daily` que o plantão usa, traduzidos
para o português do resto do código, e congelar o `daily`.

### Layout

```
src/comentario_matinal/
  render/
    __init__.py
    painel.py       ← daily/monitor.py
    tabelas.py      ← daily/tables.py
    ativos.py       ← daily/tickers.py
    feriados.py     ← daily/calendars.py
    gravacao.py     ← daily/output.py
    estilo.py       ← daily/config.py
  bql.py            ← daily/bloomberg.py
```

O `bql.py` fica fora do `render/` porque não desenha nada: é coleta, irmão de `dados.py`.
Seu único consumidor é o `calendario.py`.

Não vêm: `bloomberg_blpapi.py` e `bloomberg_pdblp.py` (565 linhas), backends alternativos
que só os notebooks de `drafts/` usavam.

### Renomeações

| Origem | Destino |
|---|---|
| `monitor.build_monitor_panel` | `render.painel.monta_painel` |
| `monitor.plot_sparkline_with_areas` | `render.painel.desenha_sparkline` |
| `monitor.normalize_price_series` | `render.painel.normaliza_serie` |
| `monitor.create_monitor_panel` | **removido** |
| `tables.render_combined_tables` | `render.tabelas.monta_tabelas` |
| `tables.render_table` | `render.tabelas.monta_tabela` |
| `tables.TableSpec` | `render.tabelas.EspecDeTabela` |
| `tables.format_value` | `render.tabelas.formata_valor` |
| `tables.should_highlight_atual` | `render.tabelas.destaca_atual` |
| `tables.should_highlight_revisado` | `render.tabelas.destaca_revisado` |
| `tables.ECO_TABLE_SPEC` | `render.tabelas.ESPEC_ECO` |
| `tables.CB_TABLE_SPEC_COMBINED` | `render.tabelas.ESPEC_BC` |
| `tables.CB_TABLE_SPEC` | **removido** |
| `tickers.TickerInfo` | `render.ativos.ItemDaGrade` |
| `tickers.MONITOR_TICKERS`, `ALL_TICKERS` | **removidos** |
| `tickers.MARKET_CALENDARS` | `render.ativos.CALENDARIOS_DE_MERCADO` |
| `calendars.is_market_holiday` | `render.feriados.e_feriado_de_mercado` |
| `output.save_figure` | `render.gravacao.grava_figura` |
| `config.COLORS` | `render.estilo.CORES` |
| `config.FONT_SIZES` | `render.estilo.FONTES` |
| `config.SPARKLINE_*` | `render.estilo.SPARKLINE_*` |
| `config.ECO_COLUMNS`, `ECO_COL_WIDTHS` | `render.tabelas`, junto do `ESPEC_ECO` |
| `config.CB_COLUMNS`, `CB_COL_WIDTHS_COMBINED` | `render.tabelas`, junto do `ESPEC_BC` |
| `config.CB_COL_WIDTHS_STANDALONE` | **removido** |
| `config.PROJECT_ROOT`, `OUTPUT_DIR` | **removidos** |
| `config.INPUT_DIR` | `config.MERCADO_FECHADO`, ver abaixo |
| `bloomberg.fetch_eco_calendar` | `bql.busca_calendario` |
| `bloomberg.fetch_central_banks` | `bql.busca_bancos_centrais` |
| `config.BQL_COUNTRIES`, `BQL_DATE_RANGE` | `bql.PAISES`, `bql.JANELA` |

`MONITOR_TICKERS` e `ALL_TICKERS` saem porque aqui os ativos vêm do `painel.toml`.
`PROJECT_ROOT`, `OUTPUT_DIR` e `INPUT_DIR` saem porque são os caminhos do `daily`; este
repositório já tem os seus em `config.py`, e o plantão passa `save_path` e `allowed_root`
explícitos.

### O ativo em disco

O painel não é só código. Ele carrega `input/market_closed.png` (110 KB) em tempo de
execução e o estampa nos tiles sem barras intradiárias. É o único uso vivo de `INPUT_DIR`
— o `eco_data.xlsx` que divide a pasta com ele só serve aos notebooks.

A imagem vem para `templates/mercado_fechado.png`, ao lado do `comentario.dotx`, e é
localizada por uma constante em `config.py`, do mesmo jeito que o template do Word:

```python
MERCADO_FECHADO = RAIZ / "templates" / "mercado_fechado.png"
```

O `render/painel.py` recebe o caminho por parâmetro, com esse valor como padrão, em vez
de derivá-lo de uma raiz de projeto. Assim a camada de desenho não precisa saber onde o
repositório começa.

Esquecer este item não quebra teste algum: o código já trata a ausência do arquivo como
caso normal (`if market_closed_path.exists()`), e o painel sai sem o selo. É exatamente o
tipo de regressão silenciosa que o teste de imagem de referência existe para pegar.

### `TickerInfo` vira `ItemDaGrade`, não `Ativo`

Este repositório já tem `Ativo` em `config.py`, e é o conceito mais rico: carrega
`rotulo`, `rotulo_grade`, `tipo` em português e `coluna`, com um `tipo_render` que existe
justamente para converter ao `type` inglês do `TickerInfo`. Traduzir `TickerInfo` para
`Ativo` criaria duas classes de mesmo nome e sentidos diferentes.

`ItemDaGrade` diz o que a coisa é: a visão que a camada de desenho tem do ativo, um tile
da grade.

## Sequenciamento

Dois commits, não um. O destino é idêntico; a diferença é diagnóstica.

**Commit 1 — mudança de lugar, sem tradução.** Move os sete módulos com os nomes em
inglês, reescreve os caminhos de import nos três arquivos que os consomem, traz o
`test_render.py` intacto e remove a dependência do `pyproject.toml`. Os testes provam que
a mudança de lugar não quebrou nada.

**Commit 2 — tradução.** Renomeia módulos, funções, classes e constantes conforme a
tabela acima, com os testes verdes antes e depois.

Num commit único, uma quebra não diria se veio da mudança de lugar ou da renomeação.

## Rede de segurança

Os 13 testes de `test_render.py` são de fumaça: verificam que sai uma `Figure`, que o
arquivo é gravado quando há caminho e que nada é escrito quando não há. Pegariam import
quebrado ou assinatura trocada; não pegariam o painel saindo diferente.

Como a saída desta camada é imagem que vai para a mesa, o spec acrescenta **um teste de
imagem de referência**, escrito ANTES do commit 1:

1. Renderizar um painel a partir de dados sintéticos determinísticos — sem Bloomberg — e
   gravar o PNG como referência em `tests/referencia/`.
2. Após cada commit, renderizar de novo e comparar com
   `matplotlib.testing.compare.compare_images`, com tolerância.

É o único artefato que prova que o painel entregue continua idêntico. Sem ele, a tradução
de 1.300 linhas fica apoiada em testes que só verificam que a função devolve uma figura.

## Dependências a declarar

Hoje elas chegam de carona pelo `daily`. Saindo ele do `pyproject.toml`, precisam entrar
por nome, ou o plantão quebra na primeira execução real:

| Pacote | Quem usa | Para quê |
|---|---|---|
| `polars-bloomberg` | `bql.py` | a consulta BQL do calendário e dos bancos centrais |
| `pandas-market-calendars` | `render/feriados.py` | distinguir feriado de bolsa de erro de dado |
| `numpy` | `render/painel.py` | normalização das séries do sparkline |

O `pyarrow`, que o `daily` declara, precisa ser verificado: se o `polars-bloomberg` o
exigir em tempo de execução, entra junto.

Verificação: `uv sync` num clone limpo, sem o `../daily` no disco, seguido da suíte.

## Pontos de chamada afetados

O raio de alcance deste lado são três arquivos e oito linhas:

| Arquivo | Linha | Símbolo |
|---|---|---|
| `config.py` | 15 | `TickerInfo` (import de topo) |
| `config.py` | 115–122 | `para_ticker_info` constrói `TickerInfo` |
| `cli.py` | 165, 169 | `build_monitor_panel` |
| `cli.py` | 186–193 | `render_combined_tables`, os dois specs |
| `calendario.py` | 55–58 | `fetch_eco_calendar`, `fetch_central_banks` |

## O que acontece com o `daily`

Fica congelado no GitHub como está, sem receber mais correções, com uma nota no README
dizendo que a camada de renderização passou para o `comentario_matinal`. Nada é apagado.

O worktree `../daily-dev` sai do fluxo. O README do `comentario_matinal` perde os passos
de configuração que mandam clonar o `../daily` e a seção sobre a dança de worktree.

## Fora de escopo

`Ativo.tipo_render` e `Config.para_ticker_info` existem para converter entre os dois
mundos. Com os dois no mesmo repositório, essa conversão provavelmente pode ser
colapsada — `Ativo` passaria direto para a camada de desenho.

**Não se faz aqui.** É outra mudança, com seu próprio risco, e misturá-la à mudança de
lugar e à tradução é exatamente o que o sequenciamento em dois commits existe para
evitar.

Também fora de escopo: traduzir os comentários e docstrings internos dos módulos movidos
além do necessário para que façam sentido. A tradução do commit 2 cobre a API pública e
o que estiver no caminho.

## Riscos

| Risco | Mitigação |
|---|---|
| A tradução muda o painel sem ninguém notar | Teste de imagem de referência, escrito antes de tudo |
| Dependência que vinha pelo `daily` falta aqui | Declaradas explicitamente no commit 1, ver abaixo; a suíte roda antes de seguir |
| Renomeação incompleta deixa símbolo órfão | `uv run pytest` mais `grep -rn "daily"` ao fim de cada commit |
| Perda dos notebooks | O `daily` fica congelado, não apagado; continuam rodando contra ele |

## Critérios de aceitação

1. `grep -rn "daily" src/ tests/ pyproject.toml` não devolve nada.
2. `uv sync` completa sem o `../daily` existir no disco.
3. Os 83 testes atuais mais os 13 do `test_render.py` mais o de imagem passam.
4. O painel renderizado bate com a referência dentro da tolerância.
5. O README não menciona mais clonar o `../daily` nem o worktree `../daily-dev`.
