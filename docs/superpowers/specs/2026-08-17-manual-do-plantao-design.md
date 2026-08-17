# Manual do plantão: um documento por leitor, com a sincronia presa por teste

Data: 17/08/2026

## Contexto

O autor quer um wiki descrevendo o passo a passo do fluxo, para que um gestor novo saiba
como agir, e quer que ele seja atualizado sempre que uma mudança no código afetar o
fluxo.

A segunda metade é a mesma exigência que atravessou o dia inteiro, e que já falhou em
quatro frentes deste repositório: a separação `daily`/`comentario_matinal`, as convenções
duplicadas no `project_instructions.md`, o `.docx` contra o `.md`, e a segunda lista de
ativos. Em todas, o que faltou foi mecanismo, não intenção.

E há uma dificuldade específica: **o README já é o runbook**. São 282 das suas 476 linhas.
Um documento novo "descrevendo o passo a passo" seria uma segunda cópia dessas 282 linhas
no dia em que nascesse.

## Decisão

Não se cria um segundo documento sobre o mesmo assunto. Separa-se o README por leitor:

- **`docs/plantao/`** — o manual de quem vai rodar o plantão. Recebe o runbook e a
  instalação, que saem do README, e ganha três páginas que não existem hoje.
- **`README.md`** — a referência de quem mexe no código. Fica com o que o repositório é,
  a estrutura, e as notas de projeto. Cai para perto de 150 linhas.

Uma fonte para cada assunto. O que estava em um lugar continua em um lugar; muda qual.

A cópia no Wiki do GitHub é derivada, não fonte, e diz isso em cada página.

## As páginas

```
docs/plantao/
  README.md              índice — o que o GitHub abre ao navegar a pasta
  01-primeiro-dia.md     orientação: o produto, o leitor, o tempo, as duas formas
  02-instalacao.md       uma vez só — sai do README
  03-runbook.md          os nove passos — sai do README
  04-decisoes.md         o que é do autor decidir, e por quê
  05-quando-da-errado.md os modos de falha, o sintoma exato, a saída
```

### O que muda de lugar

Mapa exato, para que a mudança não seja um exercício de julgamento:

| README hoje | Destino |
|---|---|
| `## Estrutura` | fica |
| `## Configuração inicial (uma vez)` | `02-instalacao.md` |
| `### As etapas de IA` | dividida: `--web` e `--modelo` vão para `03-runbook.md`; a troca de backend por `modelo.py` fica no README |
| `### A janela e o dry run` | `01-primeiro-dia.md` |
| `### O Project do Claude` | `02-instalacao.md`, como caminho alternativo |
| `### Os exemplos` | fica — trata de promover exemplo ao guia, que é manutenção |
| `## Runbook do plantão` e os nove passos | `03-runbook.md` |
| `### As duas formas de rodar` | `01-primeiro-dia.md` |
| `### Referência de fusos` | `03-runbook.md`, junto do passo que a usa |
| `## Notas` e `### A coluna ATUAL` | ficam |

O README ganha, no topo, um link grande para `docs/plantao/`. A sua seção de instalação
vira duas linhas apontando para lá: quem clona para desenvolver precisa do mesmo
`uv sync` que o plantonista, e duas instruções de instalação divergiriam.

### O que é conteúdo novo

Três páginas, e é nelas que está o valor — nenhuma existe hoje.

**`01-primeiro-dia.md`.** O que você produz, quem lê, quanto tempo leva, o que é seu
decidir e o que o comando decide. As duas formas de rodar e como escolher. A janela e o
dry run.

**`04-decisoes.md`.** Recolhe o que hoje está espalhado ou não está escrito:

- a escolha de temas entre a triagem e a redação — o comando **recusa** fazê-la, e o
  porquê dessa recusa é a coisa mais importante do processo. A página precisa distinguir
  duas coisas que a interface junta: os **números** dizem quais temas entram, e essa
  parte é mecânica; a **ressalva dentro do marcador** é o que o autor acrescenta, e é
  onde o julgamento dele de fato entra. Em 17/08 foi uma ressalva assim que impediu o
  comentário de afirmar que o dólar caíra na sessão quando o painel mostrava o câmbio
  estável — e nenhuma escolha de números teria produzido aquilo;
- os "pontos sob julgamento do autor" que a revisão devolve, e como decidi-los;
- quando uma divergência do `conferir` é intencional e quando é acidente;
- quando `--forcar` é legítimo, e as três recusas que ele contorna de uma vez.

**`05-quando-da-errado.md`.** Cada modo de falha com o **sintoma exato que aparece na
tela** e a saída. O material vem do que a operação de 17/08 expôs:

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

A linha do `conferir` merece o caso concreto de 17/08: quatro palavras sumiram do
documento durante a edição manual, entre elas o `swap` de "mercados de swap", e o e-mail
saiu com a frase quebrada porque a conferência rodou depois do envio.

## O mecanismo de sincronia

`tests/test_documentacao.py`, mesma família do `test_notebook.py`.

O escopo de leitura é `docs/plantao/*.md` **mais o `README.md`**. Os dois são
documentação de leitor humano, e restringir a aferição ao manual deixaria o README livre
para citar um comando que não existe mais — que é justamente o estado em que ele ficaria
depois desta mudança, se ninguém olhasse. O `docs/superpowers/` fica fora: spec e plano
são registro do que se decidiu quando se decidiu, e devem continuar dizendo o que era
verdade na data.

**1. Os comandos.** Todo subcomando de `cli.SUBCOMANDOS` aparece no runbook, e todo
`uv run matinal X` que a documentação mostra existe de fato. É este que torna mecânica a
segunda metade do pedido: comando novo sem documentação, ou documentação citando comando
que sumiu, fica vermelho na mesma suíte de sempre.

**2. Os passos.** Todo passo de `plantao.PASSOS`, exceto os que o manual declare
deliberadamente fora, é alcançável pelo manual.

**3. A janela — e este exige cuidado.** Ela hoje aparece escrita de **quatro** formas
diferentes: "entre 7h00 e 9h00", "7h–9h", "7h00 às 9h00", e `faixa()` devolve
"07h00 a 09h00". Um teste de string literal é impossível e seria errado: obrigaria uma
única redação e endureceria a prosa.

O teste extrai por expressão regular todo par de horas mencionado na documentação e no
`prompts/00_guia_de_estilo.md`, e afere que cada par bate com `janela.ABERTURA.hour` e
`janela.FECHAMENTO.hour`. Muda-se a janela no código, e toda menção em prosa fica
vermelha, qualquer que seja a redação.

O guia entra na aferição porque ele é lido pelo modelo em toda etapa: uma janela errada
ali não confunde o leitor, confunde a triagem.

**4. Os caminhos.** As pastas nomeadas na documentação batem com as constantes de
`config.py`.

**5. O README aponta para o manual.** Simples, e impede que a mudança de lugar deixe o
leitor sem trilha.

## A publicação

Módulo `src/comentario_matinal/wiki.py`, com entrada `publica-wiki` em
`[project.scripts]` ao lado do `matinal` — **fora do `matinal`**. Publicar documentação
não é passo do plantão, e um `matinal wiki` entraria em `SUBCOMANDOS` — onde o teste de
sincronia do notebook passaria a cobrar uma célula para ele, ou uma exceção registrada.
A fronteira de `SUBCOMANDOS` é "os passos do plantão", e vale preservá-la.

O comando monta a cópia no repositório do wiki, uma página por arquivo, e cada uma abre
com:

```markdown
> Gerado a partir de `docs/plantao/NN-nome.md` no commit `abc1234`.
> Não editar aqui — a edição se perde na próxima publicação.
```

**O SHA do commit de origem é o que torna o envelhecimento visível.** Não há como aferir
por teste uma cópia que mora noutro repositório git; então a honestidade fica no próprio
texto, onde o leitor a encontra sem procurar.

O comando empurra para o wiki. **Quem o roda é o autor**, não o assistente: empurrar para
repositório compartilhado é ato dele.

### Um passo manual, uma vez

O GitHub só cria `comentario_matinal.wiki.git` depois que a primeira página nasce pela
interface web. Antes disso o `git ls-remote` responde "Repository not found" — verificado.
Então: abrir a aba Wiki, criar qualquer página, e a partir daí o publicador funciona. O
`02-instalacao.md` registra isso.

## Fora de escopo

- Os quatro itens estacionados do trabalho anterior: `roda_etapa` com 144 linhas; os
  prints diretos ao stderr em `etapas.py`, `documento.py`, `fontes.py` e `modelo.py`; a
  chave simples de `PARAMETROS_FORA_DO_NOTEBOOK`; e a frase inalcançável de
  `ASOF_DIVERGE_DO_PAINEL`.
- **Reescrever o conteúdo que muda de lugar**, além do mínimo para ele fazer sentido no
  destino — cabeçalho, ligação entre seções, referências cruzadas. Mover e reescrever no
  mesmo passo esconde o que mudou, que é a lição que a extração do `plantao.py` acabou de
  cobrar em duas rodadas de correção.
- Qualquer mudança de comportamento no código. As únicas alterações em `src/` são o módulo
  novo de publicação e a entrada em `[project.scripts]`.

## Riscos

| Risco | Mitigação |
|---|---|
| A mudança de lugar perde uma seção pelo caminho | O mapa acima é exaustivo; um teste afere que o README aponta para o manual, e a revisão compara o README de antes com a soma dos destinos |
| O teste da janela endurece a prosa | Ele afere horas, não redação; as quatro formas atuais continuam válidas |
| A cópia no Wiki envelhece | O SHA de origem em cada página; não há como fazer melhor de outro repositório |
| Quem chega pelo README não acha o manual | Link no topo, não no rodapé; e teste aferindo que ele existe |
| O runbook some do README e alguém procura ali | O link no topo e a seção de instalação apontando para o manual |

## Critérios de aceitação

1. `docs/plantao/` tem as seis páginas, e o índice lista todas.
2. Nenhuma seção do README de hoje se perdeu: cada uma está no README ou no manual, e a
   revisão consegue apontar onde.
3. `tests/test_documentacao.py` passa, e cada uma das suas seis aferições foi vista
   vermelha ao ser provocada.
4. Mudar `janela.ABERTURA` para outra hora deixa a suíte vermelha, nomeando os arquivos.
5. `uv run publica-wiki` monta a cópia com a faixa de origem em cada página; o autor a
   empurra.
6. `uv run matinal` e todos os subcomandos seguem se comportando como hoje — 135 testes
   verdes.
