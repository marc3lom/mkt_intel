# AGENTS.md — informes_eventos

Informes de inteligência de mercado que a Mesa de Investimentos envia por e-mail depois
de eventos dos EUA: reunião do FOMC e divulgação do payroll. Vieram do `py-bcb` em
setembro de 2026, com histórico. As regras comuns do repositório estão em `../../AGENTS.md`.

## Ambiente e comandos

Tudo roda de dentro desta pasta.

| Para quê | Comando |
|---|---|
| Instalar | `uv sync` |
| Verificar (o portão) | `uv run pytest` — sem Bloomberg, sem rede |
| Lint | `uv run ruff check .` e `uv run ruff format --check .` |
| Notebooks (a interface) | `uv run jupyter notebook` |

- pandas `<3` e numpy `<2.5`, com `build-constraint-dependencies = ["numpy<2.5"]`. Trocar as duas travas juntas, ou nenhuma.
- `is_bloomberg_available()` não existe aqui; chamada real à Bloomberg só com Windows e o terminal logado.
- A chave do FRED (fallback do payroll) é lida de `etc/.env`, gerado do `etc/.env.tpl` com `op inject -i etc/.env.tpl -o etc/.env`.

## Código

- Identificadores, mensagens de log e de erro em inglês; docstrings, comentários, rótulos de gráfico e commits em pt-BR. Docstrings antigas em inglês ficam como estão.
- `src/reports/_bloomberg.py` e `src/reports/_style.py` são cópias do `py-bcb`. Nunca importar `classes.*` — `tests/test_independence.py` falha.
- Todo caminho se ancora na raiz deste produto: `input/`, `output/`, `etc/` aqui, e `src/reports/fomc/input/` para os documentos do Fed. `TestProjectRootAnchors` prende isso.
- xbbg 1.x: `abdib` aceita um ticker por chamada e devolve o horário (UTC) numa **coluna** `time`; chamadas sync travam no Jupyter — usar sempre `_run_async`.
- Fusos: horários do FOMC e do payroll são âncoras em ET (`America/New_York`); exibição em `America/Sao_Paulo`; tirar o fuso só imediatamente antes de plotar.
- `COPOM[4]` (vermelho) é reservado às linhas de evento no grid.

## Convenções de mercado implementadas

| Onde | O quê | Convenção |
|---|---|---|
| `fomc/core/data_loader.py` | OIS forward 1Y1Y, derivado | capitalização anual: `f = (1+S₂)²/(1+S₁) − 1`, saída em % |
| `fomc/core/data_loader.py` | inclinação 2s10s | `(10Y − 2Y) × 100` → bps |
| `fomc/core/calculations.py` | surpresa | atual − pesquisa |

## Não mexer

Nunca ler, imprimir, comitar ou resumir `etc/.env`, `input/`, `src/reports/*/input/` (PDFs do Fed, `email_info/`, `grid1.xlsx`, `emailPayroll.xlsx`), `output/`. Referir por caminho apenas.

## Questões em aberto

- O template do FOMC é um caminho absoluto no OneDrive (`fomc/core/word_report.py:22`). Trazer um `.dotx` para `templates/`, como o matinal, ou manter?
- `calculate_surprise` trunca surpresa de 1bp para 0bp (`int()` sobre `0.9999…`); fixado como `xfail` estrito.
- Subir para pandas 3 (o matinal já está nele).
