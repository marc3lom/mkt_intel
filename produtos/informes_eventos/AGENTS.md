# AGENTS.md — informes_eventos

Informes de inteligência de mercado que a Mesa de Investimentos envia por e-mail depois
de eventos dos EUA: reunião do FOMC e divulgação do payroll. Vieram do `py-bcb` em
setembro de 2026, com histórico. As regras comuns do repositório estão em `../../AGENTS.md`.

## Ambiente e comandos

Tudo roda de dentro desta pasta.

| Para quê | Comando |
|---|---|
| Instalar | `uv sync --all-packages`, na raiz do repositório |
| Verificar (o portão) | `uv run pytest` — sem Bloomberg, sem rede |
| Lint | `uv run ruff check .` e `uv run ruff format --check .` |
| Notebooks (a interface) | `uv run jupyter notebook` |

- pandas 3 e numpy 2.5, as mesmas versões do comentário matinal: o workspace resolve um lock só, e os dois produtos andam juntos. O teto `<3` herdado do py-bcb caiu em 15/09, aferido pela caracterização antes de sair.
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

## Etapas de modelo do FOMC

Resumo, comentários dos bancos e revisão de coerência são etapas de modelo em
`fomc/core/drafting.py`, disparadas por células do `fomc_analysis.ipynb`. O backend é
`src/reports/_modelo.py`, **cópia** do `modelo.py` do comentário matinal — nunca
importar `comentario_matinal`; `tests/test_independence.py` falha.

- Chama `claude -p --safe-mode` sem ferramentas, mensagem pela stdin, autenticação
  pela sessão do Claude Code; `ANTHROPIC_API_KEY` sai do ambiente do subprocesso.
  Variável: `INFORMES_EVENTOS_BACKEND` (padrão `claude-code`).
- **Os prompts em `prompts/` são a fonte de verdade editorial.** Para mudar como o
  texto lê, editar `00_guia_de_estilo.md`; o prompt da etapa só quando a mecânica
  mudar. Nada de estilo fixo no Python.
- Pasta do dia: `input/fomc/<AAAAMMDD>/` com `headlines.txt` (linha com `***` é
  destaque), `coletiva.txt` e `bancos/*.pdf` (nome do arquivo = nome do banco).
  Saídas em `output/reports/fomc/<AAAAMMDD>/`. Tudo fora do git e sob a regra de
  sigilo abaixo.
- Nenhum teste chama o `claude`: `subprocess.run` e o registro `BACKENDS` recebem
  dublês.

## Não mexer

Nunca ler, imprimir, comitar ou resumir `etc/.env`, `input/`, `input/fomc/`, `src/reports/*/input/` (PDFs do Fed, `email_info/`, `grid1.xlsx`, `emailPayroll.xlsx`), `output/`, `output/reports/fomc/<data>/`. Referir por caminho apenas. As respostas do modelo gravadas ali são minuta de informe: nunca ler nem resumir na conversa.

## Questões em aberto

- O template do FOMC é um caminho absoluto no OneDrive (`fomc/core/word_report.py:22`). Trazer um `.dotx` para `templates/`, como o matinal, ou manter?
