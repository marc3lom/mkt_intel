# Configuração inicial (uma vez)

Uma vez por máquina, antes do primeiro plantão. Leva alguns minutos e não exige o
terminal Bloomberg aberto — a instalação não fala com ele; a coleta, sim.

Faça isto na véspera, não às 7h de um dia em que você está de plantão.

## O que precisa estar na máquina

Seis coisas, e o plantão para sem qualquer uma delas. As máquinas do BC já trazem a
maioria.

**1. Windows nativo.** Não WSL. O `blpapi` conversa com o terminal Bloomberg por IPC
local, e do WSL ele não alcança.

**2. O terminal Bloomberg**, aberto e logado na mesma máquina, com licença BQL para o
calendário do dia. É a única fonte de mercado do plantão.

**3. O `git`.** É como o repositório chega à máquina e como as atualizações chegam
depois. Conferir com `git --version`.

**4. O `uv`.** É o gerenciador de ambiente, e é como tudo neste repositório roda — daí
todo comando começar por `uv run`. Conferir com `uv --version`. Ele cuida também do
Python: se a versão que o repositório pede não estiver na máquina, o `uv` a baixa.

**5. O VS Code, com o GitHub Copilot.** O notebook roda no VS Code, e as três etapas de
texto são feitas pelo Copilot, no chat do próprio VS Code. Instalar as extensões
**Python**, **Jupyter** e **GitHub Copilot** (a do chat vem junto), e entrar com a sua
conta do GitHub: o ícone de conta, no canto inferior esquerdo, mostra se o Copilot está
ativo. O plano gratuito do Copilot basta.

**6. O Word.** O Passo 7 monta um `.docx` a partir de
`templates/comentario_matinal/comentario.dotx`, e é no Word que você insere o gráfico do
dia — opcional, colado à mão —, confere o documento e **exporta o PDF** que vai anexado
ao e-mail. O notebook não gera o PDF, e não há caminho sem esse passo manual.

## Clonar o repositório

O repositório é o `mkt_intel`, no GitHub do BC, e é privado: sem acesso, o `git clone`
responde que ele não existe — é assim que o GitHub nega leitura, e não significa que você
errou o endereço. O acesso se pede a quem administra o repositório.

O endereço está no botão **Code** da página do repositório. Numa pasta sua de trabalho:

```
git clone <endereço do repositório>
cd mkt_intel
```

**Todos os comandos abaixo rodam da raiz do clone**, a pasta `mkt_intel`.

Se o `git` não alcançar o GitHub pela rede do BC — erro de proxy, 407, certificado —,
configurar o proxy no próprio repositório, uma vez:

```
git config http.proxy http://:@webaccess.bcb.gov.br:62408
git config http.proxyAuthMethod negotiate
git config http.sslBackend schannel
```

O `negotiate` autentica pela sessão do Windows, e o `schannel` usa os certificados do
Windows, que é onde está o da inspeção de TLS do proxy.

## A instalação

Três comandos, na raiz do clone:

1. Instalar as dependências: `uv sync`.
2. Instalar o filtro de notebook: `uv run nbstripout --install`.
3. Criar a pasta das fontes: `mkdir input\comentario_matinal` (ver abaixo por que ela
   não vem no clone).

O passo 2 vale por clone, e é o que impede que um notebook executado leve para um commit
os dados de mercado e o texto do comentário — possivelmente antes de ele ter sido
enviado. O filtro tira as saídas no `git add`, sem tocar no arquivo aberto na tela.

O `uv sync` cria a `.venv` — uma só, na raiz — e instala tudo, inclusive o `blpapi`, que
não vem do PyPI: o `pyproject.toml` já aponta para o índice da Bloomberg.

Por fim, no VS Code: **Arquivo → Abrir Pasta**, e escolher a pasta `mkt_intel` — a raiz,
não uma subpasta. Abrir `notebooks/comentario_matinal/plantao_copilot.ipynb` e, no canto
superior direito, **Selecionar Kernel → Ambientes Python → `.venv`**. A escolha fica
gravada; não se repete a cada plantão.

Abrir a raiz, e não a pasta `notebooks/`, importa por dois motivos: os comandos
`/matinal-…` do chat vêm de `.github/prompts/`, que o VS Code só enxerga com a raiz
aberta; e os caminhos do plantão são ancorados na raiz do repositório.

### As pastas que não vêm no clone

`input/` e `output/` estão no `.gitignore` e **não existem depois de clonar**. É de
propósito: uma guarda os PDFs da Bloomberg, que não entram no repositório, e a outra
guarda as saídas do dia, que são refeitas toda manhã.

Isso importa porque o Passo 1 manda salvar os PDFs do dia **dentro de
`input/comentario_matinal/`**, e a pasta não está lá. Criá-la à mão, na raiz do
repositório — ao lado de `prompts/` —, não dentro de `notebooks/`, que é o engano fácil:
uma pasta de fontes no lugar errado faz a etapa avisar que não aproveitou PDF algum, sem
dizer por quê. A `output/comentario_matinal/` o próprio notebook cria.

A pasta `arquivo/` também é desta máquina: é onde o Passo 9 guarda os comentários que
você enviou, e ela não vai ao repositório.

## O ensaio que fecha a instalação

Instalado não é o mesmo que funcionando. Rodar o plantão uma vez **fora da janela de
7h–9h** — de tarde, na véspera. Fora da janela toda execução é ensaio: o notebook
produz todos os artefatos e carimba o painel com `PAINEL DIRECIONAL — DRY RUN`. Nada é
enviado, e nada é bloqueado.

Com o terminal Bloomberg aberto e logado, e um PDF qualquer em
`input/comentario_matinal/`, rodar o notebook do começo até a célula da triagem, e
fazer a triagem pelo chat com `/matinal-triagem`, como no
[runbook](03-runbook.md#passo-2--triagem-t0--5-min).

As células do Passo 1 exercitam a instalação do lado da Bloomberg — `blpapi`, licença,
IPC — e gravam quatro arquivos em `output/comentario_matinal/`. A triagem exercita o
Copilot, que é a outra metade que pode faltar. Se as duas passaram, sua máquina está
pronta.

Ensaiar até o fim — redação, revisão, montagem do `.docx` — é melhor ainda, e é a única
forma de descobrir que o Word não abre o documento numa manhã que não seja a sua
primeira. O único passo que **não** se ensaia é o `uv run matinal enviado`: ele afirma
que o e-mail foi enviado, e arquiva.

Deu erro? [Quando dá errado](05-quando-da-errado.md) lista o sintoma exato de cada
falha desta lista.

## Manter a instalação em dia

O guia de estilo, os prompts e o código chegam pelo repositório. De tempos em tempos —
e sempre que avisarem de uma mudança —, na raiz do clone:

```
git pull
uv sync
```

O guia de estilo não se edita na sua cópia: mudança de convenção é pedida a quem mantém
o repositório, e chega a todos na atualização seguinte. Duas cópias do guia que divergem
são dois comentários que deixam de ser indistinguíveis entre os autores.
