# AGENTS.md — informes_eventos

Informes de inteligência de mercado que a Mesa de Investimentos envia por e-mail depois
de eventos dos EUA: reunião do FOMC e divulgação do payroll. Vieram do `py-bcb` em
setembro de 2026, com histórico. As regras comuns do repositório estão em `../../AGENTS.md`.

## Ambiente e comandos

Tudo roda da raiz do repositório.

| Para quê | Comando |
|---|---|
| Instalar | `uv sync`, na raiz do repositório |
| Verificar (o portão) | `uv run pytest tests/informes_eventos` — sem Bloomberg, sem rede |
| Lint | `uv run ruff check .` e `uv run ruff format --check .` |
| Notebooks (a interface) | `uv run jupyter notebook` |

- pandas 3 e numpy 2.5, as mesmas versões do comentário matinal: o projeto resolve um lock só, e os dois produtos andam juntos. O teto `<3` herdado do py-bcb caiu em 15/09, aferido pela caracterização antes de sair.
- `is_bloomberg_available()` não existe aqui; chamada real à Bloomberg só com Windows e o terminal logado.
- A chave do FRED (fallback do payroll) vem da variável `FRED_API_KEY` ou de `etc/.env`, na raiz, lido por `reports._env.get_secret`. Cada máquina tem o seu, fora do git; o modelo é `etc/env.exemplo`.

## Código

- Identificadores, mensagens de log e de erro em inglês; docstrings, comentários, rótulos de gráfico e commits em pt-BR. Docstrings antigas em inglês ficam como estão.
- `src/reports/_bloomberg.py` e `src/reports/_style.py` são cópias do `py-bcb`. Nunca importar `classes.*` — `tests/informes_eventos/test_independence.py` falha.
- Todo caminho sai de `src/reports/_paths.py`: `input/informes_eventos/`, `output/informes_eventos/`, `etc/.env` (`ENV_FILE`), `input/informes_eventos/fed/` para os documentos do Fed, e `templates/informes_eventos/` (`TEMPLATES`) para o `fomc.dotx`, o template do informe, sem corpo e só com as faixas do cabeçalho e do rodapé. `tests/informes_eventos/test_paths.py` e `test_fomc_template.py` prendem isso.
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
importar `comentario_matinal`; `tests/informes_eventos/test_independence.py` falha.

- Dois backends. O local (`src/reports/_backend_claude.py`, que se registra
  sozinho: o `_modelo.py` importa todo `_backend_*.py` do pacote sem citá-lo) chama
  `claude -p --safe-mode` sem ferramentas, mensagem pela stdin, autenticação pela
  sessão do Claude Code, `ANTHROPIC_API_KEY` fora do ambiente do subprocesso. O
  `copilot` grava a mensagem em `output/informes_eventos/copilot/`, espera o
  `/fomc-<etapa>` rodar no chat do VS Code e confere o código de leitura.
  Variável: `INFORMES_EVENTOS_BACKEND`; sem ela, o local se o `claude` estiver no
  PATH, senão o `copilot`.
- **Os prompts em `prompts/` são a fonte de verdade editorial.** Para mudar como o
  texto lê, editar `00_guia_de_estilo.md`; o prompt da etapa só quando a mecânica
  mudar. Nada de estilo fixo no Python.
- Pasta do dia: `input/informes_eventos/fomc/<AAAAMMDD>/`. Obrigatório só o statement, que a célula 3
  baixa. Opcionais: `bancos.txt` com os comentários colados dos chats da Bloomberg,
  cada bloco aberto por uma linha `Casa abaixo:` (o nome antes de "abaixo" vira a
  instituição; o research alimenta o texto principal, atribuído à casa e nunca ao
  autor); `bancos/*.pdf` e `bancos/*.txt` (nome do arquivo = nome do banco);
  `headlines.txt` e `coletiva.txt` (linha com `***` é destaque; o autor costuma colar
  os headlines direto no Word). A transcrição da coletiva é o
  `FOMCpresconf<data>.pdf` do Fed, em `input/informes_eventos/fed/committee_meeting_docs/`,
  baixado pela célula 3; a etapa pós-coletiva aceita a transcrição, os headlines ou
  os dois. A captura `market_reaction.png` (só se o Bloomberg falhar) e a `dot_plot.png`
  (reuniões com SEP) também ficam na pasta do dia. Saídas em `output/informes_eventos/reports/fomc/<AAAAMMDD>/`. Tudo fora do
  git e sob a regra de sigilo abaixo.
- Nenhum teste chama o `claude`: `subprocess.run` e o registro `BACKENDS` recebem
  dublês.

## Não mexer

Nunca ler, imprimir, comitar ou resumir `etc/.env`, `input/informes_eventos/` (pasta do
dia do FOMC, `fed/` com os PDFs do Fed e o `email_info/`, `payroll/`, `grid1.xlsx`,
`emailPayroll.xlsx`) e `output/informes_eventos/`. Referir por caminho apenas. As
respostas do modelo gravadas ali são minuta de informe: nunca ler nem resumir na
conversa.
