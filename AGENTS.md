# AGENTS.md — mkt_intelligence

Regras que valem para todos os produtos. As de cada produto estão no `AGENTS.md` da
pasta dele, e prevalecem no que for específico. Antes de mexer num produto, ler o dele.

## Estrutura

- Cada produto mora em `produtos/<nome>/` e é um projeto uv autônomo. Não há workspace, lock ou pacote comuns. Rodar `uv` sempre de dentro da pasta do produto.
- Mudança num produto não mexe noutro. Se mexer, é sinal de acoplamento — parar e perguntar.
- O portão de cada produto é o `uv run pytest` dele. Não há portão na raiz.

## Ambiente

- Só uv; nunca `pip install`. Python ≥3.14.
- `blpapi` só pelo índice explícito da Bloomberg. Bloomberg exige Windows e o terminal logado; nenhum teste a chama.
- Notebooks: `.gitattributes` liga o `nbstripout` para o repositório inteiro; instalar por clone com `uv run nbstripout --install` de dentro de qualquer produto.

## Sigilo

- Nunca comitar, ler, imprimir ou resumir: fontes do dia, saídas antes do envio, `.env`, `input/` com planilhas de e-mail ou posições.
- Nunca colar conteúdo de fonte, número de painel, minuta de comentário ou de informe em commit, issue ou qualquer coisa que saia da máquina.
- `*.pdf` e `*.docx` ficam fora do git em qualquer pasta.

## Git

- Nunca comitar nem empurrar sem pedido. Quando pedirem, commit direto na `main`; mostrar o diff e a mensagem e esperar antes de empurrar. Divergência entre local e remoto: apontar e perguntar.
- Mensagem em português, terceira pessoa do presente, até 72 caracteres, sem prefixo nem ponto final; corpo em prosa explicando o porquê. Trailers `Co-Authored-By:` e `Claude-Session:` mantidos.
