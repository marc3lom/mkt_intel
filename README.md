# comentario_matinal

Prompts, guia de estilo e utilitários do Comentário Matinal da Mesa de Investimentos
(DEPIN/DIRIN — Banco Central do Brasil).

O comentário é produzido diariamente pela manhã, com envio pretendido até 8h00 de
Brasília. A autoria roda entre os gestores da divisão; o processo não deve variar com o
autor nem com o horário em que o plantão começa. Este repositório existe para garantir
isso.

---

## Estrutura

```
comentario_matinal/
├── README.md                   este arquivo — runbook do plantão
├── prompts/
│   ├── 00_guia_de_estilo.md    fonte única de convenções
│   ├── 01_triagem.md           etapa 1 — seleção de temas
│   ├── 02_redacao.md           etapa 2 — redação
│   ├── 03_revisao.md           etapa 3 — revisão
│   └── project_instructions.md texto a colar no Project do Claude
├── exemplos/
│   ├── aprovados/              comentários exemplares (few-shot)
│   └── rejeitados/             trechos rejeitados, com o motivo no cabeçalho
├── arquivo/
│   └── AAAA/MM/AAAAMMDD.md     comentários enviados
├── src/comentario_matinal/     o comando `matinal`
│   ├── config.py               leitura do painel.toml
│   ├── dados.py                a coleta de mercado — uma só, para todas as saídas
│   ├── calendario.py           calendário econômico e status de divulgação
│   ├── texto.py                bloco direcional
│   ├── fontes.py               PDFs das fontes → texto
│   ├── modelo.py               a chamada ao modelo, atrás de uma função única
│   ├── etapas.py               as três etapas de IA e o encadeamento
│   ├── documento.py            montagem do .docx a partir do template
│   └── cli.py                  o comando
├── fontes/                     PDFs do dia (fora do repositório)
├── saida/                      saídas do dia (fora do repositório)
├── config/
│   └── painel.toml             lista canônica de ativos do painel
├── templates/
│   └── comentario.dotx         template do documento enviado
├── pyproject.toml              dependências do comando
└── uv.lock                     versões exatas — versionado de propósito
```

---

## Configuração inicial (uma vez)

1. Criar um Project no Claude chamado "Comentário Matinal — DEPIN/DIRIN".
2. Colar `prompts/project_instructions.md` nas instruções do projeto.
3. Anexar ao conhecimento do projeto os quatro arquivos de `prompts/`.
4. Instalar as dependências: `uv sync`.

O `uv sync` cria o `.venv` e instala tudo, inclusive o `blpapi`, que não vem do PyPI —
o `pyproject.toml` já aponta para o índice da Bloomberg. Rodar sempre do Windows nativo,
nunca do WSL: o `blpapi` conversa com o terminal por IPC local. A instalação não exige
terminal aberto; a execução do comando, sim.

**O repositório `daily` precisa estar clonado ao lado deste**, em `../daily`, **e em
`main`**: a camada que desenha a grade do painel e as tabelas do calendário mora lá e é
compartilhada, não copiada — ela tem outros consumidores naquele repositório. Sem o
`../daily` o `uv sync` falha.

O plantão lê `../daily` diretamente do disco, sem passar pelo GitHub. Um `git checkout`
naquele diretório muda o código que o comando `matinal` executa na manhã seguinte, sem
aviso e sem reinstalação. Por isso `../daily` fica fixo em `main`, e o desenvolvimento
acontece em outro lugar:

```
../daily        main      o que o plantão consome
../daily-dev    develop   worktree de desenvolvimento
```

**Alteração na renderização se faz em `../daily-dev`, e só chega ao plantão depois de
mesclada em `main`.** As duas pastas compartilham o mesmo repositório git, então o
trabalho feito na worktree já está versionado — o que a separação garante é que ele não
entre em produção antes da hora. Para conferir onde cada uma está:

```
git -C ../daily worktree list
```

Sempre que uma convenção mudar, editar `prompts/00_guia_de_estilo.md`, comitar, e
substituir o arquivo no conhecimento do projeto. Não editar convenções nos prompts de
etapa — eles apenas referenciam o guia.

### As etapas de IA

As três etapas rodam pelo Claude Code em modo não interativo, e exigem o `claude` no
PATH. A chamada ao modelo está isolada em `modelo.py`, atrás de uma função única: trocar
para Copilot CLI, Azure OpenAI ou chamada direta à API é escrever outra classe e apontar
a variável `COMENTARIO_MATINAL_BACKEND`, sem tocar no fluxo das etapas.

Os PDFs viram texto antes de chegar ao modelo, para que o insumo seja o mesmo em
qualquer backend — um lê PDF anexo, outro não.

Por padrão a etapa roda **sem ferramenta alguma**: tudo vai injetado na mensagem. `--web`
libera busca para confirmar dado já presente nas fontes, como os prompts permitem, e
nesse caso a etapa é instruída a registrar cada consulta no bloco de auditoria — o guia
exige sinalização explícita, e o revisor precisa saber que houve.

O modelo é o que estiver configurado na CLI do Claude Code; `--modelo` fixa por execução.

---

## Runbook do plantão

O roteiro é contado em tempo relativo a partir do término da coleta (T0), não em horário
de relógio. O plantão pode começar às 7h30 ou às 7h50; a sequência e a folga são as
mesmas. Ciclo completo em torno de vinte e cinco minutos.

### Passo 1 — Coleta (T0)

Reunir as fontes do dia: wraps da Bloomberg, First Word, e-mails de sell-side, matérias
do Financial Times ou do Wall Street Journal. **Salvar em PDF dentro de `fontes/`** — é
de lá que as etapas de IA leem, e a pasta fica fora do repositório.

Gerar as três saídas do dia:

```
uv run matinal
```

Uma execução, uma consulta de mercado, três arquivos em `saida/`:

| Arquivo | Uso |
|---|---|
| `painel_AAAAMMDD.png` | grade de ativos, para colar no e-mail |
| `calendario_AAAAMMDD.png` | tabela de divulgações e bancos centrais, idem |
| `painel_AAAAMMDD.txt` | bloco direcional, insumo das etapas de IA |
| `calendario_AAAAMMDD.md` | o mesmo calendário em texto, idem |

As três saem do mesmo conjunto de dados. O texto não recalcula direção nenhuma: ele lê
os mesmos números que cada tile da imagem renderizou. Por construção, a imagem enviada à
diretoria e o texto usado na conferência não podem discordar sobre a direção de um ativo.

O comando carimba o horário de execução na imagem e no texto. Se o painel for gerado bem
antes da redação, regerá-lo — direção de ativo muda, e o painel é a referência de
coerência do texto. Para reproduzir um horário específico, `--asof 2026-08-14T07:35`;
vale para a imagem e para o texto, mas **não** para a tabela do calendário, que sempre
traz o estado corrente do BQL.

**Anote o horário em que a coleta terminou. Ele é o horário de redação do dia** e
acompanha o trabalho até a revisão.

### Passo 2 — Triagem (T0 + 5 min)

```
uv run matinal triagem
```

Converte os PDFs de `fontes/` para texto, monta a mensagem com o guia de estilo, o
prompt da etapa, as fontes, o painel e o calendário, e grava `saida/triagem_AAAAMMDD.md`
— tabela de temas candidatos, tema dominante proposto, alertas e sugestão de corte.

**O horário de redação não é informado à mão: vem do carimbo do painel**, que é o
término da coleta. Passar `--asof` diverge disso e o comando avisa.

Também é possível fazer a etapa no Project do Claude, anexando os PDFs e o
`painel_AAAAMMDD.txt` e escrevendo `etapa 1` com o horário de redação. Os prompts são os
mesmos; o comando apenas evita o trabalho de anexar.

### Passo 3 — Decisão editorial (T0 + 10 min)

**Este é o único passo que não se delega.** Ler a tabela, conferir os alertas —
sobretudo os de dado ainda não divulgado e os de divergência com o painel — e definir o
tema dominante e os dois ou três temas seguintes, em ordem.

Não pular esta etapa em dia corrido. É onde se evita excesso de temas e dado antecipado.

### Passo 4 — Redação (T0 + 15 min)

```
uv run matinal redacao --temas "dominante | tema 2 | tema 3"
```

Os temas vão na ordem de relevância, o dominante primeiro. Para textos longos,
`--temas-arquivo temas.md`. **É por aqui que a decisão do passo 3 entra no fluxo** — o
comando recusa rodar sem os temas, porque a hierarquia é escolha do autor e não do
modelo.

A redação recebe os alertas da triagem automaticamente, extraídos da seção C do arquivo
da etapa anterior. Sai `saida/redacao_AAAAMMDD.md`, com o comentário e o bloco de
auditoria.

Conferir o bloco de auditoria: contagem total dentro de 350–500, orçamento por marcador,
mapeamento marcador → fonte, ressalvas.

### Passo 5 — Passagem ao revisor

**Regra de folga: a passagem ocorre com pelo menos dez minutos de antecedência sobre o
horário de envio pretendido.** Se a coleta atrasou e essa folga não existe mais, avisar o
revisor antes de mandar, para que ele priorize as correções obrigatórias e trate as
sugestões como descartáveis.

Enviar ao segundo analista: texto, PDFs das fontes, `painel_AAAAMMDD.txt`, bloco de
auditoria e **o horário de redação**.

### Passo 6 — Revisão

```
uv run matinal revisao
```

Toma o comentário e o bloco de auditoria de `saida/redacao_AAAAMMDD.md` e grava
`saida/revisao_AAAAMMDD.md` — correções obrigatórias, sugestões, texto revisado e
auditoria da revisão. Grava também `saida/comentario_AAAAMMDD.md`, extraído do bloco de
código da seção 3, que é o insumo do passo 7.

**Se esse bloco não vier no formato esperado, o comando falha e não grava o `.md`.** É o
único ponto em que a saída do modelo entra direto no documento que vai à diretoria, e um
arquivo malformado só apareceria no Word. Nesse caso, extrair o texto à mão da revisão.

O revisor também pode fazer a etapa no Project, escrevendo `etapa 3` com o horário de
redação e anexando tudo.

O horário informado é o do autor, não o do revisor. Um comentário redigido às 7h35 e
outro às 7h55 podem descrever quadros diferentes de forma legítima — releases europeus e
britânicos saem entre 3h e 6h de Nova York, dentro da janela de redação. O revisor precisa
saber contra qual momento está conferindo.

Tratar primeiro as correções obrigatórias; as sugestões são opcionais e ficam a critério
do autor.

### Passo 7 — Montagem do documento

Salvar o texto revisado em Markdown, um marcador por parágrafo, e montar o documento:

```
uv run matinal --comentario comentario.md
```

Sai `saida/comentario_AAAAMMDD.docx`, a partir de `templates/comentario.dotx`, com o
painel no alto e a tabela do calendário depois dos marcadores. Do Markdown, `- ` vira
parágrafo com o marcador do template, `*termo*` vira itálico e `**termo**` vira negrito.
O fecho vem do template; se o Markdown trouxer um, ele é descartado com aviso.

**Esta chamada não consulta o Bloomberg.** Ela reaproveita o painel e o calendário já
gerados para a data — o comentário é escrito depois do painel, e recoletar produziria um
documento com o mercado de agora sob um texto redigido contra o de antes. Se as imagens
do dia não existirem em `saida/`, aí sim o comando coleta antes de montar.

O comando avisa no stderr quando o comentário sai da faixa de quatro a cinco marcadores
que o guia fixa, e quando alguma linha fora de marcador foi ignorada.

Abrir o `.docx` no Word para inserir o gráfico do dia, quando houver, conferir o texto e
exportar o PDF. **O PDF não é gerado pelo comando**: a exportação é feita do Word, na
mesma passagem em que o analista confere o documento.

### Referência de fusos

| Brasília | Nova York | Observação                                              |
|----------|-----------|---------------------------------------------------------|
| 07h00    | 06h00     | Releases europeus e britânicos já divulgados             |
| 08h00    | 07h00     | Limite usual de envio                                    |
| 09h30    | 08h30     | Maioria dos releases americanos — sempre após a redação   |

Horários de Nova York consideram o horário de verão americano. Fora dele, subtrair uma
hora adicional da conversão.

### Após o envio

Salvar o texto final em `arquivo/AAAA/MM/AAAAMMDD.md` — Markdown, data ISO no nome do
arquivo, apenas o corpo do comentário. Não incluir painel, calendário nem bloco de
auditoria.

O formato é Markdown por decisão deliberada: o arquivo precisa ser pesquisável por texto
para alimentar os exemplos few-shot e permitir conferência de consistência entre dias.
Comentários anteriores em `.docx`, sob a convenção antiga `AAAA/AAAAMM/`, permanecem como
estão; não há migração retroativa.

Comentários que a chefia destacar como exemplares vão para `exemplos/aprovados/` e
alimentam os exemplos few-shot do guia de estilo. Trechos rejeitados vão para
`exemplos/rejeitados/`, com o motivo da rejeição no cabeçalho do arquivo.

---

## Notas

- O bloco de auditoria nunca vai no e-mail.
- Os PDFs da Bloomberg trazem marcação de uso exclusivo nominal e vedação à
  redistribuição. O material não é redistribuído em nenhuma hipótese: apenas o conteúdo
  informa a redação do comentário, que é produto derivado e interno. Os PDFs não entram
  no repositório (ver `.gitignore`).
- O Project do Claude está hoje em assinatura pessoal. Na migração para o ambiente
  corporativo, solicitar projeto compartilhado com permissão de edição restrita, de modo
  que os gestores de plantão usem sem divergir, e submeter o fluxo à governança de IA da
  instituição.
- Repositório privado. Contém comentários institucionais enviados à diretoria.

### A confirmar no primeiro plantão real

A coluna `ATUAL` da tabela do calendário **não foi verificada às 7h40 para um release
das 9h30**. A verificação só é possível dentro da janela do plantão, e as execuções de
teste ocorreram fora dela — o que se observou foi a tabela às 13h, quando os releases da
manhã já haviam saído de verdade.

O que conferir: às 7h40, um release americano das 9h30 aparece na tabela com `ATUAL`
vazio, ou já preenchido com o número do período anterior?

**Se vier preenchido antes da divulgação, a regra de status deve ignorar `ATUAL` e
decidir exclusivamente pela comparação de horário** — que é como
`calendario.eventos_do_dia` já funciona hoje. A conferência serve para saber se a tabela
enviada à diretoria precisa de ressalva, já que ela exibe `ATUAL` sem qualificar o
status, ao contrário do bloco em texto.
