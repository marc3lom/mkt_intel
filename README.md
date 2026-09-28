# mkt_intelligence

Ferramentas de apoio à disseminação de informação e inteligência da Mesa de
Investimentos (DEPIN/DIRIN — Banco Central do Brasil). Repositório privado: guarda
material que vai à diretoria.

## Produtos

| Produto | O que produz | Cadência | Pacote | Notebooks | Docs |
|---|---|---|---|---|---|
| Comentário Matinal | e-mail de abertura de mercado | diária, 7h–9h | `src/comentario_matinal` | `notebooks/comentario_matinal/` | `docs/comentario_matinal/` |
| Informes pós-evento | e-mails de inteligência após FOMC e payroll | por evento | `src/reports` | `notebooks/informes_eventos/` | `docs/informes_eventos/` |

Um projeto uv só: um `pyproject.toml`, um `uv.lock` e uma `.venv`, os três na raiz.
Instalar é `uv sync`, na raiz; tudo roda **da raiz**, inclusive `uv run jupyter lab`.
Cada produto tem `AGENTS.md` próprio em `docs/<produto>/`, importado pelo `CLAUDE.md`
da raiz. O manual de quem roda o plantão do matinal está em
`docs/comentario_matinal/plantao/`.

### Estrutura

```
mkt_intelligence/
├── pyproject.toml            # projeto único; índice da Bloomberg; ruff; pytest
├── uv.lock  .python-version  .gitignore  .gitattributes
├── AGENTS.md  CLAUDE.md  README.md
├── .env                      # fora do git
├── src/
│   ├── comentario_matinal/
│   └── reports/              # sem notebooks/ e sem input/ dentro
├── notebooks/
│   ├── comentario_matinal/   plantao.ipynb, imagens.ipynb
│   └── informes_eventos/
│       ├── fomc/             fomc_analysis.ipynb, market_reaction_grid.ipynb
│       └── payroll/          payroll_analysis.ipynb, payroll_report.ipynb,
│                             market_reaction_grid.ipynb
├── tests/
│   ├── comentario_matinal/   inclui referencia/*.png
│   └── informes_eventos/     inclui conftest.py
├── config/comentario_matinal/painel.toml
├── prompts/{comentario_matinal,informes_eventos}/
├── templates/comentario_matinal/   comentario.dotx, mercado_fechado.png
├── arquivo/comentario_matinal/AAAA/MM/AAAAMMDD.md
├── exemplos/comentario_matinal/{aprovados,rejeitados}/
├── docs/
│   ├── comentario_matinal/   AGENTS.md, CLAUDE.md, README.md, plantao/, superpowers/
│   ├── informes_eventos/     AGENTS.md, README.md, historico-py-bcb.md, superpowers/
│   └── superpowers/          specs e planos que valem para o repositório
├── input/                    # fora do git, inteiro
│   ├── comentario_matinal/   os PDFs do dia
│   └── informes_eventos/
│       ├── fomc/<AAAAMMDD>/  pasta do dia
│       ├── fed/              documentos do Fed
│       └── …                 grid1.xlsx, email_info/, payroll, entre outros
└── output/                   # fora do git, inteiro
    ├── comentario_matinal/   painel, calendário, etapas, .docx
    └── informes_eventos/     reports/fomc/<AAAAMMDD>/, payroll, fonts/
```

Dentro de `input/informes_eventos/` cada evento tem sua pasta. A exceção é `fed/`:
documentos do Fed sem data de evento, fora do pacote `src/reports/`.

## Um produto novo

1. Informe pós-evento de mesma natureza (CPI, BCE, Copom…) → subpacote de `src/reports/`, notebooks em `notebooks/informes_eventos/<evento>/`.
2. Produto de outra natureza → pacote novo em `src/<nome>/`, acrescentado a `module-name` no `pyproject.toml`, com um módulo único de caminhos e o teste de âncora correspondente; subpasta `<nome>/` em `notebooks/`, `tests/`, `docs/` (com `AGENTS.md`, importado pelo `CLAUDE.md` da raiz) e no que mais usar.
3. Dados de trabalho em `input/<nome>/` e `output/<nome>/`, que já estão fora do git. Segredo no `.env` da raiz.
4. O pacote novo não importa os outros: acrescentar a direção nova a `tests/informes_eventos/test_independence.py`.
5. Linha nova na tabela acima.
