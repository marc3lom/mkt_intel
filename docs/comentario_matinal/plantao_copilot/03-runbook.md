# Runbook do plantão

Os nove passos, contados no notebook `notebooks/comentario_matinal/plantao_copilot.ipynb`,
mais [o envio](#o-envio) — que não tem número porque nenhuma linha de código participa
dele, e que fica entre o Passo 8 e o Passo 9. O quanto cada um demora e por que o roteiro
é contado em tempo relativo estão em [O primeiro dia](01-primeiro-dia.md#quanto-tempo-leva).

Rodar as células na ordem, de cima para baixo: cada uma consome o que a anterior gravou
em `output/comentario_matinal/`. Os títulos das células de texto do notebook trazem os
mesmos números de passo desta página.

## Passo 1 — Coleta (T0)

Reunir as fontes do dia: wraps da Bloomberg, First Word, e-mails de sell-side, matérias
do Financial Times ou do Wall Street Journal. **Salvar em PDF dentro de
`input/comentario_matinal/`** — é de lá que as etapas de texto leem, e a pasta fica fora
do repositório.

**Só PDF é lido.** `.docx`, `.png`, `.msg` e afins ficam de fora: as etapas recebem
texto, nunca anexo nem imagem. A etapa lista todo arquivo que deixou de ler, com nome —
um `.docx` na pasta não produz erro, e sem esse aviso a falta só apareceria como a
ausência de um tema na triagem. Do Outlook, Arquivo → Imprimir → Microsoft Print to PDF;
do navegador, Ctrl+P → Salvar em PDF.

**O comentário do dia anterior também pode ir na pasta**, em PDF, com nome começando por
`anterior` — `anterior_2026-09-28.pdf`, por exemplo. Ele não é lido como fonte: vai para
o campo próprio, contra o qual a triagem julga o ineditismo dos temas e a revisão procura
contradição com o que já se disse. É opcional, e quando está lá vale mais que o
comentário arquivado nesta máquina, que pode ser de dias antes — no rodízio, o de ontem
quase sempre foi enviado por outro colega. Sem nenhum dos dois, as etapas trabalham só
com as fontes.

Os PDFs da Bloomberg trazem marcação de uso exclusivo nominal e vedação à
redistribuição. O material não é redistribuído em nenhuma hipótese: apenas o conteúdo
informa a redação do comentário, que é produto derivado e interno. Os PDFs não entram
no repositório, e a `input/comentario_matinal/` é esvaziada no Passo 9.

Com o terminal Bloomberg aberto e logado, rodar a primeira célula — a faixa verde ou
vermelha diz se esta execução é plantão ou ensaio — e as quatro células do Passo 1:
coleta, painel, calendário e bloco direcional. Uma consulta de mercado, quatro arquivos
em `output/comentario_matinal/`:

| Arquivo | Uso |
|---|---|
| `painel_AAAAMMDD.png` | grade de ativos, para colar no e-mail |
| `calendario_AAAAMMDD.png` | tabela de divulgações e bancos centrais, idem |
| `painel_AAAAMMDD.txt` | bloco direcional, insumo das etapas de texto |
| `calendario_AAAAMMDD.md` | o mesmo calendário em texto, idem |

Os quatro saem do mesmo conjunto de dados. O texto não recalcula direção nenhuma: ele lê
os mesmos números que cada tile da imagem renderizou. Por construção, a imagem enviada à
diretoria e o texto usado na conferência não podem discordar sobre a direção de um ativo.

O painel carrega o horário de execução na imagem e no texto. Se ele for gerado bem antes
da redação, regerá-lo — direção de ativo muda, e o painel é a referência de coerência do
texto.

Numa máquina sem licença BQL, trocar para `SEM_CALENDARIO = True` na célula do
calendário — ver [Quando dá errado](05-quando-da-errado.md#a-consulta-do-calendário-estoura).

**Anote o horário em que a coleta terminou. Ele é o horário de redação do dia** e
acompanha o trabalho até a revisão.

## Durante as etapas de texto

Os passos 2, 4 e 6 funcionam do mesmo jeito, e vale entender uma vez.

A célula monta a mensagem da etapa — o guia de estilo, o prompt da etapa, as fontes, o
painel, o calendário e o que mais a etapa precisa — e a grava em
`output/comentario_matinal/copilot/`. Em seguida mostra qual comando rodar e fica
esperando, com o indicador de execução girando. Então:

1. Abrir o chat do Copilot: **Ctrl+Alt+I**, ou o ícone do chat na barra do VS Code.
2. No seletor embaixo da caixa de texto, escolher o modo **Agente**.
3. Digitar o comando que a célula pediu — `/matinal-triagem`, `/matinal-redacao` ou
   `/matinal-revisao` — e enviar.
4. Esperar. O Copilot lê a mensagem em trechos, porque ela é longa, e grava a resposta em
   `output/comentario_matinal/copilot/`. Se o VS Code pedir para confirmar a gravação do
   arquivo, confirmar. Ao terminar, o chat diz "Resposta gravada."
5. A célula percebe a resposta sozinha, confere e continua. Não é preciso rodá-la de novo.

**A célula confere se a mensagem foi lida inteira.** A mensagem traz um código de leitura
em quatro pedaços espalhados pelo texto, e a resposta tem de devolvê-lo montado, na
primeira e na última linha. Sem o código, a resposta é recusada: é o sinal de que o
Copilot pulou parte das fontes ou parou no meio da gravação. Resposta com o código de uma
execução anterior é descartada, e a célula continua esperando a de agora.

A espera dura até **15 minutos**. Interromper a célula (o quadrado ao lado dela) cancela a
espera; rodá-la de novo gera uma mensagem nova, com código novo, e o comando se repete no
chat.

As etapas rodam **sem acesso à web**: tudo o que o modelo usa está na mensagem. O modelo
é o escolhido no seletor de modelo do chat; mantê-lo o mesmo nas três etapas do dia.

## Passo 2 — Triagem (T0 + 5 min)

Antes de rodar, conferir que os PDFs do dia estão em `input/comentario_matinal/`. Rodar a
célula da triagem e, no chat, `/matinal-triagem`.

A célula converte os PDFs para texto, monta a mensagem e, recebida a resposta, a grava em
`output/comentario_matinal/triagem_AAAAMMDD.md` e a mostra formatada logo abaixo: a
tabela de temas candidatos, o tema dominante proposto, os alertas e a sugestão de corte.

**O horário de redação não é informado à mão: vem do carimbo do painel**, que é o
término da coleta.

**O comentário do dia anterior entra sozinho**: o `anterior*.pdf` das fontes, se houver;
senão o comentário arquivado mais recente desta máquina, da última semana. A célula diz
qual foi usado, ou avisa que não havia nenhum — os avisos aparecem antes de a mensagem
ser gravada, para que você possa interromper e resolver antes de esperar.

## Passo 3 — Decisão editorial (T0 + 10 min)

**Este é o único passo que não se delega.** Ler a tabela, conferir os alertas —
sobretudo os de dado ainda não divulgado e os de divergência com o painel — e definir o
tema dominante e os dois ou três temas seguintes, em ordem.

Não pular esta etapa em dia corrido. É onde se evita excesso de temas e dado antecipado.

A célula do Passo 3 interrompe a execução de propósito, com uma faixa âmbar — ela não é
erro. Editar a lista `ESCOLHA` na célula logo abaixo, com os números da tabela, o
dominante primeiro, e seguir dali. Como decidir, e como acrescentar uma ressalva que a
tabela não tem, está em [O que é seu decidir](04-decisoes.md#a-escolha-de-temas).

## Passo 4 — Redação (T0 + 15 min)

Rodar a célula da redação e, no chat, `/matinal-redacao`.

A redação recebe os temas da célula do Passo 3 e os alertas da triagem, extraídos da
seção C do arquivo da etapa anterior — não é preciso copiá-los à mão. Sai
`output/comentario_matinal/redacao_AAAAMMDD.md`, com o comentário e o bloco de
auditoria.

Conferir o bloco de auditoria: contagem total dentro de 350–500, orçamento por marcador,
mapeamento marcador → fonte, ressalvas.

## Passo 5 — Passagem ao revisor

**Regra de folga: a passagem ocorre com pelo menos dez minutos de antecedência sobre o
horário de envio pretendido — no limite, 8h50.** Se a coleta atrasou e essa folga não
existe mais, avisar o revisor antes de mandar, para que ele priorize as correções
obrigatórias e trate as sugestões como descartáveis.

Enviar ao segundo analista: texto, PDFs das fontes, `painel_AAAAMMDD.txt`, bloco de
auditoria e **o horário de redação**.

## Passo 6 — Revisão

Rodar a célula da revisão e, no chat, `/matinal-revisao`.

A revisão lê o comentário e o bloco de auditoria da redação e grava
`output/comentario_matinal/revisao_AAAAMMDD.md` — correções obrigatórias, sugestões,
texto revisado e auditoria da revisão. Grava também
`output/comentario_matinal/comentario_AAAAMMDD.md`, extraído do bloco de código da seção
3, que é o insumo do Passo 7.

**Se esse bloco não vier no formato esperado, a célula para e não grava o `.md`.** É o
único ponto em que a saída do modelo entra direto no documento que vai à diretoria, e um
arquivo malformado só apareceria no Word. Nesse caso, extrair o texto à mão da revisão —
ver o [Passo 7](#passo-7--montagem-do-documento).

A revisão também recebe o comentário do dia anterior, pela mesma regra da triagem — é
dele que sai a checagem de contradição não sinalizada entre um dia e o seguinte.

O horário informado é o do autor, não o do revisor. Um comentário redigido às 7h35 e
outro às 7h55 podem descrever quadros diferentes de forma legítima — releases europeus e
britânicos saem entre 3h e 6h de Nova York, dentro da janela de redação. O revisor precisa
saber contra qual momento está conferindo.

Tratar primeiro as correções obrigatórias; as sugestões são opcionais e ficam a critério
do autor. A auditoria da revisão fecha com os pontos que permanecem sob julgamento do
autor; como decidi-los está em
[O que é seu decidir](04-decisoes.md#os-pontos-sob-julgamento-do-autor).

## Passo 7 — Montagem do documento

O texto revisado já está em `output/comentario_matinal/comentario_AAAAMMDD.md` — o
Passo 6 o gravou, e a célula mostrou o caminho. Editar esse arquivo, e não uma cópia: é
ele que o Passo 8 compara com o `.docx`, e é ele que o Passo 9 arquiva. Um marcador por
parágrafo. Depois, rodar a célula do Passo 7.

**Exceção:** se o Passo 6 não gravou o `.md` — bloco de código malformado —, salvar o
texto à mão a partir da revisão, com esse mesmo nome e nessa mesma pasta, e montar pelo
terminal, na raiz do repositório:

```
uv run matinal --comentario output/comentario_matinal/comentario_AAAAMMDD.md
```

Salvá-lo noutro lugar faz o Passo 8 comparar o documento com um arquivo que você não
editou, e acusar divergências que são artefato do par errado.

Sai `output/comentario_matinal/comentario_AAAAMMDD.docx`, a partir de
`templates/comentario_matinal/comentario.dotx`, com o painel no alto e a tabela do
calendário depois dos marcadores. Do Markdown, `- ` vira parágrafo com o marcador do
template, `*termo*` vira itálico e `**termo**` vira negrito. O fecho vem do template; se
o Markdown trouxer um, ele é descartado com aviso.

**A montagem não consulta a Bloomberg.** Ela reaproveita o painel e o calendário já
gerados para a data — o comentário é escrito depois do painel, e recoletar produziria um
documento com o mercado de agora sob um texto redigido contra o de antes. Sem a tabela do
calendário a montagem é recusada: o template tem dois lugares de imagem.

A célula avisa quando o comentário sai da faixa de quatro a cinco marcadores que o guia
fixa, e quando alguma linha fora de marcador foi ignorada.

Abrir o `.docx` no Word para inserir o gráfico do dia, quando houver, conferir o texto e
exportar o PDF. **O gráfico é opcional e não sai do notebook** — é uma imagem que você
mesmo monta, quando algum tema pede ilustração, e cola à mão no Word; a maioria dos dias
não tem nenhum. **O PDF não é gerado pelo notebook**: a exportação é feita do Word, na
mesma passagem em que se confere o documento.

## Passo 8 — Conferência, antes do e-mail

Rodar a célula da conferência **depois** de editar o `.docx` no Word e **antes** de
mandar o e-mail.

Ela compara marcador a marcador o `.docx` com o `.md` e mostra os trechos que diferem,
com as palavras em volta para situar. Não arquiva, não limpa, não toca em nada: só lê os
dois arquivos e responde.

Toda correção feita no Word aparece aqui. As intencionais devem ser repetidas no `.md`,
que é o que fica arquivado. As não intencionais — palavra comida por um clique fora do
lugar, trecho perdido numa substituição — são justamente o que este passo existe para
apanhar, e **este é o último momento em que ainda têm conserto**.

Vale a pena mesmo quando o texto parece igual ao que saiu da revisão. Na primeira rodada
em produção, quatro palavras haviam sumido do documento durante a edição manual, entre
elas o `swap` de "mercados de swap", e o e-mail saiu com a frase quebrada. A conferência
rodou depois do envio, quando já não adiantava.

Separar a divergência intencional do acidente é decisão sua:
[O que é seu decidir](04-decisoes.md#a-divergência-do-conferir).

## O envio

Este passo não tem número: os nove números são os passos que o processo executa, e o
envio é inteiramente seu — nenhuma linha de código participa dele. Ele acontece entre o
Passo 8 e o Passo 9.

**O corpo do e-mail é o texto do `.docx` final, com as tabelas.** Não é um recado de
encaminhamento apontando para um anexo. Quem abre a mensagem vê o comentário: os
marcadores, o painel e a tabela do calendário, na própria mensagem. Copiar do `.docx`
já pronto — é para isso que ele foi montado com as duas imagens no lugar.

**O anexo é esse mesmo `.docx` exportado em PDF**, do Word, na mesma passagem em que
você conferiu o documento no Passo 7.

> **Se o Passo 8 acusou alguma divergência e você editou o `.docx`, exporte o PDF de
> novo.** O que você tem na mão é o PDF de antes da correção.
>
> Sem isso, o corpo do e-mail leva o texto corrigido e o anexo leva o antigo — e é o
> anexo que a chefia encaminha por WhatsApp. A diretoria receberia a versão errada, por
> um canal que ninguém na divisão enxerga, e nenhuma checagem compara o PDF com coisa
> alguma.

### Por que o anexo não é redundante

Olhando a mensagem pronta, a conclusão razoável é que o anexo sobra: o corpo já carrega
o texto e as duas tabelas. A conclusão é razoável e está errada.

**O PDF existe para que a chefia do DEPIN o encaminhe por WhatsApp ao grupo da
diretoria.** Ninguém na divisão tem acesso a esse grupo — só a chefia — e o
encaminhamento é feito à mão, a partir do anexo do e-mail que ela recebe. Sem o PDF
anexado, não há o que encaminhar.

E a falha é **silenciosa**. Um e-mail sem anexo não gera erro, não volta, e não parece
incompleto para quem o lê no Outlook. A diretoria simplesmente não recebe o comentário
naquele dia, e ninguém na divisão está no grupo para notar. É por isso que o anexo é
regra e não conveniência.

### Os destinatários não são seus para editar

**A lista de distribuição é mantida pela TI do DEPIN**, não por quem escreve o
comentário. Incluir alguém, tirar alguém, corrigir um endereço errado: o pedido vai ao
mestre de TI do DEPIN, e não à janela de destinatários do Outlook.

Consertar a lista à mão parece o caminho curto, e é o caminho que a estraga. Cada
plantonista corrige um pouco à sua maneira, ninguém registra o que corrigiu, e em
algumas semanas quem recebe o comentário depende de quem estava de plantão. A deriva é
**invisível**: o e-mail sai normalmente todas as manhãs, e ninguém que ficou de fora
escreve para avisar que não recebeu.

### Endereço e assunto

O endereço não está neste repositório, e não deve estar: a lista é operada no DEPIN e
muda sem que o repositório fique sabendo. Copie os destinatários do e-mail do dia
anterior.

O assunto é sempre o mesmo, sem data:

```
Comentário Matinal – Mesa de Investimentos (DEPIN/DIRIN)
```

Um assunto constante é o que faz a série ficar agrupada na caixa de quem recebe.
Correção enviada depois leva o prefixo `[ERRATA]`.

Enviado o e-mail — e só então — seguir para o Passo 9.

## Passo 9 — Após o envio

No terminal do VS Code (**Terminal → Novo Terminal**), na raiz do repositório:

```
uv run matinal enviado
```

Arquiva `arquivo/comentario_matinal/AAAA/MM/AAAAMMDD.md` e o `.docx` do dia, e esvazia
`input/comentario_matinal/` e `output/comentario_matinal/`. **Rodar só depois de o
e-mail ter saído** — o comando afirma que o comentário foi enviado.

O arquivo é desta máquina: ele não vai ao repositório nem aos outros colegas. É dele que
sai o comentário do dia anterior do seu próximo plantão aqui, quando ninguém anexar o
`anterior*.pdf`.

Antes de arquivar, o comando **repete a comparação do Passo 8** e para sem arquivar nada
se os dois divergirem. Aqui a checagem já não salva o comentário de hoje — o e-mail saiu.
Ela protege o insumo de um plantão futuro: registrar um texto que não foi o enviado não
erra hoje, erra depois, como contradição inventada.

Três recusas, todas contornáveis com `--forcar`, que é rombudo e passa pelas três de
uma vez:

| Recusa | Por quê |
|---|---|
| Fora da janela de 7h–9h | É a única etapa que bloqueia. As outras produzem artefato, carimbado como ensaio; esta afirma um envio |
| `.docx` e `.md` divergem | Ver acima |
| Já existe comentário arquivado para a data | Rearquivar por engano apagaria em silêncio o comentário de um dia já enviado |

Quando cada uma delas é legítima de contornar está em
[O que é seu decidir](04-decisoes.md#quando-é-legítimo-forçar-o-arquivamento).

A limpeza só ocorre **depois** de o arquivamento dar certo. Falhando o arquivamento,
nada é apagado.

**O nome do arquivo é lido pelo processo**, não é só convenção de organização. Nome fora
do padrão `AAAAMMDD.md` é ignorado em silêncio, e a checagem de ineditismo roda sem base.

Os arquivos de etapa — `triagem`, `redacao`, `revisao`, com seus blocos de auditoria —
vão embora na limpeza. Para guardar a memória de como um comentário foi construído,
copiá-los à mão antes de rodar `enviado`.

Antes de fechar o VS Code, **limpar as saídas do notebook** (o botão **Limpar Todas as
Saídas**, no topo): as células executadas carregam dados de mercado e o texto do
comentário.

## Referência de fusos

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
