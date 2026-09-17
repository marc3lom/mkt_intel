# informes_eventos

Informes pós-evento da Mesa de Investimentos (DEPIN/DIRIN): FOMC e payroll.
Cada informe é um notebook que coleta os dados, gera os gráficos e monta o `.docx`.

| Informe | Notebook principal |
|---|---|
| FOMC | `src/reports/fomc/notebooks/fomc_analysis.ipynb` |
| Grid de reação ao FOMC | `src/reports/fomc/notebooks/market_reaction_grid.ipynb` |
| Payroll | `src/reports/payroll/notebooks/payroll_report.ipynb` |
| Grid de reação ao payroll | `src/reports/payroll/notebooks/market_reaction_grid.ipynb` |

Instalação: `uv sync`, depois `op inject -i .env.tpl -o .env`.
Regras para quem mexe no código: `AGENTS.md`. Histórico das decisões: `docs/historico-py-bcb.md`.
