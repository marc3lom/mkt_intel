# comentario_matinal

Prompts, guia de estilo e utilitários do Comentário Matinal da Mesa de Investimentos
(DEPIN/DIRIN — Banco Central do Brasil).

O comentário é produzido e enviado diariamente entre 7h00 e 9h00, no fuso da máquina do
plantão — nesta mesa, Brasília. A autoria roda entre os gestores da divisão; o processo
não deve variar com o autor nem com o horário em que o plantão começa. Este repositório
existe para garantir isso.

Fora dessa janela o comando entende que a execução é ensaio e carimba as saídas
(ver "Dry run").

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
│   └── project_instructions.md o Project do Claude — caminho alternativo
├── exemplos/                   material humano; nada em src/ lê estas pastas
│   ├── aprovados/              casos a promover à seção 12 do guia
│   └── rejeitados/             trechos rejeitados, com o motivo no cabeçalho
├── arquivo/
│   └── AAAA/MM/AAAAMMDD.md     comentários enviados — o nome é lido pelo comando
├── src/comentario_matinal/     o comando `matinal`
│   ├── config.py               leitura do painel.toml
│   ├── dados.py                a coleta de mercado — uma só, para todas as saídas
│   ├── calendario.py           calendário econômico e status de divulgação
│   ├── janela.py               a janela 7h–9h, o fuso local e o dry run
│   ├── texto.py                bloco direcional
│   ├── fontes.py               PDFs das fontes → texto
│   ├── modelo.py               a chamada ao modelo, atrás de uma função única
│   ├── etapas.py               as três etapas de IA e o encadeamento
│   ├── documento.py            montagem do .docx a partir do template
│   ├── enviado.py              arquivamento do enviado e limpeza do dia
│   ├── plantao.py              o plantão como funções — o núcleo das duas fachadas
│   ├── cli.py                  fachada de terminal: o comando
│   └── render/                 painel, tabelas do calendário e o que elas precisam
├── notebooks/
│   └── plantao.ipynb           fachada de notebook — as mesmas funções, em células
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

O plantão inteiro roda deste repositório. Não é preciso criar Project algum: as três
etapas de IA montam a mensagem com o guia de estilo e o prompt da etapa embutidos, a
partir dos arquivos de `prompts/`. O Project continua existindo como caminho
alternativo — ver "O Project do Claude", mais abaixo.

1. Instalar as dependências: `uv sync`.
2. Ter o `claude` no PATH, autenticado. É o backend padrão das etapas de IA.
3. Instalar o filtro de notebook: `uv run nbstripout --install`.

O passo 3 vale por clone, e é o que impede que um notebook executado leve para o
commit os dados de mercado e o texto do comentário — possivelmente antes de ele ter
sido enviado. O filtro tira as saídas no `git add`, sem tocar no arquivo aberto na
tela. Sem ele nada avisa na hora: quem percebe é o `tests/test_notebook.py`, que
existe como rede para o clone em que o passo foi esquecido.

O `uv sync` cria o `.venv` e instala tudo, inclusive o `blpapi`, que não vem do PyPI —
o `pyproject.toml` já aponta para o índice da Bloomberg. Rodar sempre do Windows nativo,
nunca do WSL: o `blpapi` conversa com o terminal por IPC local. A instalação não exige
terminal aberto; a execução do comando, sim.

Sempre que uma convenção mudar, editar `prompts/00_guia_de_estilo.md` e comitar. O
comando lê o arquivo do disco a cada execução, então a mudança vale no plantão
seguinte, sem mais nenhum passo. Quem usa o Project precisa substituir o arquivo lá
também. Não editar convenções nos prompts de etapa — eles apenas referenciam o guia.

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

### A janela e o dry run

O plantão vai das **7h00 às 9h00**, inclusive nas duas pontas, medidas no fuso da
máquina. Fora dela toda execução é ensaio: o comando abre com um banner no stderr e
carimba o painel em texto com `PAINEL DIRECIONAL — DRY RUN`.

O carimbo vai no título, e não na linha `Referência:` — é ela que o comando lê para
achar o horário de redação. Como o painel em texto vai injetado inteiro na mensagem das
três etapas, o marcador chega também ao modelo: a triagem e a revisão sabem que estão
num ensaio e podem registrar isso na auditoria.

**Nada é bloqueado.** Ensaiar fora da janela é o uso legítimo — testar a montagem do
documento à tarde, reprocessar um dia antigo, conferir uma mudança de template. O
carimbo existe para que o arquivo de ensaio não seja confundido depois com um de
plantão.

A decisão sai sempre do **relógio real**, nunca do `--asof`. Reproduzir um horário
antigo é ensaio por definição; e passar `--asof 07:35` às 7h50, que é o uso real do
flag, continua sendo plantão.

O fuso é lido a cada execução, do sistema operacional. Nesta máquina o relógio de
hardware guarda UTC (`RealTimeIsUniversal=1`, padrão de dual boot com Linux), e isso não
interfere: o sistema entrega hora local já convertida. Rodando de um fuso que não seja o
de Brasília, o comando avisa — a janela continua fazendo sentido como hora do analista,
mas as regras temporais do guia pressupõem a relação Brasília↔Nova York, e os horários
do calendário chegam do terminal no fuso dele.

### O Project do Claude

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

### Os exemplos

`exemplos/aprovados/` e `exemplos/rejeitados/` são material de trabalho humano, **não
insumo do comando**: nada em `src/` lê essas pastas. Elas guardam os casos brutos —
comentários que a chefia destacou, trechos rejeitados com o motivo no cabeçalho — até
que alguém os transforme em exemplo anotado na seção 12 do guia de estilo. É a seção
12 que chega ao modelo, porque o guia inteiro vai injetado em toda etapa.

Um comentário arquivado em `exemplos/` e nunca promovido ao guia não influencia saída
nenhuma.

---

## Runbook do plantão

O roteiro é contado em tempo relativo a partir do término da coleta (T0), não em horário
de relógio. O plantão pode começar às 7h00 ou às 8h30; a sequência e a folga são as
mesmas. Ciclo completo em torno de vinte e cinco minutos — o que exige começar a coleta
até 8h30 para caber na janela.

### As duas formas de rodar

O runbook abaixo é contado no terminal, com `uv run matinal`. `notebooks/plantao.ipynb`
é a outra forma, com os mesmos passos em células: quem prefere ver o painel e as
tabelas na própria página, ou quer inspecionar o `DataFrame` que virou o bloco
direcional, roda por lá.

Nenhuma das duas implementa o plantão. As duas são fachadas sobre
`src/comentario_matinal/plantao.py` e chamam as mesmas funções, então não podem
divergir no que fazem. O que poderia divergir é a **sequência** — ela existe duas
vezes, no argparse e nas células —, e é isso que `tests/test_notebook.py` prende:
passo novo no núcleo ou subcomando novo no terminal derruba o teste até que o notebook
seja atualizado junto.

**O Passo 9 só existe no terminal.** `uv run matinal enviado` arquiva o comentário e
esvazia `fontes/` e `saida/`; o que ele arquiva vira o "comentário do dia anterior" de
amanhã. É o único passo destrutivo do processo e o único que afirma um fato que
nenhum código pode verificar — que o e-mail foi mesmo enviado. Notebook é onde se
re-executa célula sem querer, e por isso ele fica de fora de propósito.

### Passo 1 — Coleta (T0)

Reunir as fontes do dia: wraps da Bloomberg, First Word, e-mails de sell-side, matérias
do Financial Times ou do Wall Street Journal. **Salvar em PDF dentro de `fontes/`** — é
de lá que as etapas de IA leem, e a pasta fica fora do repositório.

**Só PDF é lido.** `.docx`, `.png`, `.msg` e afins ficam de fora: as etapas recebem
texto, nunca anexo nem imagem, para que o insumo não mude com o backend. O comando
lista no stderr todo arquivo que deixou de ler, com nome — um `.docx` na pasta não
produz erro, e sem esse aviso a falta só apareceria como a ausência de um tema na
triagem. Do Outlook, Arquivo → Imprimir → Microsoft Print to PDF; do navegador,
Ctrl+P → Salvar em PDF.

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

**O comentário do dia anterior também entra sozinho**, tomado do arquivado mais
recente em `arquivo/AAAA/MM/`. É contra ele que a triagem julga ineditismo do tema. O
comando informa no stderr qual data foi usada — numa segunda-feira é a de sexta — e
avisa quando não achou nenhum dentro da última semana. `--anterior caminho.md` força
outro arquivo; `--sem-anterior` roda sem.

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
horário de envio pretendido — no limite, 8h50.** Se a coleta atrasou e essa folga não
existe mais, avisar o revisor antes de mandar, para que ele priorize as correções
obrigatórias e trate as sugestões como descartáveis.

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

A revisão também recebe o comentário do dia anterior automaticamente, pela mesma
regra da triagem — é dele que sai a checagem de contradição não sinalizada entre um
dia e o seguinte.

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

### Passo 8 — Conferência, antes do e-mail

```
uv run matinal conferir
```

Compara marcador a marcador o `.docx` com o `.md` e mostra os trechos que diferem, com
as palavras em volta para situar. Não arquiva, não limpa, não toca em nada: só lê os
dois arquivos e responde. Sai com código 1 quando há divergência.

Toda correção feita no Word aparece aqui. As intencionais devem ser repetidas no `.md`,
que é o que fica versionado. As não intencionais — palavra comida por um clique fora do
lugar, trecho perdido numa substituição — são justamente o que este passo existe para
apanhar, e **este é o último momento em que ainda têm conserto**.

Vale a pena mesmo quando o texto parece igual ao que saiu da revisão. Na primeira rodada
em produção, quatro palavras haviam sumido do documento durante a edição manual, entre
elas o `swap` de "mercados de swap", e o e-mail saiu com a frase quebrada. A conferência
rodou depois do envio, quando já não adiantava.

### Passo 9 — Após o envio

```
uv run matinal enviado
```

Arquiva `arquivo/AAAA/MM/AAAAMMDD.md` e `arquivo/AAAA/MM/comentario_AAAAMMDD.docx`, e
esvazia `fontes/` e `saida/`. **Rodar só depois de o e-mail ter saído** — o comando
afirma que o comentário foi enviado.

Antes de arquivar, ele **repete a comparação do Passo 8** e para sem arquivar nada se os
dois divergirem. Aqui a checagem já não salva o comentário de hoje — o e-mail saiu. Ela
protege o insumo de amanhã: é o `.md` que fica versionado e que a triagem lê como
comentário do dia anterior, e registrar ali um texto que não foi o enviado não erra hoje,
erra amanhã, como contradição inventada. Por isso o Passo 8 existe separado: mesma
comparação, no único momento em que ela ainda tem conserto.

Três recusas, todas contornáveis com `--forcar`, que é rombudo e passa pelas três de
uma vez:

| Recusa | Por quê |
|---|---|
| Fora da janela de 7h–9h | É a única etapa que bloqueia. As outras produzem artefato, carimbado como ensaio; esta afirma um envio, e o que arquiva vira o insumo de amanhã |
| `.docx` e `.md` divergem | Ver acima |
| Já existe comentário arquivado para a data | Rearquivar por engano apagaria em silêncio o comentário de um dia já enviado |

A limpeza só ocorre **depois** de o arquivamento dar certo. Falhando o arquivamento,
nada é apagado.

O `.docx` vai para `arquivo/` como registro local do que foi mandado, mas **não é
versionado** — `.gitignore` cobre `*.docx`. O que entra no git é o `.md`.

**O nome do arquivo é lido pelo comando**, não é só convenção de organização: é dele
que sai o comentário do dia anterior da triagem e da revisão do plantão seguinte.
Nome fora do padrão `AAAAMMDD.md` é ignorado em silêncio, e a checagem de ineditismo
roda sem base. Pular o arquivamento tem o mesmo efeito.

Os arquivos de etapa — `triagem`, `redacao`, `revisao`, com seus blocos de auditoria —
vão embora na limpeza. Para guardar a memória de como um comentário foi construído,
copiá-los à mão antes de rodar `enviado`.

### Referência de fusos

| Brasília | Nova York | Observação                                                  |
|----------|-----------|-------------------------------------------------------------|
| 07h00    | 06h00     | Abertura da janela. Releases europeus e britânicos já saíram |
| 09h00    | 08h00     | Fecho da janela. Mercado americano à vista ainda fechado     |
| 09h30    | 08h30     | Maioria dos releases americanos — sempre após a redação      |

Horários de Nova York consideram o horário de verão americano. Fora dele, subtrair uma
hora adicional da conversão.

**Trinta minutos separam o fim da janela do bloco americano das 8h30 de Nova York.**
Redigindo perto das 9h, conferir com cuidado redobrado o status de cada indicador
americano do dia — o bloco de calendário em texto traz `AINDA NÃO DIVULGADO` por
comparação de horário, e é nele que se confia, nunca no campo `ATUAL` da imagem.

O formato é Markdown por decisão deliberada: o arquivo precisa ser pesquisável por texto
e legível pelo comando. `arquivo/` guarda apenas o que o processo produz, a partir da
primeira rodada em produção. Os comentários antigos em `.docx`, sob a convenção
`AAAA/AAAAMM/`, foram retirados: serviam de contexto e não casavam com o padrão que o
comando lê.

Comentários que a chefia destacar como exemplares vão para `exemplos/aprovados/`;
trechos rejeitados vão para `exemplos/rejeitados/`, com o motivo no cabeçalho do
arquivo. **Guardar ali não muda o comportamento do modelo**: as duas pastas são
material de trabalho, e o que chega às etapas é a seção 12 do guia de estilo. Promover
o caso a exemplo anotado no guia é passo manual, e é o único que tem efeito.

---

## Notas

- O bloco de auditoria nunca vai no e-mail.
- Os PDFs da Bloomberg trazem marcação de uso exclusivo nominal e vedação à
  redistribuição. O material não é redistribuído em nenhuma hipótese: apenas o conteúdo
  informa a redação do comentário, que é produto derivado e interno. Os PDFs não entram
  no repositório (ver `.gitignore`).
- O acesso ao modelo está hoje em assinatura pessoal, tanto na CLI quanto no Project.
  Na migração para o ambiente corporativo, submeter o fluxo à governança de IA da
  instituição e providenciar acesso institucional à CLI — que é o caminho do plantão.
  Havendo Project, pedi-lo compartilhado com permissão de edição restrita, para que os
  gestores usem sem divergir.
- Repositório privado. Contém comentários institucionais enviados à diretoria.

### A coluna `ATUAL` — questão resolvida

**Antes da divulgação, `ATUAL` vem vazio.** Não carrega o número do período anterior,
que era a hipótese temida. Observado no terminal em 16/08/2026.

Consequência prática: **a tabela enviada à diretoria não precisa de ressalva.** Célula
vazia se lê como "ainda não saiu", sem depender de o leitor conhecer a convenção.

A regra do código não muda por isso. `calendario.eventos_do_dia` continua decidindo o
status **exclusivamente pela comparação de horário**, e o teste que fixa isso
(`test_status_vem_do_horario_e_nao_do_valor_preenchido`) monta de propósito um
calendário com `ATUAL` preenchido para evento futuro. Ele guarda a decisão de desenho,
não o comportamento observado do BQL: se um dia a fonte mudar, o status não muda junto.

Fica um caso a observar, agora que `ATUAL` é informativo: se ele aparecer **preenchido
antes** do horário previsto, é sinal de release antecipado ou de horário desatualizado
na agenda — e aí a comparação de horário erraria para o lado perigoso, marcando como
não divulgado algo que já saiu. É o inverso do risco original, e menos grave (o texto
deixaria de citar um dado disponível, em vez de citar um indisponível), mas vale saber
que existe.
