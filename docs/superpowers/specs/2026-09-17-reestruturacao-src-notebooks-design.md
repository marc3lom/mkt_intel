# Reestruturação do repositório: `src/` e `notebooks/` na raiz, projeto único

**Data:** 17/09/2026
**Produto:** o repositório inteiro (`comentario_matinal` e `informes_eventos`)
**Estado:** aprovado em conversa; aguardando revisão da spec escrita

## 1. Problema

O repositório é um workspace uv com dois membros em `produtos/<nome>/`, cada um
com seu `pyproject.toml`, seu `src/`, seus testes, seus recursos e suas pastas
de trabalho. A `.venv` e o `uv.lock` já são únicos e ficam na raiz, mas o resto
do layout é por produto, e isso cobra três preços:

- Quem usa o repositório pelos notebooks precisa saber em que pasta de produto
  entrar, e os cinco notebooks do informes moram **dentro do pacote**
  (`src/reports/<evento>/notebooks/`), com um `sys.path.insert` para achar o
  código que já está instalado.
- Instalar é `uv sync --all-packages` na raiz; `uv sync` de dentro de um
  produto poda a `.venv`. A armadilha está documentada, mas continua armada.
- Entradas e saídas do dia se espalham por cinco lugares com nomes diferentes:
  `fontes/` e `saida/` no matinal; `input/`, `output/`, `etc/` e
  `src/reports/fomc/input/` no informes — este último, dado sigiloso dentro do
  pacote.

O objetivo é um layout em que a raiz tenha `src/` com todo o código e
`notebooks/` com todos os notebooks, um projeto só, um ambiente só, e um
endereço só para o que entra e para o que sai.

## 2. Alcance

Entra:

- Projeto único na raiz, sem workspace; `src/` com os dois pacotes.
- `notebooks/`, `tests/`, `config/`, `prompts/`, `templates/`, `arquivo/`,
  `exemplos/` e `docs/` na raiz, cada um com subpasta por produto.
- `input/` e `output/` na raiz, fora do git, com subpasta por produto.
- Âncora única de caminhos por pacote, aferida por teste.
- Reescrita do `.gitignore`, dos `AGENTS.md`/`CLAUDE.md`, dos `README.md` e do
  manual do plantão no que citam caminho ou comando.

Fica de fora, de propósito:

- Renomear pacotes ou imports (`comentario_matinal` e `reports` ficam).
- Fundir código dos dois produtos. `reports/_modelo.py` continua cópia do
  `modelo.py` do matinal; a independência continua valendo.
- Portão de lint para o matinal, ou conserto dos erros de `ruff` que ele acusa.
- O template do FOMC em caminho absoluto do OneDrive
  (`fomc/core/word_report.py`), questão em aberto do informes.
- Qualquer mudança de comportamento do pipeline, dos prompts ou do guia.

## 3. Decisões que orientam o desenho

1. **Projeto único, não workspace.** Um `pyproject.toml`, dependências unidas,
   `uv sync` simples. O lock já resolve os dois produtos juntos (pandas 3,
   Python ≥3.14); a fronteira de dependências entre eles já era nominal.
2. **Pastas por tipo na raiz, subpasta por produto.** `prompts/informes_eventos/`,
   e não `produtos/informes_eventos/prompts/`. O diretório `produtos/` desaparece.
3. **`input/` e `output/`, em inglês, o par inteiro.** É a convenção mais comum
   para pipeline de relatório, o informes já usa esses nomes, e combina com o
   resto da raiz (`src`, `tests`, `docs`, `notebooks`).
4. **`arquivo/` não é saída.** `output/` é efêmero, regenerável, sigiloso e fora
   do git; `arquivo/` é o registro institucional dos comentários enviados,
   versionado e escrito só pelo `matinal enviado`. Ficam separados para que a
   regra de sigilo seja "`/output/` inteiro ignorado", sem lista de exceções.
5. **A independência deixa de ser física e passa a ser testada.** Sem pasta de
   produto, o que impede um pacote de importar o outro é o
   `test_independence.py`, que passa a vigiar as duas direções.
6. **Migração em fases, portão verde a cada commit, tudo com `git mv`.** Um
   commit único não se bisecta e perde o histórico dos arquivos.

## 4. Árvore-alvo

```
mkt_intelligence/
├── pyproject.toml            # projeto único; índice da Bloomberg; ruff; pytest
├── uv.lock  .python-version  .gitignore  .gitattributes
├── AGENTS.md  CLAUDE.md  README.md
├── .env.tpl                  # versionado: referências do 1Password
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
│   ├── comentario_matinal/   AGENTS.md, plantao/, superpowers/
│   ├── informes_eventos/     AGENTS.md, historico-py-bcb.md, superpowers/
│   └── superpowers/          specs e planos que valem para o repositório
├── input/                    # fora do git, inteiro
│   ├── comentario_matinal/   os PDFs do dia (a antiga fontes/)
│   └── informes_eventos/
│       ├── fomc/<AAAAMMDD>/  pasta do dia
│       ├── fed/              documentos do Fed (hoje src/reports/fomc/input/)
│       └── …                 grid1.xlsx, email_info/, payroll — como hoje
└── output/                   # fora do git, inteiro
    ├── comentario_matinal/   painel, calendário, etapas, .docx (a antiga saida/)
    └── informes_eventos/     reports/fomc/<AAAAMMDD>/, payroll, fonts/
```

Dentro de `input/informes_eventos/` e `output/informes_eventos/` a estrutura
interna é a de hoje; só o prefixo muda. A exceção é `fed/`, que sai de dentro
do pacote.

## 5. Ambiente

- `[project] name = "mkt-intelligence"`, `requires-python = ">=3.14"`,
  dependências = união das duas listas, com o piso mais alto onde divergem
  (`pandas>=3.0`). Os comentários que explicam cada dependência acompanham.
- `[project.scripts]`: `matinal` e `publica-wiki`, inalterados.
- `[dependency-groups] dev`: pytest, ruff, jupyter, ipykernel, nbformat,
  nbstripout.
- Build: `uv_build`, `module-root = "src"`,
  `module-name = ["comentario_matinal", "reports"]`. O uv em uso (0.12) aceita
  lista; o plano confirma com um `uv build` antes de seguir. Se falhar, troca-se
  o backend por hatchling, sem efeito no resto do desenho.
- `[tool.uv.sources]` e `[[tool.uv.index]]` da Bloomberg ficam como estão;
  sai só o `[tool.uv.workspace]`.
- `.python-version` único na raiz.
- Instalar: `uv sync` na raiz, depois `uv run nbstripout --install`.
- Notebooks: `uv run jupyter lab` na raiz, ou o kernel `.venv` no VS Code. O
  projeto é instalado em modo editável, então `from reports… import` e
  `from comentario_matinal import …` resolvem sem `sys.path`.

## 6. Caminhos

Hoje o código acha a raiz do produto contando níveis de `__file__` em dez
pontos de oito módulos. Qualquer mudança de profundidade quebra isso em silêncio, e é esse o
risco principal da migração. A contagem passa a existir em **um lugar por
pacote**.

**`comentario_matinal`** — `config.py` já centraliza. `RAIZ` passa a ser a raiz
do repositório (`parents[2]`) e as constantes ganham o sufixo do produto:

| Constante | Valor novo |
|---|---|
| `CONFIG_PADRAO` | `RAIZ/config/comentario_matinal/painel.toml` |
| `TEMPLATE_PADRAO`, `MERCADO_FECHADO` | `RAIZ/templates/comentario_matinal/…` |
| `PROMPTS` | `RAIZ/prompts/comentario_matinal` |
| `ARQUIVO_PADRAO` | `RAIZ/arquivo/comentario_matinal` |
| `FONTES_PADRAO` | `RAIZ/input/comentario_matinal` |
| `SAIDA_PADRAO` | `RAIZ/output/comentario_matinal` |

Os nomes das constantes não mudam; só os valores. `wiki.py` deixa de recalcular
a raiz e importa `RAIZ` de `config`; `DESTINO_PADRAO` passa a `RAIZ.parent /
"mkt_intelligence.wiki"`, o mesmo diretório de hoje.

**`reports`** — módulo novo `reports/_paths.py` com `ROOT`, `INPUT`, `OUTPUT`,
`FED_DOCS`, `PROMPTS` e `ENV_FILE`. Passam a importar dele:
`fomc/core/drafting.py`, `fomc/core/data_loader.py` (dois pontos),
`fomc/core/word_export.py`, `fomc/core/fed_scraper.py`, `_style.py` e
`payroll/core/data_loader.py`. `ENV_FILE` é `ROOT/.env`.

**Notebooks do informes** — sai o bloco `project_root` + `sys.path.insert`; o
que ainda precisar da raiz importa `ROOT` de `reports._paths`.

**Pastas ignoradas não existem num clone novo.** O código que grava cria
`output/<produto>/…` sob demanda (`mkdir(parents=True, exist_ok=True)`); o
README manda criar `input/<produto>/`.

## 7. Sigilo

- `.gitignore`: `/input/` e `/output/`, ancoradas na raiz. Continuam, como
  segunda barreira, `*.pdf`, `*.docx`, `.env`, `.env.*` com `!.env.tpl` e
  `!.env.example`, `painel.txt`. Saem as regras sem âncora `saida/` e `fontes/`
  e o `.gitignore` do informes.
- As pastas sigilosas mudam de lugar por `mv` no disco, sem que o conteúdo seja
  lido, listado ou impresso. São: `fontes/`, `saida/`, `input/`, `output/`,
  `etc/.env` e `src/reports/*/input/`.
- Antes de cada commit da migração: `git status --porcelain` sem nada sob
  `input/` ou `output/`, e `git check-ignore` positivo para um caminho de cada.
- As regras de "Não mexer" dos dois `AGENTS.md` são reescritas com os caminhos
  novos, sem afrouxar nenhuma.

## 8. Testes, lint e independência

- Portão único: `uv run pytest` na raiz. `testpaths = ["tests"]`,
  `addopts = "-ra --strict-markers --import-mode=importlib"` — há
  `test_modelo.py` nos dois produtos, e sem o modo importlib os nomes colidem.
  Rodar um produto só: `uv run pytest tests/<produto>`.
- `ruff` restrito a `src/reports` e `tests/informes_eventos`, com a configuração
  atual do informes (que já exclui `*.ipynb`). O matinal segue sem portão de lint.
- `test_independence.py` afere as duas direções, em `src/` e em `notebooks/`:
  nada de `reports` importa `comentario_matinal`, nada de `comentario_matinal`
  importa `reports`, e nada importa `classes`.
- Teste de âncora por pacote: a raiz derivada contém `pyproject.toml`, e cada
  pasta versionada derivada dela existe. `TestProjectRootAnchors` é reescrito
  sobre `_paths`; o matinal ganha o equivalente sobre `config`.
- `test_documentacao.py`, `test_notebook.py` e `test_reports_fomc.py` prendem
  nomes de pasta, caminhos de notebook e a contagem de testes anunciada no
  `AGENTS.md`. São atualizados na mesma fase em que o caminho muda. A contagem
  passa a ser a do produto (`tests/comentario_matinal`), não a do repositório.

## 9. Instruções de agente e documentação

- `AGENTS.md` da raiz: estrutura nova; instalar é `uv sync`; o portão é o
  `uv run pytest` da raiz; "mudança num produto não mexe noutro" vira "um pacote
  não importa o outro, e `test_independence.py` cobra".
- Os `AGENTS.md` de produto vão para `docs/<produto>/AGENTS.md` e o `CLAUDE.md`
  da raiz os importa com `@`. Sem pasta de produto, o carregamento automático
  por diretório deixa de funcionar; dentro de `src/` eles seriam empacotados.
  O `CLAUDE.md` do matinal, que tem conteúdo próprio e é aferido pelo
  `test_documentacao.py`, vai junto para `docs/comentario_matinal/CLAUDE.md` e é
  importado do mesmo jeito; o do informes, que só importa o `AGENTS.md`, some.
- `README.md` único na raiz, com seção por produto; os `README.md` de produto
  viram `docs/<produto>/README.md` se tiverem conteúdo que não caiba.
- Manual do plantão (`docs/comentario_matinal/plantao/`): `fontes/` →
  `input/comentario_matinal/`, `saida/` → `output/comentario_matinal/`, e os
  exemplos de comando que citam `saida/comentario_AAAAMMDD.md`. É prosa conferida
  por teste; muda junto com o teste.
- Memória do Claude (`repo-mkt-intelligence.md`): atualizada ao fim.
- A wiki publicada é regenerada por `uv run publica-wiki` depois da migração,
  fora do plantão, a pedido.

## 10. Migração

Sete fases, cada uma um commit com `uv run pytest` verde, todas com `git mv`.

1. **Âncoras, sem mover nada.** `reports/_paths.py`, `wiki.py` sobre
   `config.RAIZ`, testes de âncora. Refatoração pura no layout atual.
2. **Projeto único.** `pyproject.toml` da raiz absorve os dois; somem os dos
   produtos e o workspace; `uv lock`, `uv sync`, `uv build` de conferência;
   pytest na raiz com `testpaths` ainda apontando para `produtos/*/tests`.
3. **`src/`.** Move os dois pacotes; ajusta as âncoras para a profundidade nova.
   Nesta fase os recursos ainda estão em `produtos/`, então as constantes
   apontam para lá.
4. **`notebooks/`.** Move os sete, tira o `sys.path`, ajusta os testes que
   prendem o caminho dos notebooks.
5. **Recursos versionados.** `tests/`, `config/`, `prompts/`, `templates/`,
   `arquivo/`, `exemplos/`, `docs/`; constantes e `testpaths` passam aos valores
   finais.
6. **`input/` e `output/`.** `mv` no disco do material sigiloso, `.env` para a
   raiz, `.gitignore` novo, conferência de sigilo da seção 7.
7. **Documentação.** `AGENTS.md`, `CLAUDE.md`, `README.md`, manual do plantão,
   memória; remove o que sobrar de `produtos/`.

Pré-condições: árvore de trabalho limpa — o `notebooks/imagens.ipynb` está
modificado e não comitado, e isso se resolve antes da fase 1; fora da janela
7h00–9h00; longe de dia de evento (próximo FOMC em 28/10/2026). Nenhuma fase é
empurrada sem o diff e a mensagem mostrados antes.

## 11. Critérios de aceite

- `produtos/` não existe; `git ls-files` não lista nada sob `input/` nem `output/`.
- Num clone limpo, `uv sync` + `uv run pytest` passam, sem Bloomberg e sem rede.
- `uv run matinal --help` e `uv run publica-wiki --help` respondem a partir da
  raiz e de uma subpasta.
- Os sete notebooks compilam (os testes que já os compilam continuam valendo) e
  nenhum contém `sys.path`.
- `git log --follow` num arquivo movido chega ao histórico anterior.
- `uv run ruff check` e `ruff format --check` no escopo do informes saem como
  saíam antes.
- Conferência manual, com o terminal logado e fora do plantão: `uv run matinal
  imagens` grava em `output/comentario_matinal/`, e a primeira célula de dados
  do `fomc_analysis.ipynb` lê de `input/informes_eventos/`.

## 12. Riscos

- **Caminho quebrado em silêncio.** Mitigado pela fase 1 (âncora antes de
  mover) e pelos testes de âncora; o que os testes não cobrem é a chamada real
  à Bloomberg, daí a conferência manual do aceite.
- **Material sigiloso rastreado por engano** na troca do `.gitignore`. Mitigado
  pela conferência obrigatória antes de cada commit e pelas barreiras por
  extensão, que não saem.
- **`arquivo/` renomeado.** O nome do arquivo é a data de envio e a busca pelo
  dia anterior o lê; só o prefixo do diretório muda, por `git mv`, e o teste de
  orquestração que exercita essa busca tem de continuar verde.
- **Acoplamento futuro.** Com tudo num `src/`, importar o vizinho fica a um
  `import` de distância. `test_independence.py` é a única barreira; a regra vai
  escrita no `AGENTS.md` da raiz.
