# O primeiro dia

Você está de plantão. Esta página é o que você precisa saber antes de abrir o notebook:
o que sai daqui, quem lê, quanto tempo leva, o que é seu decidir, e como se roda.

## O que você produz, e quem lê

Um e-mail, todo dia útil, com três peças:

- o **comentário** — quatro a cinco marcadores, entre 350 e 500 palavras, descrevendo o
  que moveu os mercados desde o fechamento anterior;
- o **painel direcional** — a grade de ativos, como imagem;
- o **calendário do dia** — divulgações e decisões de bancos centrais, como imagem.

As três vão **no corpo da mensagem**, e o mesmo documento vai **anexado em PDF**. O
anexo não é redundância: é dele que a chefia do DEPIN encaminha o comentário ao grupo
da diretoria no WhatsApp, e ninguém mais na divisão tem acesso a esse grupo. O
[runbook](03-runbook.md#o-envio) explica a montagem do e-mail em detalhe.

O leitor é a diretoria do Banco Central. O comentário é descritivo e impessoal: ele
relata o que os mercados fizeram e o que as fontes atribuíram a esse movimento, sem
posição institucional e sem previsão. As convenções todas estão em
`prompts/comentario_matinal/00_guia_de_estilo.md`, que é a fonte única — o notebook o
põe na mensagem de toda etapa de texto, e é por isso que você não precisa conhecê-lo de
cor para produzir texto que o respeite.

O **bloco de auditoria** que acompanha cada etapa é ferramenta de trabalho e **nunca vai
no e-mail**.

## Quanto tempo leva

O roteiro é contado em tempo relativo a partir do término da coleta (T0), não em horário
de relógio. O plantão pode começar às 7h00 ou às 8h30; a sequência e a folga são as
mesmas. Ciclo completo em torno de vinte e cinco minutos — o que exige começar a coleta
até 8h30 para caber na janela.

Duas esperas dominam esse tempo, e nenhuma delas é trabalho seu: o Copilot lendo a
mensagem e escrevendo a resposta, nos passos 2, 4 e 6, leva minutos. O que é seu nesses
passos é só digitar o comando no chat. Os passos que dependem de você — escolher os
temas, ler a revisão, conferir o documento no Word — são os curtos, e são os que não se
pulam.

## O que é seu decidir, e o que o processo decide

O processo decide tudo o que é mecânico e verificável, e **recusa** decidir o resto.

Ele decide sozinho: quais ativos entram no painel (`config/comentario_matinal/painel.toml`),
a direção de cada um, se um indicador já foi divulgado (por comparação de horário, nunca
pelo valor na tela), qual é o comentário do dia anterior, qual é o horário de redação (o
carimbo do painel, não o relógio), e se a execução está dentro da janela.

Você decide: quais temas entram e em que ordem; que ressalva o painel exige e a tabela
de temas não tem como saber; o que fazer com os pontos que a revisão devolve sob seu
julgamento; se uma divergência entre o `.docx` e o `.md` foi intencional; e se vale
contornar uma recusa do arquivamento com `--forcar`.

Os quatro pontos estão detalhados em [O que é seu decidir](04-decisoes.md). Vale ler
antes do primeiro plantão — o passo 3 do runbook chega rápido, e ele é o único que não
se delega.

## Como se roda

O plantão é o notebook `notebooks/comentario_matinal/plantao_copilot.ipynb`, aberto no
VS Code com o kernel `.venv`, célula a célula, de cima para baixo. Cada célula consome o
que a anterior gravou em `output/comentario_matinal/`.

Nas três etapas de texto, a célula não fala sozinha com modelo algum. Ela grava a
mensagem da etapa num arquivo e fica esperando; você abre o chat do Copilot, no modo
**Agente**, e digita o comando que a célula pediu — `/matinal-triagem`,
`/matinal-redacao` ou `/matinal-revisao`. O Copilot lê a mensagem, grava a resposta, e
a célula percebe e continua. Como isso funciona, e por que a célula às vezes recusa a
resposta, está no [runbook](03-runbook.md#durante-as-etapas-de-texto).

Numa máquina sem licença BQL, o `SEM_CALENDARIO = True` da célula do calendário pula a
consulta. O bloco direcional sai sem a agenda, dizendo isso no próprio texto, e a
montagem do documento é recusada — o template tem dois lugares de imagem, e um deles
ficaria vazio no que vai à diretoria.

**O Passo 9 não está no notebook.** `uv run matinal enviado`, no terminal, arquiva o
comentário e esvazia `input/comentario_matinal/` e `output/comentario_matinal/`; o que
ele arquiva vira o "comentário do dia anterior" do seu próximo plantão nesta máquina. É
o único passo destrutivo do processo e o único que afirma um fato que nenhum código pode
verificar — que o e-mail foi mesmo enviado. Notebook é onde se re-executa célula sem
querer, e por isso ele fica de fora de propósito.

## A janela e o dry run

O plantão vai das **7h00 às 9h00**, inclusive nas duas pontas, medidas no fuso da
máquina. A primeira célula do notebook mostra uma faixa: verde dentro da janela,
vermelha fora dela. Fora da janela toda execução é ensaio, e o painel em texto sai
carimbado com `PAINEL DIRECIONAL — DRY RUN`.

O carimbo vai no título, e não na linha `Referência:` — é ela que o processo lê para
achar o horário de redação. Como o painel em texto vai inteiro na mensagem das três
etapas, o marcador chega também ao modelo: a triagem e a revisão sabem que estão num
ensaio e podem registrar isso na auditoria.

**Nada é bloqueado.** Ensaiar fora da janela é o uso legítimo — testar a montagem do
documento à tarde, conferir que a máquina está pronta na véspera. O carimbo existe para
que o arquivo de ensaio não seja confundido depois com um de plantão.

O fuso é lido a cada execução, do sistema operacional. Rodando de um fuso que não seja o
de Brasília, o notebook avisa — a janela continua fazendo sentido como hora do analista,
mas as regras temporais do guia pressupõem a relação Brasília↔Nova York, e os horários
do calendário chegam do terminal Bloomberg no fuso dele.

---

Instalado? [Vá para o runbook](03-runbook.md). Ainda não?
[Instalação](02-instalacao.md), uma vez por máquina.
