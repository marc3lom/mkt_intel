# Quando dá errado

Os avisos e erros do comando saem no stderr, em português e nomeando o arquivo. Procure
aqui pelo trecho que apareceu na sua tela.

| Sintoma | Causa | Saída |
|---|---|---|
| "a consulta de referência não devolveu dado algum" | terminal Bloomberg inativo | abrir o terminal e repetir |
| a consulta do calendário estoura | máquina sem licença BQL | `--sem-calendario`, ou `SEM_CALENDARIO` no notebook |
| "N PDF(s) não renderam texto" | digitalização sem OCR | reimprimir em PDF |
| "arquivo(s) NÃO foram lidos" | arquivo que não é PDF em `fontes/` | reimprimir em PDF |
| "não achei a tabela de temas candidatos" | a triagem saiu fora do formato | escrever os temas à mão, sem os números |
| "a triagem de … não tem o tema N" | número fora da tabela | reler a tabela; ela diz até onde vai |
| o `conferir` acusa divergência | texto corrigido no Word e não repetido no `.md` | repetir no `.md`, ou entender o que sumiu |
| banner de DRY RUN | fora da janela | é ensaio; não enviar |
| aviso de fuso | máquina fora de Brasília | as regras temporais do guia pressupõem Brasília↔Nova York |

## "a consulta de referência não devolveu dado algum"

O terminal Bloomberg não está aberto e logado nesta máquina. É o único passo que fala
com o terminal, e ele fala por IPC local — não há como coletar de outro lugar.

Abrir o terminal, logar, e repetir o Passo 1. Se o terminal está aberto e o erro
persiste, conferir que o comando está rodando do Windows nativo e não do WSL.

Este erro interrompe: sem mercado não há painel, e sem painel não há horário de
redação para as etapas de IA.

## A consulta do calendário estoura

A consulta do calendário usa BQL, e nem toda licença tem BQL. O sintoma é a exceção
vindo da consulta do calendário, com o painel de mercado tendo saído normalmente.

No terminal, `uv run matinal --sem-calendario`. No notebook, `SEM_CALENDARIO = True` na
célula do calendário.

**Duas consequências, e as duas são visíveis.** O bloco direcional sai sem a agenda do
dia, e diz isso no próprio texto — as etapas de IA vão saber que não têm calendário. E
a montagem do documento, no Passo 7, passa a ser **recusada**: o template tem dois
lugares de imagem, e um deles ficaria vazio no que vai à diretoria.

Ou seja: `--sem-calendario` permite chegar até a revisão, não até o e-mail. Para fechar
o plantão é preciso uma máquina com licença BQL.

## "N PDF(s) não renderam texto"

O PDF é digitalização sem OCR: uma imagem de página, sem camada de texto. O comando
nomeia os arquivos. Eles chegaram, foram abertos, e vieram vazios — a etapa vai rodar
sem eles.

Reimprimir em PDF a partir da origem: do Outlook, Arquivo → Imprimir → Microsoft Print
to PDF; do navegador, Ctrl+P → Salvar em PDF. Um PDF gerado assim tem texto.

É aviso, não erro: a etapa segue. Se o arquivo perdido era a fonte do tema dominante,
repetir o Passo 2 depois de corrigi-lo — a triagem sem ele não vai citar o que não leu.

## "arquivo(s) NÃO foram lidos"

Há algo em `fontes/` que não é PDF — um `.docx`, um `.msg` arrastado do Outlook, um
`.png` de gráfico. **Só PDF é aproveitado**, para que o insumo não mude com o backend
do modelo, e o conteúdo desse arquivo não chegou ao modelo.

O comando nomeia cada arquivo ignorado justamente porque a falta não produz erro. Sem
o aviso, ela só apareceria como a ausência de um tema na triagem — e essa ausência é
indistinguível de uma decisão editorial.

Reimprimir em PDF, pelos mesmos caminhos acima, e repetir o Passo 2.

## "não achei a tabela de temas candidatos"

A triagem rodou, mas a saída não trouxe a tabela no formato esperado — e sem tabela não
há números para escolher. Acontece quando o modelo responde fora de formato.

Saída: escrever os temas à mão, sem os números. `--temas "dominante | tema 2"` ou
`--temas-arquivo temas.md`. O arquivo da triagem continua em `saida/`, e é dele que
você tira o texto dos temas.

Rodar a triagem de novo também costuma resolver, e é mais barato que transcrever. Só
não vale rodar duas vezes sem olhar: se a segunda saiu no formato, compare o tema
dominante das duas antes de seguir.

## "a triagem de … não tem o tema N"

Você pediu um número que não existe na tabela — `--temas-numeros "1,3,7"` quando a
triagem propôs cinco temas. O comando para antes de escrever qualquer coisa.

Reler a tabela da triagem: ela diz até onde vai. O erro é quase sempre de contagem ao
ler a tabela na tela, não de decisão.

## O `conferir` acusa divergência

Alguma coisa mudou no `.docx` que não está no `.md`. Este é o passo funcionando: ele
existe para mostrar exatamente isso.

Se a mudança foi sua e intencional, repeti-la no `.md` — é o `.md` que fica versionado
e que a triagem de amanhã lê. Se você não reconhece a mudança, ela é acidente, e este é
o último momento em que tem conserto.

Não pule por parecer improvável: em 17/08 foram quatro palavras, e o e-mail saiu
quebrado. O caso está contado no
[Passo 8](03-runbook.md#passo-8--conferência-antes-do-e-mail), e como separar o
intencional do acidente, em
[O que é seu decidir](04-decisoes.md#a-divergência-do-conferir).

## Banner de DRY RUN

A execução está fora da janela de 7h–9h. O comando abre com o banner no stderr e
carimba o painel em texto com `PAINEL DIRECIONAL — DRY RUN`.

**Nada é bloqueado, e nada está errado.** Ensaiar fora da janela é uso legítimo, e o
carimbo existe para dizer o que aquele arquivo é — ver
[A janela e o dry run](01-primeiro-dia.md#a-janela-e-o-dry-run).

O que **não** se faz num dry run é enviar o e-mail e rodar o `enviado`. Se o banner
apareceu num plantão de verdade, o relógio da máquina está errado — a decisão sai do
relógio real, nunca do `--asof`.

## Aviso de fuso

A máquina não está no fuso de Brasília. O comando informa o offset que encontrou e
segue rodando.

A janela continua fazendo sentido como hora do analista. O que não vale mais é a
relação **Brasília↔Nova York** que as regras temporais do guia pressupõem — o que já
foi divulgado, o que ainda não foi, e o que sai depois da redação. Os horários do
calendário chegam do terminal no fuso dele.

Rodando de outro fuso, conferir o status de cada indicador do dia à mão, no calendário
em texto, antes de citá-lo.

## Nada disso é o meu caso

O comando nomeia sempre o arquivo e a etapa. Duas verificações resolvem a maioria do
resto:

1. **Os arquivos do dia estão em `saida/`?** As etapas não recoletam nada: cada uma lê
   o que a anterior gravou. Falta de insumo é sempre uma etapa não rodada, e o comando
   diz qual.
2. **A data é a de hoje?** Todos os nomes carregam `AAAAMMDD`. Um plantão iniciado
   antes da meia-noite e continuado depois procura arquivos de outra data.
