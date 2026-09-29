# AGENTS.md — mkt_intel

Regras que valem para todos os produtos. As de cada produto estão em
`docs/<produto>/AGENTS.md`, e prevalecem no que for específico. Antes de mexer num
produto, ler o dele.

## Estrutura

- Um projeto uv só: um `pyproject.toml`, um `uv.lock` e uma `.venv`, os três na raiz. **Instalar é `uv sync`, na raiz.**
- As pastas da raiz são por tipo, com subpasta por produto onde couber: `src/` (pacotes `comentario_matinal` e `reports`), `notebooks/`, `tests/`, `config/`, `prompts/`, `templates/`, `arquivo/`, `exemplos/`, `docs/`.
- `input/<produto>/` é tudo o que entra e `output/<produto>/` é tudo o que sai; as duas ficam fora do git, inteiras. `arquivo/` não é saída: é o registro versionado do que foi enviado.
- Um pacote não importa o outro. Código igual nos dois é cópia (`reports/_modelo.py`), e `tests/informes_eventos/test_independence.py` cobra. Se uma mudança num produto pedir mexer no outro, é sinal de acoplamento — parar e perguntar.
- Caminho se acha num lugar por pacote: `comentario_matinal/config.py` e `reports/_paths.py`. Nenhum outro módulo lê `__file__`; os testes de âncora cobram.
- O portão é `uv run pytest`, na raiz. Para um produto só: `uv run pytest tests/<produto>`.

## Ambiente

- Só uv; nunca `pip install`. Python ≥3.14.
- `blpapi` só pelo índice explícito da Bloomberg. Bloomberg exige Windows e o terminal logado; nenhum teste a chama.
- Notebooks: `.gitattributes` liga o `nbstripout` para o repositório inteiro; instalar por clone com `uv run nbstripout --install`, na raiz. Rodar: `uv run jupyter lab` na raiz, ou o kernel `.venv` no VS Code.

## Sigilo

- Nunca comitar, ler, imprimir ou resumir: `input/`, `output/` e `.env`.
- Nunca colar conteúdo de fonte, número de painel, minuta de comentário ou de informe em commit, issue ou qualquer coisa que saia da máquina.
- `*.pdf` e `*.docx` ficam fora do git em qualquer pasta.

## Git

- Nunca comitar nem empurrar sem pedido. Quando pedirem, commit direto na `main`; mostrar o diff e a mensagem e esperar antes de empurrar. Divergência entre local e remoto: apontar e perguntar.
- Mensagem em português, terceira pessoa do presente, até 72 caracteres, sem prefixo nem ponto final; corpo em prosa explicando o porquê. Trailers `Co-Authored-By:` e `Claude-Session:` mantidos.
