# O que é seu decidir

O processo automatiza tudo o que é verificável e para em quatro pontos. Nos quatro, o
comando poderia ter chutado; em nenhum ele chuta, porque um chute plausível é pior que
uma parada — ele passa despercebido.

## A escolha de temas

Acontece entre o Passo 2 e o Passo 4, e **o comando recusa fazê-la**. Rodar
`uv run matinal redacao` sem temas não escolhe o tema dominante por você: falha e diz o
que falta.

A recusa é deliberada. A triagem propõe um tema dominante, e a proposta costuma ser
razoável — mas hierarquia de temas é julgamento editorial sobre o que a diretoria
precisa ler primeiro hoje, e isso o modelo não tem como saber. Se o comando aceitasse a
sugestão em silêncio, o plantão em que ninguém leu a triagem seria indistinguível do
plantão em que alguém a leu e concordou.

A interface junta duas coisas que você precisa separar:

**Os números são mecânicos.** `--temas-numeros "1,3,2"` diz quais linhas da tabela de
temas candidatos entram, e em que ordem, o dominante primeiro. O texto de cada tema sai
da própria triagem, sem transcrição. Essa parte é seleção: você escolhe entre o que já
está escrito. No notebook, é a lista `ESCOLHA` da célula do Passo 3.

**A ressalva é o julgamento.** É o que você acrescenta e que a tabela não tem como
conter: um limite temporal, uma atribuição obrigatória, uma direção que o painel
contradiz. Para acrescentá-la, escrever os temas em vez de escolhê-los, com
`--temas "dominante | tema 2"` ou `--temas-arquivo temas.md` — no notebook, somando o
texto à variável `TEMAS` depois de montá-la.

Em 17/08, o mercado vinha de uma queda do dólar e as fontes falavam dela. O painel
daquela manhã, porém, mostrava o câmbio estável na sessão corrente. Nenhuma escolha de
números resolveria isso: os temas candidatos estavam certos, e a ordem também. O que
impediu o comentário de afirmar que o dólar caíra no dia foi uma ressalva escrita à
mão — "as moedas estão estáveis na sessão corrente" — anexada ao marcador. Este é o
formato do julgamento que só você pode dar.

Regra prática: se o painel e as fontes descrevem quadros diferentes, a ressalva é
obrigatória. Os alertas de divergência com o painel, na triagem, existem para você
notar isso.

## Os pontos sob julgamento do autor

A revisão devolve três coisas, e elas não têm o mesmo peso:

| O que vem | O que fazer |
|---|---|
| Correções obrigatórias | Aplicar. São falha de conformidade com o guia ou afirmação sem suporte nas fontes |
| Sugestões editoriais | Opcionais, no formato antes → depois. Aceitar ou descartar, sem justificar |
| Pontos sob julgamento do autor | Decidir, um a um. É aqui que o processo devolve a caneta |

O terceiro grupo fecha o bloco de auditoria da revisão. São os casos em que o revisor
identificou algo real e não tem como resolver sozinho: uma afirmação `PARCIALMENTE
SUPORTADA` que talvez seja a leitura certa das fontes, um corte que ganharia espaço mas
perderia nuance, uma atribuição que a fonte faz com hedge e o texto reproduz sem ele.

Como decidi-los:

- **Suporte nas fontes vence estilo.** Afirmação marcada como `NÃO LOCALIZADA` ou
  `CONTRADITA` sai ou ganha atribuição explícita. Não há julgamento a fazer aqui — isso
  já é correção obrigatória.
- **`PARCIALMENTE SUPORTADA` é onde você decide de verdade.** Ou você reconhece a
  afirmação como leitura sua, e ela ganha a ressalva que a torna honesta, ou ela sai.
  O que não se faz é mantê-la como se a fonte a tivesse dito.
- **Contra o painel, o painel ganha.** Ele é o estado de mercado que o e-mail carrega
  como imagem. Texto e imagem discordando é o erro mais visível que este processo pode
  cometer.
- **Contra o relógio, o relógio ganha.** Dado ainda não divulgado não entra, por mais
  que a fonte o antecipe. `AINDA NÃO DIVULGADO` no calendário em texto é a palavra
  final, nunca o campo `ATUAL` da imagem.
- **Na dúvida com pressa, corte.** Perto das 9h, um marcador a menos é sempre mais
  barato que um marcador que precisa de retratação.

## A divergência do `conferir`

O Passo 8 compara marcador a marcador o `.docx` com o `.md` e mostra os trechos que
diferem. Toda edição que você fez no Word aparece ali. A pergunta é sempre a mesma:
**eu fiz isso de propósito?**

**Intencional** — você corrigiu uma vírgula, trocou uma palavra, ajustou um número
depois de reler a fonte. O `.docx` está certo e o `.md` está velho. Repita a correção
no `.md`: é ele que fica versionado, e é ele que a triagem de amanhã lê como comentário
do dia anterior. Correção que só existe no Word desaparece do processo no dia seguinte.

**Acidente** — você não reconhece a diferença. Um clique fora do lugar comeu uma
palavra, uma substituição levou junto um trecho vizinho, uma colagem substituiu mais do
que devia. Corrija no `.docx` e rode de novo.

O teste é o reconhecimento, não a plausibilidade. Em 17/08 o `conferir` acusou quatro
palavras faltando, entre elas o `swap` de "mercados de swap" — a frase ficou "mercados
de", e o e-mail saiu assim, porque a conferência rodou depois do envio. Nenhuma das
quatro tinha sido tirada de propósito, e nenhuma delas parecia estranha na lista de
divergências até alguém olhar a frase inteira.

Por isso o Passo 8 existe separado do Passo 9, com a mesma comparação: é o último
momento em que a resposta "foi acidente" ainda tem conserto.

## Quando é legítimo forçar o arquivamento

`uv run matinal enviado` é o único passo que bloqueia, e recusa por três motivos.
`--forcar` é rombudo: ele passa pelos três de uma vez, e não há como contornar só um.
Antes de usá-lo, saiba qual dos três você está contornando.

**Fora da janela de 7h–9h.** Legítimo quando o envio ocorreu mesmo e o plantão atrasou
— o e-mail saiu às 9h05 e você está arquivando o que foi enviado. Ilegítimo em ensaio:
se você está reprocessando um dia antigo ou testando a montagem à tarde, o
arquivamento gravaria como enviado algo que não foi.

**`.docx` e `.md` divergem.** Legítimo quando você entendeu a divergência e decidiu que
o `.md` está certo como está — caso raro, e que na prática significa que o e-mail saiu
com o texto do `.md`. Ilegítimo como atalho para não olhar: a comparação está
protegendo o insumo de amanhã, e um `.md` que não é o texto enviado vira contradição
inventada na triagem do dia seguinte.

**Já existe comentário arquivado para a data.** Legítimo quando o primeiro
arquivamento foi errado e você está substituindo conscientemente. Ilegítimo em qualquer
outro caso: rearquivar por engano apaga em silêncio o comentário de um dia já enviado,
e não há aviso depois.

Regra: se você não consegue dizer em voz alta qual das três recusas está contornando e
por quê, não use `--forcar`. Corrija a causa.
