# Redação, bancos e revisão do informe do FOMC por etapas de modelo

**Data:** 16/09/2026
**Produto:** `produtos/informes_eventos`
**Estado:** aprovado em conversa; aguardando revisão da spec escrita

## 1. Problema

O informe do FOMC sai de `src/reports/fomc/notebooks/fomc_analysis.ipynb`: o
notebook baixa os PDFs do Fed, parseia statement e SEP, monta o grid de reação
de mercado e gera o `.docx`. O texto, porém, é manual: resumo em parágrafos,
headlines da Bloomberg e comentários dos bancos vivem na célula de configuração
e são digitados a cada reunião.

Em 17/06/2026 esse texto foi produzido fora do repositório, numa conversa no
claude.ai: o autor subiu statement, SEP e notícias da Bloomberg; o modelo
escreveu cinco parágrafos para a Diretoria, reescreveu os últimos depois da
coletiva e, com a versão final, checou a coerência entre texto, tabela do SEP e
números dos gráficos, apontando dois juros que não batiam com o painel.

O objetivo é trazer esse trabalho para dentro do produto, por código, sem
mudar quem decide: o autor continua escolhendo o que entra e assinando o
documento.

## 2. Alcance

Entra:

- Resumo em parágrafos, em dois momentos: após a decisão e após a coletiva.
- Comentário por banco a partir de research em PDF.
- Revisão de coerência do conjunto antes de gerar o Word.
- Headlines lidos de arquivo, com marcação mecânica de destaque.
- Itálico e negrito inline no resumo do Word.

Fica de fora, de propósito: seleção ou reescrita de headlines pelo modelo, CLI,
envio por e-mail, o informe do payroll, e qualquer mudança no comentário
matinal.

## 3. Decisões que orientam o desenho

- **O backend do modelo é uma cópia, não um import.** A regra da raiz diz que
  mudança num produto não mexe noutro. O informes_eventos ganha
  `src/reports/_modelo.py`, cópia enxuta do `modelo.py` do matinal, seguindo o
  precedente de `_bloomberg.py` e `_style.py`, que são cópias do py-bcb. Um
  teste de independência garante que nada aqui importa `comentario_matinal`.
- **Os prompts são a fonte de verdade editorial.** Como no matinal, mudar como
  o texto lê é editar o guia de estilo; o prompt da etapa muda só quando a
  mecânica da etapa muda; nenhuma decisão de estilo fica fixa no Python.
- **O sigilo continua valendo para o agente na conversa.** Quem lê o statement
  do dia e o research dos bancos é o subprocesso da etapa, com as fontes
  injetadas na mensagem. As regras de `AGENTS.md` sobre `input/` e `output/`
  ficam intactas.
- **Nada roda sozinho.** Cada etapa é uma célula que o autor executa. A ordem
  entre etapas é sugerida pelo notebook, não imposta pelo código, exceto onde
  uma etapa depende do arquivo de outra.
- **Autenticação pela sessão do Claude Code.** O subprocesso roda
  `claude -p --safe-mode`, sem ferramentas, com `ANTHROPIC_API_KEY` retirada
  do ambiente. Rodar por chave de API é escrever outro backend.
- **Identificadores em inglês, prosa em português**, como manda o `AGENTS.md`
  do produto. Os prompts, o guia e as saídas são em português.

## 4. Arquivos

```text
produtos/informes_eventos/
  prompts/
    00_guia_de_estilo.md            guia editorial do informe do FOMC
    01_resumo.md                    etapa: resumo (decisão e pós-coletiva)
    02_bancos.md                    etapa: comentário por banco
    03_revisao.md                   etapa: revisão de coerência
  src/reports/
    _modelo.py                      backend do modelo (cópia do matinal)
    fomc/core/drafting.py           etapas, montagem de mensagens, leitura de saídas
    fomc/core/word_report.py        itálico/negrito inline no resumo (alteração)
    fomc/notebooks/fomc_analysis.ipynb   células novas; campos de texto saem
  input/fomc/<AAAAMMDD>/            pasta do dia, fora do git
    headlines.txt                   Bloomberg, um headline por linha
    coletiva.txt                    headlines da coletiva, mesmo formato
    bancos/<Nome do banco>.pdf      research; o nome do arquivo é o nome do banco
  output/reports/fomc/<AAAAMMDD>/   saídas das etapas, fora do git
    resumo_decisao.md
    resumo_coletiva.md
    bancos.md
    revisao.md
  tests/test_drafting.py            testes das etapas, com dublê do modelo
  tests/test_independence.py        ganha a proibição de importar o matinal
```

`input/` e `output/` já estão no `.gitignore` do produto sem âncora, então as
pastas novas nascem fora do git. O `.docx` e o grid continuam em
`output/reports/fomc/`, ao lado da pasta do dia.

### 4.1 Formato dos arquivos de entrada

`headlines.txt` e `coletiva.txt`: UTF-8, um headline por linha, linhas vazias
ignoradas. Linha que começa com `***` é destaque; o prefixo é removido e o
headline entra em negrito no Word. Qualquer outro prefixo de asteriscos é
removido sem marcar destaque. O horário do headline, quando colado junto, fica
no texto: o modelo o vê e o Word o imprime como está.

`bancos/`: só `*.pdf`. O nome do banco é o nome do arquivo sem extensão, com
sublinhados trocados por espaço. Outros arquivos na pasta são listados como
ignorados no aviso da etapa.

### 4.2 Formato dos arquivos de saída

Cada etapa grava a resposta inteira do modelo, auditoria incluída. O que o
notebook consome é o **último bloco cercado** da resposta, delimitado por
```` ``` ````. Na etapa de bancos o bloco traz seções `## Nome do banco`, uma por
PDF. Nas demais, o bloco é o texto em markdown: parágrafos separados por linha
em branco, `*itálico*` para termos em inglês, `**negrito**` raro.

## 5. O backend: `src/reports/_modelo.py`

Cópia do `modelo.py` do matinal com estas diferenças e nenhuma outra:

- Variável de ambiente `INFORMES_EVENTOS_BACKEND`, padrão `claude-code`.
- Prompt de sistema com o nome do produto: assistente da Mesa de Investimentos
  do DEPIN/DIRIN, execução automatizada sem ninguém do outro lado; proibido
  perguntar, proibido preâmbulo; entrada obrigatória ausente abre a resposta
  com `ENTRADA OBRIGATÓRIA AUSENTE:`; seguir o guia e o prompt da etapa.
- Identificadores em inglês: `Backend`, `ClaudeCode`, `ModelError`, `run`,
  `active_backend`, `BACKENDS`, `BLOCKED_TOOLS`, `TIMEOUT = 900`.
- Sem a opção `web`: nenhuma etapa do informe consulta a internet.

Mantido do matinal: mensagem pela entrada padrão, `--safe-mode`,
`--disallowed-tools` com todas as ferramentas, `--model` só se pedido,
`ANTHROPIC_API_KEY` removida do ambiente, erro com o fim do stdout quando a CLI
sai com código diferente de zero, resposta vazia é erro.

## 6. As etapas: `src/reports/fomc/core/drafting.py`

### 6.1 Insumos

```python
@dataclass
class MeetingInputs:
    meeting_date: str                 # AAAAMMDD
    statement_text: str               # texto do PDF do statement
    statement: dict                   # saída de parse_statement
    is_sep: bool
    sep_medians: pd.DataFrame | None  # medianas atuais
    sep_prior: pd.DataFrame | None    # medianas anteriores
    prior_label: str | None           # ex. "June projection"
    headlines: list[Headline]         # de headlines.txt
    market: MarketSnapshot | None     # de fetch_market_reaction
```

`Headline` é `(text: str, bold: bool)`. `MarketSnapshot` tem, para cada um dos
nove painéis de `MARKET_REACTION_PANELS`, o nível imediatamente anterior à
decisão, o último nível disponível e a variação, formatados com o mesmo
formato do painel; e o horário do último dado, em Brasília. A função que o
calcula, `market_snapshot(market_data, decision_time)`, é pura e testável com
um intraday sintético.

Funções de leitura da pasta do dia:

- `day_folder(meeting_date) -> Path`: `<raiz>/input/fomc/<AAAAMMDD>`.
- `read_headlines(path) -> list[Headline]`: aplica a regra do `***`.
- `read_bank_pdfs(folder) -> tuple[list[BankSource], list[str]]`: texto por
  PDF via pdfplumber, mais a lista de ignorados e vazios.
- `output_folder(meeting_date) -> Path`: `<raiz>/output/reports/fomc/<AAAAMMDD>`,
  criada se não existir.

### 6.2 Montagem da mensagem

Toda etapa monta a mensagem na mesma ordem: guia de estilo, prompt da etapa,
depois as entradas em blocos rotulados em maiúsculas, um por insumo:

```text
=== STATEMENT ===
...
=== DECISÃO (parse) ===
decisão: manutenção; faixa: 3,50%–3,75%; unânime: não; dissidentes: ...
=== SEP: MEDIANAS ATUAIS vs ANTERIORES (June projection) ===
| Variável | 2026 | 2027 | 2028 | 2029 | Longer run |
| Change in real GDP | 1,8 (1,4) | ...
=== HEADLINES BLOOMBERG ===
*** ...
=== REAÇÃO DE MERCADO (até 15:42 BRT) ===
UST 2 Anos: 4,201% (na decisão 4,070%; +13,1 p.b.)
...
```

Bloco de insumo ausente ou vazio não é omitido em silêncio: entra como
`=== NOME === (ausente)` para o prompt poder reclamar. A tabela do SEP entra
com vírgula decimal, como o texto deve sair. Reunião sem SEP não tem o bloco
do SEP, e o prompt manda pular o parágrafo das projeções.

### 6.3 Resumo: `draft_summary(inputs, *, stage, previous=None)`

- `stage="decision"`: mensagem com todos os insumos; grava
  `resumo_decisao.md`; devolve o texto do bloco cercado.
- `stage="presser"`: exige `previous` (o texto do resumo da decisão) e
  `coletiva.txt`; a mensagem traz o resumo anterior como bloco `RESUMO DA
  DECISÃO` e os headlines da coletiva como `HEADLINES DA COLETIVA`, além da
  reação de mercado atualizada; o prompt manda manter os parágrafos de
  decisão, statement e SEP e reescrever só o que a coletiva e o fechamento
  mudam; grava `resumo_coletiva.md`.
- O prompt da etapa (`01_resumo.md`) pede quatro a seis parágrafos breves, os
  números só dos blocos recebidos, atribuição explícita de inferência de
  fonte, e termina com o bloco cercado.

### 6.4 Bancos: `draft_bank_comments(inputs, folder)`

Um bloco `=== RESEARCH: Nome do banco ===` por PDF. O prompt (`02_bancos.md`)
pede um parágrafo por banco, em português, atribuído pelo nome, só com o que
aquele research diz, sem misturar casas nem completar com o statement. O bloco
cercado traz `## Nome do banco` seguido do parágrafo. A função grava
`bancos.md` e devolve `dict[str, str]` na ordem dos arquivos. Bancos cujo PDF
não rendeu texto ficam fora do dicionário e na lista de avisos.

### 6.5 Revisão: `review_report(inputs, summary, bank_comments)`

Mensagem com o resumo escolhido, os comentários dos bancos, e os mesmos
insumos factuais da redação. O prompt (`03_revisao.md`) manda, nesta ordem:

1. **Checagem factual**, afirmação por afirmação, com veredito `SUPORTADA`,
   `PARCIALMENTE SUPORTADA`, `NÃO LOCALIZADA` ou `CONTRADITA` e o bloco que
   sustenta ou contradiz. Números do texto contra a tabela do SEP, o parse do
   statement e a reação de mercado; votação e dissidências; direção da leitura
   (hawkish, dovish, neutra) contra o que o grid mostra.
2. **Conformidade com o guia**: vírgula decimal, itálico nos termos em inglês,
   extensão, seções coerentes com haver ou não SEP, nenhuma opinião da divisão.
3. **Sugestões editoriais**, separadas das anteriores.
4. Bloco cercado final com o texto corrigido, só com as correções de fato e de
   conformidade; sugestões editoriais não são aplicadas.

Grava `revisao.md` e devolve o texto corrigido. Aceitar ou não é do autor.

### 6.6 Execução e erros

`run_stage(name, message, destination) -> str` chama o backend, verifica a
resposta e grava. É erro, com `DraftingError` e sem gravar nada:

- backend ausente, tempo esgotado, código de saída diferente de zero, resposta
  vazia (vindos de `ModelError`);
- resposta começando por `ENTRADA OBRIGATÓRIA AUSENTE`;
- resposta sem bloco cercado.

Antes de chamar o modelo, é erro: pasta do dia inexistente; `headlines.txt`
ausente ou vazio na etapa de resumo; `coletiva.txt` ausente no momento
"presser"; `previous` vazio no momento "presser"; pasta `bancos/` sem PDF na
etapa de bancos. A mensagem do erro diz o caminho esperado.

Reexecutar uma etapa sobrescreve o `.md` dela. Não há histórico de versões
dentro do produto: o arquivo anterior é substituído.

## 7. Notebook

A célula de configuração perde `SUMMARY_TEXT`, `HEADLINES`,
`PRESSER_HEADLINES`, `BANK_COMMENTS` e `MESA_COMMENT`. Fica com a data, os
horários, os caminhos dos screenshots e `SUMMARY_SOURCE`, que escolhe qual
resumo vai ao Word: `"revisao"`, `"coletiva"` ou `"decisao"`, com padrão
`"auto"`, que pega o mais avançado que existir na pasta de saída, nessa ordem.

Células novas, depois do SEP e antes do preview, cada uma independente:

1. **Insumos do dia**: monta `MeetingInputs` a partir do que as células
   anteriores já produziram e da pasta do dia; imprime o que achou e o que
   falta, sem chamar o modelo.
2. **Resumo da decisão**: `draft_summary(..., stage="decision")`; mostra a
   resposta inteira e, destacado, o bloco final.
3. **Resumo pós-coletiva**: só roda se `coletiva.txt` existir; usa o texto do
   resumo da decisão gravado.
4. **Bancos**: só roda se `bancos/` tiver PDF.
5. **Revisão**: roda sobre o resumo escolhido por `SUMMARY_SOURCE` e os
   comentários dos bancos, se houver; mostra a checagem factual.

O preview passa a dizer de qual arquivo vem o resumo, com contagem de
palavras, quantos headlines e quantos em destaque, e os bancos por nome. A
célula de geração lê o resumo e os bancos dos arquivos e chama
`generate_fomc_report` como hoje, com `presser_headlines` vindo de
`coletiva.txt` quando existir.

`MESA_COMMENT` deixa de existir no notebook; o parâmetro `mesa_comment` de
`generate_fomc_report` continua aceito, com padrão vazio.

## 8. Word

`_add_summary` passa a usar a mesma rotina de marcação inline dos comentários
dos bancos, estendida para `*itálico*` além de `**negrito**`. A rotina vive
numa função só, `_add_marked_text(paragraph, text, size)`, usada pelos dois. O
negrito é testado primeiro, depois o itálico, para `**x**` não virar dois
itálicos. Nenhuma outra mudança de layout.

## 9. Guia de estilo: `prompts/00_guia_de_estilo.md`

Primeira versão escrita a partir do que se fixou em junho; o autor revisa e o
guia passa a mandar. Conteúdo mínimo, numerado para os prompts citarem:

1. **Leitor e registro.** Diretoria do BCB, economistas experientes. Formal,
   impessoal, sem explicar conceito macro, sem gíria de mesa. Nenhuma opinião,
   projeção ou recomendação da divisão.
2. **Forma.** Prosa corrida, quatro a seis parágrafos breves, sem marcadores.
   Ordem canônica: decisão e votação; statement; SEP quando houver; coletiva
   quando houver; reação de mercado e leitura.
3. **Números.** Só dos insumos recebidos, nunca de memória. Vírgula decimal.
   Pontos-base grafados "p.b.". Mediana do SEP com uma casa decimal, como o
   Fed publica; o valor cheio em 1/8 pode ir entre parênteses.
4. **Léxico.** Termos em inglês preservados e em itálico: *hawkish*,
   *dovish*, *dots*, *forward guidance*, *hold*, *regime change*. "Fed Funds"
   com s. Nomes de participantes como no statement.
5. **Atribuição.** Inferência de veículo é atribuída ("a Bloomberg atribui");
   fato do statement e da tabela dispensam atribuição. Fala de participante
   leva cargo e ocasião.
6. **Leitura.** Um fechamento explícito: a decisão foi lida como neutra,
   *hawkish* ou *dovish* frente ao que se esperava, e a curva reagiu como.
   Sem contradizer o grid.
7. **Coletiva.** Ao reescrever, manter o que é anterior a ela e mudar só o que
   ela muda; quando um fato deixa de ser inferência e vira confirmação, dizer.

## 10. Testes

Em `tests/test_drafting.py`, sem rede, sem Bloomberg e sem `claude`:

- Dublê de backend registrado em `BACKENDS` por `monkeypatch` da variável de
  ambiente, devolvendo resposta fixa e gravando a mensagem recebida para
  inspeção.
- `read_headlines`: `***` vira destaque e some do texto; linhas vazias
  ignoradas; asterisco simples removido sem destaque.
- `market_snapshot`: com intraday sintético, nível na decisão, último e
  variação por painel, com o formato de cada painel; horário do último dado.
- Montagem da mensagem: ordem guia → prompt → blocos; blocos ausentes
  marcados `(ausente)`; reunião sem SEP não tem bloco do SEP; momento
  "presser" traz o resumo anterior e a coletiva.
- Extração do último bloco cercado; seções `## Banco` viram dicionário na
  ordem; bloco ausente e `ENTRADA OBRIGATÓRIA AUSENTE` levantam
  `DraftingError` e não gravam arquivo.
- Erros antes do modelo: pasta do dia, `headlines.txt`, `coletiva.txt`,
  `bancos/` vazia.
- `_add_marked_text`: `*x*` vira itálico, `**x**` negrito, texto sem marcação
  intacto.
- `test_independence.py`: nenhum arquivo de `src/` importa `comentario_matinal`.
- `TestProjectRootAnchors`: `day_folder` e `output_folder` nascem na raiz do
  produto; a pasta `prompts/` existe e tem os quatro arquivos.

O portão continua `uv run pytest`, mais `ruff check` e `ruff format --check`.

## 11. Fluxo de um dia de FOMC, depois da mudança

1. Antes da decisão: pasta `input/fomc/<data>/` criada; dot plot salvo no
   OneDrive como hoje.
2. Decisão: rodar o notebook até o SEP; colar os headlines em
   `headlines.txt`; rodar insumos e resumo da decisão; ler.
3. Coletiva: colar em `coletiva.txt`; rodar o resumo pós-coletiva; ler.
4. Research dos bancos em `bancos/`; rodar a etapa de bancos.
5. Rodar a revisão; decidir o que aceitar; ajustar `SUMMARY_SOURCE` se não
   quiser o padrão.
6. Preview, gerar o Word, revisão humana pelo *four eyes*, envio.

## 12. Questões que a implementação decide sozinha

- Nome exato dos prompts de etapa e a redação deles: primeira versão minha,
  revisada pelo autor junto com o guia.
- Se o `MarketSnapshot` usa o último dado ou o dado de fechamento quando o
  grid já passou das 17h: usa o último disponível e diz o horário.
