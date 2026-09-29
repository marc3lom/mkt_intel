# Quando dá errado

No notebook, erro previsto aparece como **faixa vermelha** logo abaixo da célula, em
português e nomeando o arquivo; a **faixa âmbar** do Passo 3 não é erro, é a parada da
escolha de temas. Avisos aparecem como texto, na saída da célula. Procure aqui pelo
trecho que apareceu na sua tela.

| Sintoma | Causa | Saída |
|---|---|---|
| "a consulta de referência não devolveu dado algum" | terminal Bloomberg inativo | abrir o terminal e repetir |
| a consulta do calendário estoura | máquina sem licença BQL | `SEM_CALENDARIO = True` |
| "Nenhuma resposta da etapa … em 900s" | o comando não foi rodado no chat | rodar a célula de novo e o comando |
| o comando `/matinal-…` não aparece no chat | pasta errada aberta, ou chat fora do modo Agente | abrir a raiz do repositório; modo Agente |
| "não traz a linha de leitura: a mensagem não foi lida até o fim" | o Copilot não leu a mensagem inteira | rodar a célula de novo e repetir o comando |
| "ficou incompleta" ou "chegou incompleta" | o Copilot parou no meio da gravação | rodar a célula de novo e repetir o comando |
| "código de outra execução" | resposta de uma rodada anterior | esperar; repetir o comando se o prazo acabar |
| "Não consegui apagar …: o arquivo está em uso" | outro programa segurando a resposta velha | fechar o que o segura e rodar de novo |
| "N PDF(s) não renderam texto" | digitalização sem OCR | reimprimir em PDF |
| "arquivo(s) NÃO foram lidos" | arquivo que não é PDF em `input/comentario_matinal/` | reimprimir em PDF |
| "o comentário anterior em … não pôde ser lido" | o `anterior*.pdf` é imagem ou está corrompido | reimprimir em PDF |
| "não achei a tabela de temas candidatos" | a triagem saiu fora do formato | escrever os temas à mão em `TEMAS` |
| "a triagem de … não tem o tema N" | número fora da tabela | reler a tabela; ela diz até onde vai |
| a conferência acusa divergência | texto corrigido no Word e não repetido no `.md` | repetir no `.md`, ou entender o que sumiu |
| faixa vermelha de DRY RUN | fora da janela | é ensaio; não enviar |
| aviso de fuso | máquina fora de Brasília | as regras temporais do guia pressupõem Brasília↔Nova York |

## "a consulta de referência não devolveu dado algum"

O terminal Bloomberg não está aberto e logado nesta máquina. É o único passo que fala
com o terminal, e ele fala por IPC local — não há como coletar de outro lugar.

Abrir o terminal, logar, e repetir o Passo 1. Se o terminal está aberto e o erro
persiste, o `bbcomm` — o serviço que atende essa conexão — pode não ter subido junto com
o terminal: iniciar o `bbcomm.exe` da pasta `C:\blp\` à mão e repetir. E conferir que o
VS Code está rodando no Windows, e não conectado ao WSL.

Este erro interrompe: sem mercado não há painel, e sem painel não há horário de
redação para as etapas de texto.

## A consulta do calendário estoura

A consulta do calendário usa BQL, e nem toda licença tem BQL. O sintoma é a exceção
vindo da célula do calendário, com o painel de mercado tendo saído normalmente.

Trocar para `SEM_CALENDARIO = True` na célula do calendário e rodá-la de novo.

**Duas consequências, e as duas são visíveis.** O bloco direcional sai sem a agenda do
dia, e diz isso no próprio texto — as etapas de texto vão saber que não têm calendário.
E a montagem do documento, no Passo 7, passa a ser **recusada**: o template tem dois
lugares de imagem, e um deles ficaria vazio no que vai à diretoria.

Ou seja: sem o calendário dá para chegar até a revisão, não até o e-mail. Para fechar o
plantão é preciso uma máquina com licença BQL.

## "Nenhuma resposta da etapa … em 900s"

A célula esperou quinze minutos e nenhum arquivo de resposta apareceu. Quase sempre o
comando não foi rodado no chat, ou foi rodado noutra janela do VS Code, com outra pasta
aberta — a resposta foi gravada lá, e não aqui.

Rodar a célula de novo e, no chat do VS Code em que a pasta do repositório está aberta,
no modo Agente, o comando que a célula pedir.

## O comando `/matinal-…` não aparece no chat

Os comandos vêm de `.github/prompts/`, na raiz do repositório, e o VS Code só os enxerga
com a raiz aberta. Se a pasta aberta for `notebooks/` ou outra subpasta, eles somem.
**Arquivo → Abrir Pasta**, e escolher a pasta `mkt_intel`.

Com a raiz aberta, conferir que o Copilot está ativo (o ícone de conta, no canto inferior
esquerdo) e que o chat está no modo Agente.

## "não traz a linha de leitura: a mensagem não foi lida até o fim"

A mensagem traz um código de leitura em quatro pedaços espalhados pelo texto, e a
resposta tem de devolvê-lo montado. Resposta sem ele quer dizer que o Copilot não leu a
mensagem inteira — pulou trechos das fontes, ou respondeu sem abrir o arquivo. Uma
triagem ou uma revisão feitas assim não viram o que as fontes dizem.

Rodar a célula de novo — a mensagem sai com código novo — e repetir o comando no chat.
Se acontecer duas vezes seguidas, trocar o modelo no seletor do chat antes de repetir.

## "ficou incompleta" ou "chegou incompleta"

A resposta começou a ser gravada e não chegou à última linha, a de fim. O Copilot parou
no meio — cota esgotada, conexão caída, chat fechado. A célula não entrega metade de uma
resposta à etapa seguinte.

Rodar a célula de novo e repetir o comando no chat.

## "código de outra execução"

Chegou uma resposta com o código de uma rodada anterior: você rodou a célula de novo
antes de o chat da rodada anterior terminar, e ele terminou agora. A célula descarta essa
resposta e **continua esperando** a de agora, sem você fazer nada.

Se o prazo acabar só com respostas assim, a faixa vermelha diz isso: repetir o comando no
chat.

## "Não consegui apagar …: o arquivo está em uso"

Antes de gravar a mensagem nova, a célula apaga a resposta da rodada anterior, e algum
programa está segurando o arquivo — o antivírus, o indexador do Windows, ou o próprio
arquivo aberto numa aba do VS Code. Fechar a aba ou esperar alguns segundos, e rodar a
célula de novo.

## "N PDF(s) não renderam texto"

O PDF é digitalização sem OCR: uma imagem de página, sem camada de texto. A célula
nomeia os arquivos. Eles chegaram, foram abertos, e vieram vazios — a etapa vai rodar
sem eles.

Reimprimir em PDF a partir da origem: do Outlook, Arquivo → Imprimir → Microsoft Print
to PDF; do navegador, Ctrl+P → Salvar em PDF. Um PDF gerado assim tem texto.

É aviso, não erro: a etapa segue. Se o arquivo perdido era a fonte do tema dominante,
repetir o Passo 2 depois de corrigi-lo — a triagem sem ele não vai citar o que não leu.

## "arquivo(s) NÃO foram lidos"

Há algo em `input/comentario_matinal/` que não é PDF — um `.docx`, um `.msg` arrastado
do Outlook, um `.png` de gráfico. **Só PDF é aproveitado**, e o conteúdo desse arquivo
não chegou ao modelo.

A célula nomeia cada arquivo ignorado justamente porque a falta não produz erro. Sem o
aviso, ela só apareceria como a ausência de um tema na triagem — e essa ausência é
indistinguível de uma decisão editorial.

Reimprimir em PDF, pelos mesmos caminhos acima, e repetir o Passo 2.

## "o comentário anterior em … não pôde ser lido"

O `anterior*.pdf` está na pasta, mas não rendeu texto: é imagem, ou está corrompido. As
etapas seguem com o comentário arquivado nesta máquina, se houver, ou sem nenhum.
Reimprimir o e-mail em PDF e repetir a etapa.

## "não achei a tabela de temas candidatos"

A triagem rodou, mas a resposta não trouxe a tabela no formato esperado — e sem tabela
não há números para escolher.

Saída: escrever os temas à mão, em vez de escolhê-los pelo `ESCOLHA` — na célula do
Passo 3, atribuir o texto diretamente a `TEMAS`, um tema por linha começando por `- `,
o dominante primeiro. A resposta da triagem continua em `output/comentario_matinal/`, e
é dela que você tira o texto dos temas.

Rodar a triagem de novo também costuma resolver, e é mais barato que transcrever. Só não
vale rodar duas vezes sem olhar: se a segunda saiu no formato, compare o tema dominante
das duas antes de seguir.

## "a triagem de … não tem o tema N"

Você pôs no `ESCOLHA` um número que não existe na tabela — `[1, 3, 7]` quando a triagem
propôs cinco temas. A célula para antes de montar os temas.

Reler a tabela da triagem: ela diz até onde vai. O erro é quase sempre de contagem ao
ler a tabela na tela, não de decisão.

## A conferência acusa divergência

Alguma coisa mudou no `.docx` que não está no `.md`. Este é o passo funcionando: ele
existe para mostrar exatamente isso.

Se a mudança foi sua e intencional, repeti-la no `.md` — é o `.md` que fica arquivado.
Se você não reconhece a mudança, ela é acidente, e este é o último momento em que tem
conserto.

Não pule por parecer improvável: em 17/08 foram quatro palavras, e o e-mail saiu
quebrado. O caso está contado no
[Passo 8](03-runbook.md#passo-8--conferência-antes-do-e-mail), e como separar o
intencional do acidente, em
[O que é seu decidir](04-decisoes.md#a-divergência-do-conferir).

## Faixa vermelha de DRY RUN

A execução está fora da janela de 7h–9h. A primeira célula mostra a faixa, e o painel
em texto sai carimbado com `PAINEL DIRECIONAL — DRY RUN`.

**Nada é bloqueado, e nada está errado.** Ensaiar fora da janela é uso legítimo, e o
carimbo existe para dizer o que aquele arquivo é — ver
[A janela e o dry run](01-primeiro-dia.md#a-janela-e-o-dry-run).

O que **não** se faz num dry run é enviar o e-mail e rodar o `enviado`. Se a faixa
apareceu num plantão de verdade, o relógio da máquina está errado.

## Aviso de fuso

A máquina não está no fuso de Brasília. O notebook informa o offset que encontrou e
segue rodando.

A janela continua fazendo sentido como hora do analista. O que não vale mais é a
relação **Brasília↔Nova York** que as regras temporais do guia pressupõem — o que já
foi divulgado, o que ainda não foi, e o que sai depois da redação. Os horários do
calendário chegam do terminal no fuso dele.

Rodando de outro fuso, conferir o status de cada indicador do dia à mão, no calendário
em texto, antes de citá-lo.

## Nada disso é o meu caso

A faixa vermelha nomeia sempre o arquivo e a etapa. Duas verificações resolvem a maioria
do resto:

1. **Os arquivos do dia estão em `output/comentario_matinal/`?** As etapas não
   recoletam nada: cada uma lê o que a anterior gravou. Falta de insumo é sempre uma
   célula não rodada, e a faixa diz qual.
2. **A data é a de hoje?** Todos os nomes carregam `AAAAMMDD`. Um plantão iniciado
   antes da meia-noite e continuado depois procura arquivos de outra data.
