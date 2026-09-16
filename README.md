# mkt_intelligence

Ferramentas de apoio à disseminação de informação e inteligência da Mesa de
Investimentos (DEPIN/DIRIN — Banco Central do Brasil). Repositório privado: guarda
material que vai à diretoria.

## Produtos

| Produto | O que produz | Cadência | Pasta |
|---|---|---|---|
| Comentário Matinal | e-mail de abertura de mercado | diária, 7h–9h | `produtos/comentario_matinal/` |
| Informes pós-evento | e-mails de inteligência após FOMC e payroll | por evento | `produtos/informes_eventos/` |

Cada produto tem `pyproject.toml`, testes e `AGENTS.md` próprios, e é membro do
workspace uv da raiz: um `uv.lock` e uma `.venv`, as duas na raiz. Instalar é
`uv sync --all-packages` na raiz; o resto roda **de dentro da pasta do produto**. O manual de quem
roda o plantão do matinal está em `produtos/comentario_matinal/docs/plantao/`.

## Um produto novo

1. Informe pós-evento de mesma natureza (CPI, BCE, Copom…) → subpacote de `reports` em `produtos/informes_eventos/`.
2. Produto de outra natureza → pasta nova `produtos/<nome>/`, com `uv init`, `.python-version` 3.14, `pyproject.toml`, `tests/`, `AGENTS.md` e `CLAUDE.md` com `@AGENTS.md`. O `members = ["produtos/*"]` da raiz o adota sozinho, e o índice da Bloomberg já está lá.
3. Dados de trabalho e segredos ficam fora do git: `.gitignore` do produto com `input/`, `output/`, `saida/` ou o que couber.
4. Linha nova na tabela acima.
5. Um `produtos/_comum/` só nasce quando um terceiro produto precisar do mesmo código.
