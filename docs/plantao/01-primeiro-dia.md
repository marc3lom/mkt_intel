# O primeiro dia

Você está de plantão. Esta página é o que você precisa saber antes de abrir o terminal:
o que sai daqui, quem lê, quanto tempo leva, o que é seu decidir, e de que forma rodar.

## O que você produz, e quem lê

Um e-mail, todo dia útil, com três peças:

- o **comentário** — quatro a cinco marcadores, entre 350 e 500 palavras, descrevendo o
  que moveu os mercados desde o fechamento anterior;
- o **painel direcional** — a grade de ativos, como imagem;
- o **calendário do dia** — divulgações e decisões de bancos centrais, como imagem.

O leitor é a diretoria do Banco Central. O comentário é descritivo e impessoal: ele
relata o que os mercados fizeram e o que as fontes atribuíram a esse movimento, sem
posição institucional e sem previsão. As convenções todas estão em
`prompts/00_guia_de_estilo.md`, que é a fonte única — o comando o injeta em toda etapa
de IA, e é por isso que você não precisa conhecê-lo de cor para produzir texto que o
respeite.

O **bloco de auditoria** que acompanha cada etapa é ferramenta de trabalho e **nunca vai
no e-mail**.

## Quanto tempo leva

O roteiro é contado em tempo relativo a partir do término da coleta (T0), não em horário
de relógio. O plantão pode começar às 7h00 ou às 8h30; a sequência e a folga são as
mesmas. Ciclo completo em torno de vinte e cinco minutos — o que exige começar a coleta
até 8h30 para caber na janela.

Duas esperas dominam esse tempo, e nenhuma delas é sua: as chamadas ao modelo, nos
passos 2, 4 e 6, levam minutos. Os passos que dependem de você — escolher os temas, ler
a revisão, conferir o documento no Word — são os curtos, e são os que não se pulam.

## O que é seu decidir, e o que o comando decide

O comando decide tudo o que é mecânico e verificável, e **recusa** decidir o resto.

Ele decide sozinho: quais ativos entram no painel (`config/painel.toml`), a direção de
cada um, se um indicador já foi divulgado (por comparação de horário, nunca pelo valor
na tela), qual é o comentário do dia anterior, qual é o horário de redação (o carimbo do
painel, não o relógio), e se a execução está dentro da janela.

Você decide: quais temas entram e em que ordem; que ressalva o painel exige e a tabela
de temas não tem como saber; o que fazer com os pontos que a revisão devolve sob seu
julgamento; se uma divergência entre o `.docx` e o `.md` foi intencional; e se vale
contornar uma recusa do arquivamento com `--forcar`.

Os quatro pontos estão detalhados em [O que é seu decidir](04-decisoes.md). Vale ler
antes do primeiro plantão — o passo 3 do runbook chega rápido, e ele é o único que não
se delega.

## As duas formas de rodar

O [runbook](03-runbook.md) é contado no terminal, com `uv run matinal`.
`notebooks/plantao.ipynb`
é a outra forma, com os mesmos passos em células: quem prefere ver o painel e as
tabelas na própria página, ou quer inspecionar o `DataFrame` que virou o bloco
direcional, roda por lá.

Nenhuma das duas implementa o plantão. As duas são fachadas sobre
`src/comentario_matinal/plantao.py` e chamam as mesmas funções, então não podem
divergir no que fazem. O que poderia divergir é a **sequência** — ela existe duas
vezes, no argparse e nas células —, e é isso que `tests/test_notebook.py` prende:
passo novo no núcleo, subcomando novo no terminal ou célula fora da ordem de
`plantao.PASSOS` derrubam o teste até que o notebook seja atualizado junto.

**Parâmetro novo num passo também.** Ou uma célula o exercita, ou ele entra na lista de
exceções do teste com o motivo escrito ao lado. Não ter contrapartida no notebook é
decisão legítima — `--asof`, `--anterior` e `--modelo` são conserto, ensaio e
investigação, e moram no terminal —, mas precisa ser decisão, e não esquecimento.

Numa máquina sem licença BQL, `uv run matinal --sem-calendario` pula a consulta do
calendário; no notebook o equivalente é o `SEM_CALENDARIO = True` da célula do
calendário. Nos dois casos o bloco direcional sai sem a agenda, dizendo isso no próprio
texto, e a montagem do documento é recusada — o template tem dois lugares de imagem, e
um deles ficaria vazio no que vai à diretoria.

O núcleo também não escreve instrução de terminal. Ele diz o que falta — "falta a
triagem de 20260817." — e nomeia a falta como dado; a frase que ensina a supri-la é de
cada fachada, porque "rodar `uv run matinal triagem`" é conselho certo no terminal e
errado numa célula, onde não há linha de comando na tela que o autor está olhando.

**O Passo 9 só existe no terminal.** `uv run matinal enviado` arquiva o comentário e
esvazia `fontes/` e `saida/`; o que ele arquiva vira o "comentário do dia anterior" de
amanhã. É o único passo destrutivo do processo e o único que afirma um fato que
nenhum código pode verificar — que o e-mail foi mesmo enviado. Notebook é onde se
re-executa célula sem querer, e por isso ele fica de fora de propósito.

## A janela e o dry run

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

---

Instalado? [Vá para o runbook](03-runbook.md). Ainda não?
[Instalação](02-instalacao.md), uma vez por máquina.
