# CLAUDE.md

Este arquivo orienta o Claude Code (claude.ai/code) ao trabalhar neste repositório.

## O arquivo de instruções é o `AGENTS.md`

@AGENTS.md

É ele que reúne as regras deste repositório: o ambiente (uv apenas, Python ≥3.14,
Bloomberg no Windows), a tabela de comandos, o encadeamento dos quatro prompts, os
invariantes editoriais, a disciplina de checagem factual, o contrato de montagem do
Word, o que não se toca e o acordo de trabalho. O `tests/comentario_matinal/test_documentacao.py` afere
dos dois o que é verificável — caminhos, pastas, subcomandos, bandeiras, a janela, as
seções do guia citadas, a contagem de testes —, mas a prosa continua sendo
responsabilidade de quem escreve. Por isso o conteúdo dele não é repetido aqui: duas
cópias divergem, e a que ninguém lê é a que fica errada.

Aqui fica só o que é específico de rodar o Claude Code, mais as poucas mecânicas que
o `AGENTS.md` não detalha.

## Escolher quais testes rodar

`uv run pytest tests/comentario_matinal` é o portão do matinal — 202 testes, ~7 s,
sem Bloomberg e sem rede. O portão do repositório inteiro é `uv run pytest`, na raiz.
Enquanto se itera, dá para estreitar:

- Um arquivo: `uv run pytest tests/comentario_matinal/test_temas.py -q`
- Um teste: `uv run pytest tests/comentario_matinal/test_documentacao.py::test_o_readme_aponta_para_o_manual -q`
- Por nome, na suíte toda: `uv run pytest -q -k notebook`
- Ver a falha inteira: acrescentar `-x -vv`

Terminar sempre pelo `uv run pytest` sem filtro, na raiz — o portão do repositório
inteiro. Nunca verificar
uma alteração rodando `uv run matinal`: toda entrada do pipeline ou chama a Bloomberg,
ou grava arquivo de verdade, ou — no caso do `enviado` — destrói o trabalho do dia.

## Regras permanentes desta sessão

- **Commit direto na `main`**, contra o padrão do harness, que criaria ramo antes.
  Mostrar o diff e a mensagem e esperar antes de empurrar. Nunca resolver uma
  divergência entre local e remoto por conta própria: apontá-la e perguntar.
- **Mensagem de commit em português**, terceira pessoa do presente, uma linha de até
  72 caracteres, sem prefixo nem escopo e sem ponto final; corpo em prosa portuguesa
  explicando *por quê*. Manter os trailers `Co-Authored-By:` e `Claude-Session:`.
- **Nunca colar conteúdo de fonte, número do painel ou minuta do comentário** em
  mensagem de commit, issue, ou qualquer coisa que saia da máquina.
