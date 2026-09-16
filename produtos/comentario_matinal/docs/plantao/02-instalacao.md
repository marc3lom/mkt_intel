# Configuração inicial (uma vez)

Uma vez por máquina, antes do primeiro plantão. Leva alguns minutos e não exige o
terminal Bloomberg aberto — a instalação não fala com ele; a execução do comando, sim.

Faça isto na véspera, não às 7h de um dia em que você está de plantão.

## O que precisa estar na máquina

Cinco coisas, e o plantão para sem qualquer uma delas.

**1. Windows nativo.** Não WSL. O `blpapi` conversa com o terminal Bloomberg por IPC
local, e do WSL ele não alcança. Vale para a execução; a instalação você faz de onde
quiser, mas não há razão para instalar duas vezes.

**2. O `git`.** É como o repositório chega à máquina, e como o comentário arquivado
volta para o repositório depois. Uma máquina recém-formatada não tem. Baixar de
[git-scm.com](https://git-scm.com/download/win) e conferir com `git --version`.

Vale instalar junto o **GitHub CLI** ([cli.github.com](https://cli.github.com/)): o
`gh auth login` resolve a credencial do GitHub numa passagem só, sem chave SSH.

**3. O `uv`.** É o gerenciador de ambiente e é como tudo neste repositório roda — daí
todo comando começar por `uv run`. Instalar pelo PowerShell:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fechar e reabrir o terminal depois, para que o PATH seja relido. Conferir com
`uv --version`.

**4. O `claude`, autenticado.** É o backend das três etapas de IA — os passos 2, 4 e 6
do runbook. Sem ele no PATH, o plantão para na triagem.

Instalar pelo PowerShell:

```
irm https://claude.ai/install.ps1 | iex
```

Quem já tem Node.js na máquina pode usar `npm install -g @anthropic-ai/claude-code`.
A documentação de instalação e autenticação está em
[docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code).

Depois de instalar, rodar `claude` uma vez, no terminal, e concluir o login. A
autenticação fica gravada na máquina e não se repete a cada plantão. Conferir com
`claude --version`, e conferir que ele responde: `claude -p "responda ok"`.

O acesso ao modelo está hoje em assinatura pessoal — ver as notas do
[`README.md`](../../README.md) do produto sobre a migração para o ambiente corporativo.

**5. O Word.** O Passo 7 monta um `.docx` a partir de `templates/comentario.dotx`, e é
no Word que você insere o gráfico do dia — opcional, colado à mão, e nunca gerado pelo
comando —, confere o documento e **exporta o PDF** que vai anexado ao e-mail. O comando
não gera o PDF, e não há caminho sem esse passo manual.

## Clonar o repositório

**O repositório é privado**, e segue assim por ora. Ele guarda comentários
institucionais já enviados à diretoria, e o acesso não é público. Sem permissão, o
`git clone` responde que o repositório não existe — é assim que o GitHub nega leitura a
quem não tem acesso, e não significa que você errou o endereço.

**Para obter acesso, peça ao dono do repositório** — o `marc3lom` do endereço abaixo. Ele
concede **acesso de colaborador** a quem na divisão quiser, e é esse acesso que torna o
clone possível. Não há processo além de pedir.

```
gh repo clone marc3lom/mkt_intelligence
```

Sem o GitHub CLI, o equivalente é
`git clone https://github.com/marc3lom/mkt_intelligence.git`.

**Este endereço é provisório.** O destino é um espelho no GitHub corporativo da
instituição, e a URL muda quando ele existir. Se o comando acima falhar por endereço
inválido num dia futuro, a explicação mais provável é essa, e não um erro seu — procure
o endereço novo antes de tratar o caso como problema de acesso.

O repositório reúne vários produtos da divisão, cada um na sua pasta. O comentário
matinal é um deles, e **todos os comandos abaixo rodam de dentro da pasta dele**:

```
cd mkt_intelligence\produtos\comentario_matinal
```

## A instalação

O plantão inteiro roda deste repositório. Não é preciso criar Project algum: as três
etapas de IA montam a mensagem com o guia de estilo e o prompt da etapa embutidos, a
partir dos arquivos de `prompts/`. O Project continua existindo como caminho
alternativo — ver [O Project do Claude](#o-project-do-claude), mais abaixo.

Três comandos:

1. Instalar as dependências, **da raiz do clone**: `uv sync --all-packages`.
2. Instalar o filtro de notebook: `uv run nbstripout --install`.
3. Criar a pasta das fontes: `mkdir fontes` (ver abaixo por que ela não vem no clone).

O passo 2 vale por clone, e é o que impede que um notebook executado leve para o
commit os dados de mercado e o texto do comentário — possivelmente antes de ele ter
sido enviado. O filtro tira as saídas no `git add`, sem tocar no arquivo aberto na
tela. Sem ele nada avisa na hora: quem percebe é o `tests/test_notebook.py`, que
existe como rede para o clone em que o passo foi esquecido.

O `uv sync --all-packages` cria a `.venv` — uma só, na raiz, para os dois produtos — e
instala tudo, inclusive o `blpapi`, que não vem do PyPI —
o `pyproject.toml` já aponta para o índice da Bloomberg. Rodar sempre do Windows nativo,
nunca do WSL: o `blpapi` conversa com o terminal por IPC local. A instalação não exige
terminal aberto; a execução do comando, sim.

### As pastas que não vêm no clone

`fontes/` e `saida/` estão no `.gitignore` e **não existem depois de clonar**. É de
propósito: uma guarda os PDFs da Bloomberg, que não entram no repositório, e a outra
guarda as saídas do dia, que são refeitas toda manhã.

Isso importa porque o Passo 1 manda salvar os PDFs do dia **dentro de `fontes/`**, e a
pasta não está lá. Criá-la à mão, na pasta do produto — ao lado de `prompts/` — não
dentro de `notebooks/`, que é o engano fácil de quem roda pelo notebook: os caminhos
padrão são ancorados na pasta do produto, e uma `fontes/` no lugar errado faz a etapa
avisar que não aproveitou PDF algum, sem dizer por quê. A `saida/` o próprio comando
cria.

## O ensaio que fecha a instalação

Instalado não é o mesmo que funcionando. Rodar o plantão inteiro uma vez, **fora da
janela de 7h–9h** — de tarde, na véspera. Fora da janela toda execução é ensaio: o
comando produz todos os artefatos e carimba o painel com `PAINEL DIRECIONAL — DRY RUN`.
Nada é enviado, e nada é bloqueado.

Com o terminal Bloomberg aberto e logado, e um PDF qualquer em `fontes/`:

```
uv run matinal
uv run matinal triagem
```

O primeiro exercita a instalação inteira do lado da Bloomberg — `blpapi`, licença,
IPC — e deve gravar quatro arquivos em `saida/`. O segundo exercita o `claude`, que é
a outra metade que pode faltar. Se os dois passaram, sua máquina está pronta.

Ensaiar até o fim — redação, revisão, montagem do `.docx` — é melhor ainda, e é a única
forma de descobrir que o Word não abre o documento numa manhã que não seja a sua
primeira. O único passo que **não** se ensaia é o `uv run matinal enviado`: ele afirma
que o e-mail foi enviado, e arquiva.

Deu erro? [Quando dá errado](05-quando-da-errado.md) lista o sintoma exato de cada
falha desta lista.

## Manter o guia de estilo

Sempre que uma convenção mudar, editar `prompts/00_guia_de_estilo.md` e comitar. O
comando lê o arquivo do disco a cada execução, então a mudança vale no plantão
seguinte, sem mais nenhum passo. Quem usa o Project precisa substituir o arquivo lá
também. Não editar convenções nos prompts de etapa — eles apenas referenciam o guia.

## O Wiki (passo único de quem publica o manual)

Só quem publica o manual precisa disto — não é parte da instalação de quem só roda o
plantão. `uv run publica-wiki` copia `docs/plantao/` para o Wiki do GitHub, mas o
GitHub só cria o repositório `mkt_intelligence.wiki.git` **depois que a primeira
página nasce pela interface web**. Antes disso, `git clone` (e portanto o publicador)
responde que o repositório não existe — verificado em 17/08.

Para destravar: abrir a aba **Wiki** do repositório no GitHub, clicar em **Create the
first page**, salvar qualquer conteúdo. A partir daí `mkt_intelligence.wiki.git`
existe, e `uv run publica-wiki` funciona — é ele que sobrescreve essa primeira página
com o manual de verdade.

## O Project do Claude

O Project é caminho alternativo, para o dia em que o comando não está à mão — máquina
sem o `claude` no PATH, terminal indisponível, etapa feita fora do posto. Os prompts
são exatamente os mesmos; o que o comando evita é o trabalho de anexar os arquivos e
o risco de anexar a versão errada.

Para montá-lo: criar um Project chamado "Comentário Matinal — DEPIN/DIRIN", colar
`prompts/project_instructions.md` nas instruções e anexar ao conhecimento os quatro
arquivos de `prompts/`. Escrever `etapa 1`, `etapa 2` ou `etapa 3`, com o horário de
redação e o material do dia anexo.

`project_instructions.md` não repete convenção alguma: extensão, disciplina numérica,
atribuição e janela temporal ficam no guia, e é de lá que o Project as lê. Manter uma
cópia dessas regras nas instruções do Project produziria duas fontes, e a segunda
envelheceria em silêncio na primeira revisão do guia.
