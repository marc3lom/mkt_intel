# Runbook do plantão

Os nove passos, contados no terminal, mais [o envio](#o-envio) — que não tem número
porque nenhuma linha de código participa dele, e que fica entre o Passo 8 e o Passo 9.
O quanto cada um demora e por que o roteiro é
contado em tempo relativo estão em [O primeiro dia](01-primeiro-dia.md#quanto-tempo-leva);
o que muda ao rodar por `notebooks/plantao.ipynb` está em
[As duas formas de rodar](01-primeiro-dia.md#as-duas-formas-de-rodar).

## Passo 1 — Coleta (T0)

Reunir as fontes do dia: wraps da Bloomberg, First Word, e-mails de sell-side, matérias
do Financial Times ou do Wall Street Journal. **Salvar em PDF dentro de `fontes/`** — é
de lá que as etapas de IA leem, e a pasta fica fora do repositório.

**Só PDF é lido.** `.docx`, `.png`, `.msg` e afins ficam de fora: as etapas recebem
texto, nunca anexo nem imagem, para que o insumo não mude com o backend. O comando
lista no stderr todo arquivo que deixou de ler, com nome — um `.docx` na pasta não
produz erro, e sem esse aviso a falta só apareceria como a ausência de um tema na
triagem. Do Outlook, Arquivo → Imprimir → Microsoft Print to PDF; do navegador,
Ctrl+P → Salvar em PDF.

Os PDFs da Bloomberg trazem marcação de uso exclusivo nominal e vedação à
redistribuição. O material não é redistribuído em nenhuma hipótese: apenas o conteúdo
informa a redação do comentário, que é produto derivado e interno. Os PDFs não entram
no repositório (ver `.gitignore`), e a `fontes/` é esvaziada no Passo 9.

Gerar as saídas do dia:

```
uv run matinal
```

Uma execução, uma consulta de mercado, quatro arquivos em `saida/`:

| Arquivo | Uso |
|---|---|
| `painel_AAAAMMDD.png` | grade de ativos, para colar no e-mail |
| `calendario_AAAAMMDD.png` | tabela de divulgações e bancos centrais, idem |
| `painel_AAAAMMDD.txt` | bloco direcional, insumo das etapas de IA |
| `calendario_AAAAMMDD.md` | o mesmo calendário em texto, idem |

Os quatro saem do mesmo conjunto de dados. O texto não recalcula direção nenhuma: ele lê
os mesmos números que cada tile da imagem renderizou. Por construção, a imagem enviada à
diretoria e o texto usado na conferência não podem discordar sobre a direção de um ativo.

O comando carimba o horário de execução na imagem e no texto. Se o painel for gerado bem
antes da redação, regerá-lo — direção de ativo muda, e o painel é a referência de
coerência do texto. Para reproduzir um horário específico, `--asof 2026-08-14T07:35`;
vale para a imagem e para o texto, mas **não** para a tabela do calendário, que sempre
traz o estado corrente do BQL.

**Anote o horário em que a coleta terminou. Ele é o horário de redação do dia** e
acompanha o trabalho até a revisão.

## Passo 2 — Triagem (T0 + 5 min)

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

As duas bandeiras abaixo valem para as três etapas de IA — triagem, redação e revisão.

Por padrão a etapa roda **sem ferramenta alguma**: tudo vai injetado na mensagem. `--web`
libera busca para confirmar dado já presente nas fontes, como os prompts permitem, e
nesse caso a etapa é instruída a registrar cada consulta no bloco de auditoria — o guia
exige sinalização explícita, e o revisor precisa saber que houve.

O modelo é o que estiver configurado na CLI do Claude Code; `--modelo` fixa por execução.

## Passo 3 — Decisão editorial (T0 + 10 min)

**Este é o único passo que não se delega.** Ler a tabela, conferir os alertas —
sobretudo os de dado ainda não divulgado e os de divergência com o painel — e definir o
tema dominante e os dois ou três temas seguintes, em ordem.

Não pular esta etapa em dia corrido. É onde se evita excesso de temas e dado antecipado.

Como decidir, e o que a interface do comando junta e você precisa separar, está em
[O que é seu decidir](04-decisoes.md#a-escolha-de-temas).

## Passo 4 — Redação (T0 + 15 min)

```
uv run matinal redacao --temas-numeros "1,3,2"
```

Os números são os da tabela de temas candidatos da triagem, na ordem de relevância e com
o dominante primeiro. O texto sai da própria triagem: retranscrever a descrição à mão é
trabalho de cópia, e cópia erra.

**É por aqui que a decisão do passo 3 entra no fluxo** — o comando recusa rodar sem os
temas, porque a hierarquia é escolha do autor e não do modelo.

O que os números não dizem é a **ressalva**: um limite temporal, uma atribuição
obrigatória, uma direção que o painel contradiz. Para acrescentá-la, escrever os temas em
vez de escolhê-los, com `--temas "dominante | tema 2"` ou `--temas-arquivo temas.md`. Em
17/08 foi uma ressalva assim — "as moedas estão estáveis na sessão corrente" — que
impediu o comentário de afirmar que o dólar caíra no dia, quando o painel mostrava o
câmbio estável.

A redação recebe os alertas da triagem automaticamente, extraídos da seção C do arquivo
da etapa anterior. Sai `saida/redacao_AAAAMMDD.md`, com o comentário e o bloco de
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

A auditoria da revisão fecha com os pontos que permanecem sob julgamento do autor; como
decidi-los está em [O que é seu decidir](04-decisoes.md#os-pontos-sob-julgamento-do-autor).

## Passo 7 — Montagem do documento

O texto revisado já está em `saida/comentario_AAAAMMDD.md` — o Passo 6 o gravou, e o
comando imprimiu o caminho. Editar esse arquivo, e não uma cópia: é ele que o Passo 8
compara com o `.docx`, e é ele que o Passo 9 arquiva. Um marcador por parágrafo.

```
uv run matinal --comentario saida/comentario_AAAAMMDD.md
```

**Exceção:** se o Passo 6 não gravou o `.md` — bloco de código malformado —, aí sim
salvar o texto à mão a partir da revisão, com esse mesmo nome e nessa mesma pasta.
Salvá-lo noutro lugar faz o Passo 8 comparar o documento com um arquivo que você não
editou, e acusar divergências que são artefato do par errado.

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
exportar o PDF. **O gráfico é opcional e não sai do comando** — é uma imagem que você
mesmo monta, quando algum tema pede ilustração, e cola à mão no Word; a maioria dos dias
não tem nenhum. **O PDF não é gerado pelo comando**: a exportação é feita do Word, na
mesma passagem em que o analista confere o documento.

## Passo 8 — Conferência, antes do e-mail

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

Separar a divergência intencional do acidente é decisão sua:
[O que é seu decidir](04-decisoes.md#a-divergência-do-conferir).

## O envio

Este passo não tem número, e a razão é boba mas vale saber: os nove números são os
passos que o comando executa, e são os mesmos no notebook, célula a célula. O envio é
inteiramente seu — nenhuma linha de código participa dele. Ele acontece entre o Passo 8
e o Passo 9.

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
> um canal que ninguém na divisão enxerga. É a falha de 17/08 outra vez, e pior: lá os
> dois artefatos em desacordo eram o `.docx` e o `.md`, e a conferência apanhou o
> problema, ainda que tarde. Aqui os dois só concordam se alguém se lembrar de refazer
> o PDF — nenhuma checagem compara o PDF com coisa alguma.

### Por que o anexo não é redundante

Esta é a parte que precisa ser entendida, e não só cumprida.

Olhando a mensagem pronta, a conclusão razoável é que o anexo sobra: o corpo já carrega
o texto e as duas tabelas, e quem lê o e-mail não precisa abrir arquivo nenhum. A
conclusão é razoável e está errada.

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
comentário.

Isso responde à pergunta que você de fato vai ter, que não é "quais são os endereços" —
eles já vêm — e sim **"fulano ficou de fora, o que eu faço"**. Incluir alguém, tirar
alguém, corrigir um endereço errado: o pedido vai ao mestre de TI do DEPIN, e não à
janela de destinatários do Outlook.

Consertar a lista à mão parece o caminho curto, e é o caminho que a estraga. Cada
plantonista corrige um pouco à sua maneira, ninguém registra o que corrigiu, e em
algumas semanas quem recebe o comentário depende de quem estava de plantão. A deriva é
**invisível**: o e-mail sai normalmente todas as manhãs, e ninguém que ficou de fora
escreve para avisar que não recebeu.

### O que ainda falta nesta página

O endereço em si não está neste repositório, e não deve estar: a lista é operada no
DEPIN e muda sem que o repositório fique sabendo. Copie os destinatários do e-mail do dia
anterior. O que importa aqui não é a identificação — é saber para quem se escreve, e isso
está logo acima.

O assunto é sempre o mesmo, sem data:

```
Comentário Matinal – Mesa de Investimentos (DEPIN/DIRIN)
```

Ele não varia com o dia, e não precisa variar: o comentário é diário e o corpo já traz a
referência. Um assunto constante é o que faz a série ficar agrupada na caixa de quem
recebe.

Correção enviada depois leva o prefixo `[ERRATA]` — foi o que se fez em 17/08, quando
quatro palavras haviam sumido do documento durante a edição à mão.

Enviado o e-mail — e só então — seguir para o Passo 9.

## Passo 9 — Após o envio

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

Quando cada uma delas é legítima de contornar está em
[O que é seu decidir](04-decisoes.md#quando-é-legítimo-forçar-o-arquivamento).

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
