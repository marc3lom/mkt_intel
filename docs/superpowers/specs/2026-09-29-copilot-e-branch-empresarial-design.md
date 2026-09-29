# Backend Copilot e branch empresarial — desenho

Data: 29/09/2026. Estado: aprovado em conversa, seção por seção; falta a revisão desta
spec pelo usuário.

## Objetivo

Que qualquer gestor da Mesa de Investimentos, numa máquina corporativa do BC, clone o
repositório do GitHub empresarial e rode todos os notebooks — plantão do comentário
matinal, FOMC e payroll — sem intervenção do autor e sem instalar nada além de VS Code,
Python, uv, git e GitHub. O modelo de linguagem disponível é o **GitHub Copilot Free**,
dentro do VS Code; todos os colegas têm acesso a ele (decisão explícita do usuário).

Três subprojetos, nesta ordem:

1. **Renomear para `mkt_intel`** — feito no GitHub, nos remotes e no conteúdo (commit
   `026964f`). Falta renomear a pasta local, com esta sessão fechada.
2. **Backend Copilot e notebook agnóstico** — na `main`. O `plantao.ipynb` fica
   intacto; o novo é uma cópia, `plantao_copilot.ipynb`.
3. **Branch órfão `empresarial`** — regenerado da `main` por script, levado ao GitHub
   do BC por bundle, nos moldes do `py-mpc`.

## Fora de escopo

- Adaptar o manual (`docs/comentario_matinal/plantao/`) ao Copilot: fica para uma
  segunda rodada, como a wiki do `py-mpc`. O branch leva um README próprio.
- Backend por API (Azure OpenAI ou outro): nada disso existe nas máquinas do BC hoje.
- Compartilhar o `arquivo/` entre colegas.

## 1. Backend `copilot`

### Mecânica

Um backend novo, `Copilot`, no registro `BACKENDS` de `comentario_matinal/modelo.py`, e
a mesma classe copiada em `reports/_modelo.py` (os pacotes não se importam; a cópia é
cobrada pelo `test_independence.py`). A assinatura é a dos backends atuais: recebe a
mensagem, devolve a resposta. Nada muda em `plantao.roda_etapa`, `etapas.py` ou
`fomc/core/drafting.py`.

Ao ser chamado, o backend:

1. Grava a mensagem completa em `output/<produto>/copilot/<etapa>.mensagem.md` e apaga
   um `<etapa>.resposta.md` que tenha sobrado de execução anterior.
2. Acrescenta ao fim da mensagem uma linha com um **código de leitura** aleatório e a
   instrução de abrir a resposta com `<!-- leitura: CÓDIGO -->`.
3. Escreve no stderr (que a célula mostra na hora) o que fazer: "No chat do Copilot, em
   modo agente, digite `/triagem`".
4. Espera o `<etapa>.resposta.md` aparecer, conferindo a cada segundo, até o
   `TEMPO_LIMITE` (15 min). Considera a resposta pronta quando o arquivo existe e o
   tamanho fica estável por dois segundos seguidos — o agente pode gravar em mais de um
   passo.
5. Confere o código. Ausente ou diferente, levanta `ErroDoModelo` dizendo que a mensagem
   não foi lida até o fim. Presente, tira a linha e devolve o resto.

Interromper o kernel (ou Ctrl+C no terminal) cancela a espera. Resposta vazia, depois
de tirado o código, é erro, como nos outros backends.

### Prompt files

Em `.github/prompts/`, um por etapa: `triagem.prompt.md`, `redacao.prompt.md`,
`revisao.prompt.md` (matinal) e `fomc-resumo.prompt.md`, `fomc-bancos.prompt.md`,
`fomc-revisao.prompt.md`. O nome da etapa do FOMC segue o `stage` que o `drafting.py`
passa ao backend; a lista final sai do código. Cada um:

- roda em modo agente, com ferramentas só de ler e de criar arquivo — sem terminal, sem
  web (os nomes exatos das ferramentas são conferidos contra a documentação do VS Code
  na implementação);
- manda ler `<etapa>.mensagem.md` **inteira, até a última linha**, em quantas leituras
  forem precisas;
- manda seguir as instruções da mensagem como se fossem o pedido, sem perguntar nada e
  sem preâmbulo — o equivalente ao `SYSTEM_PROMPT` do backend Claude, que passa a ser
  texto compartilhado;
- manda gravar a resposta, e só ela, em `<etapa>.resposta.md`, sem tocar em nenhum outro
  arquivo.

O prompt file é mecânica; o conteúdo editorial continua nos prompts de `prompts/`,
que viajam dentro da mensagem. Nenhuma regra de estilo entra em `.github/prompts/`.

### Escolha do backend

Precedência: a variável de ambiente (`COMENTARIO_MATINAL_BACKEND`,
`INFORMES_EVENTOS_BACKEND`); sem ela, `claude-code` se o executável `claude` estiver no
PATH; senão `copilot`. A máquina do autor continua igual; as do BC caem no Copilot sem
configuração. O `plantao_copilot.ipynb` fixa `copilot` na primeira célula, para poder
ser exercitado também na máquina do autor.

### O backend Claude em módulo próprio

`ClaudeCode` sai de `modelo.py` para `comentario_matinal/_claude.py`, e de `_modelo.py`
para `reports/_claude.py`. O registro o importa só se o módulo existir. É o que permite
ao branch empresarial não conter menção alguma ao Claude, sem ramificar código. Os
comentários de `modelo.py`, `_modelo.py` e `cli.py` que citam o Claude são reescritos em
termos de "backend".

## 2. Comentário do dia anterior em PDF

O comentário anterior já é opcional (prompts de triagem e revisão, e
`etapas.comentario_anterior`). Acrescenta-se uma segunda origem: um PDF em
`input/comentario_matinal/` cujo nome comece por `anterior` (sem distinção de caixa)
sai da conversão das fontes (`fontes.converte`) e vai para o slot
**COMENTÁRIO DO DIA ANTERIOR**. Misturado às fontes, ele seria lido como notícia do dia
e poderia virar tema (§5.2 do guia).

Precedência: o `.md` de `arquivo/` quando existe; senão o PDF; senão nada, e a etapa
segue só com as fontes, como hoje. O aviso de progresso diz de onde o anterior veio.

## 3. Chave do FRED sem 1Password

`reports/_onepassword_env.py` e a dependência `onepassword-sdk` saem. A leitura passa a
ser: variável de ambiente `FRED_API_KEY`; senão `etc/.env`, na raiz; senão um erro que
diz qual arquivo criar, com qual linha, e onde se obtém a chave. O parser do `.env` é
mínimo (`CHAVE=valor`, comentário com `#`), sem dependência nova. `etc/.env` fica fora
do git; `etc/.env.exemplo` é versionado — o `.gitignore` atual ignora `.env.*` e só
libera `.env.example`, então ganha a exceção `!.env.exemplo`. O caminho vem de
`reports/_paths.py`, como todo caminho do pacote; o `ENV_FILE` de lá, que hoje aponta
para `.env` na raiz, passa a apontar para `etc/.env`.

## 4. Template e capturas do FOMC

- O template sai do OneDrive (`word_report.py:26`) para
  `templates/informes_eventos/fomc.dotx`, gerado a partir do `.docx` atual com o corpo
  esvaziado — ficam cabeçalho, rodapé, estilos e margens; nenhum texto de informe
  enviado entra no repositório. Abertura pela troca de content type, como o
  `documento.py` do matinal. Fecha a questão em aberto do `docs/informes_eventos/AGENTS.md`.
- `MARKET_REACTION_PNG` e `DOT_PLOT_PNG`, no `fomc_analysis.ipynb`, deixam de apontar
  para o OneDrive e passam a ser procurados na pasta do dia,
  `input/informes_eventos/fomc/<AAAAMMDD>/`.

## 5. O notebook `plantao_copilot.ipynb`

Cópia do `plantao.ipynb`, com os mesmos passos e as mesmas chamadas ao núcleo. Muda:

- a primeira célula fixa `COMENTARIO_MATINAL_BACKEND=copilot`;
- os textos das células de etapa explicam o `/triagem`, `/redacao`, `/revisao` e a
  espera, e o que fazer se o Copilot não gravar a resposta;
- o Passo 1 menciona o `anterior*.pdf`;
- nenhuma menção ao Claude.

O `test_notebook.py` passa a cobrar os dois notebooks: cada passo e parâmetro do núcleo
exercitado em ambos, ou listado como exceção com o motivo.

## 6. Branch `empresarial`

### Seleção

`scripts/build_enterprise_branch.py`, adaptado do `py-mpc`. A regra vive só ali:

| Entra | Sai |
|---|---|
| `src/`, menos `_claude.py` (dos dois pacotes) e `comentario_matinal/wiki.py` | `tests/`, `scripts/`, `docs/`, `AGENTS.md`, `CLAUDE.md` |
| `notebooks/`, menos `comentario_matinal/plantao.ipynb` | `.superpowers/`, `.claude/`, `exemplos/`, `arquivo/` |
| `prompts/`, menos `comentario_matinal/project_instructions.md` | |
| `templates/`, `config/`, `.github/prompts/`, `etc/.env.exemplo` | |
| `pyproject.toml` sem a linha `publica-wiki`; `uv.lock`; `.python-version` | |
| `.gitattributes`; `.gitignore` sem linhas do Claude e com `/arquivo/` e `/etc/.env` | |
| `README_empresarial.md` da `main`, publicado como `README.md` | |

### Mecânica (igual ao `py-mpc`)

- Lê do commit da `main`, nunca da árvore de trabalho; índice temporário.
- Um commit por regeneração, sobre a ponta do branch (push sempre fast-forward); nada
  muda, nada commita.
- Mensagem sem trailer e sem menção a ferramenta; autor e committer com o e-mail de
  `git config empresarial.email`; assina se `commit.gpgsign` estiver ligado.
- `--dry-run` mostra o que mudaria; `--bundle` grava `output/empresarial.bundle`.
- **Diferença**: qualquer ocorrência de "claude" (sem distinção de caixa) num arquivo
  selecionado **aborta** a geração, em vez de só avisar.

### `arquivo/` local

Cada máquina mantém o seu: o `matinal enviado` continua arquivando, e o `.gitignore` do
branch impede que um comentário enviado seja comitado por engano. Continuidade entre
colegas, quando houver, é pelo `anterior*.pdf`.

### README do branch

Instalação (`git clone`, `uv sync`, `uv run nbstripout --install`, `etc/.env` com a
chave do FRED, kernel `.venv` no VS Code, login no Copilot), o fluxo de cada notebook
com o Copilot, a regra de sigilo (nunca comitar `input/`, `output/`, `etc/.env`), e
problemas conhecidos: Bloomberg sem `bbcomm`, proxy do git, código de leitura ausente.

## Testes e validação

- Backend `copilot`: com arquivo de resposta simulado, gravado por uma thread do teste —
  resposta com código certo (devolve o texto sem a linha), código errado ou ausente
  (erro), resposta vazia (erro), tempo esgotado (erro, com teto reduzido no teste),
  resposta velha apagada antes de esperar. O mesmo para a cópia em `reports`.
- Escolha do backend: variável presente, `claude` no PATH, ausente (com `shutil.which`
  dublado).
- `anterior*.pdf`: sai das fontes, entra no slot, perde para o `.md` arquivado.
- FRED: variável, `etc/.env`, nenhum dos dois (mensagem de erro).
- Template do FOMC: o `.dotx` abre e não tem parágrafo de corpo com texto.
- Script do branch: funções puras de seleção e de reescrita (`.gitignore`,
  `pyproject.toml`), e o aborto por menção ao Claude.
- Validação do branch gerado, num worktree descartável: `uv sync --frozen`, importação
  dos pacotes, nenhuma ocorrência de "claude" na árvore.
- Portão: `uv run pytest`, na raiz.
- O teste real — Copilot e Bloomberg — é do autor, no notebook do BC.

## Transporte ao GitHub do BC

Como no `py-mpc`: repositório `mkt_intel` criado pelo autor na organização do BC;
bundle levado ao notebook do BC; lá, `fetch` do bundle, commit assinado e push. O push
para o BC é ação externa, sempre do autor.
