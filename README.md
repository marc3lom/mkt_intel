# comentario_matinal

> **Vai rodar o plantão?** O manual é [`docs/plantao/`](docs/plantao/) — instalação,
> os nove passos, o que é seu decidir e o que fazer quando algo quebra. Este arquivo
> descreve o repositório para quem mexe no código.

Prompts, guia de estilo e utilitários do Comentário Matinal da Mesa de Investimentos
(DEPIN/DIRIN — Banco Central do Brasil).

O comentário é produzido e enviado diariamente entre 7h00 e 9h00, no fuso da máquina do
plantão — nesta mesa, Brasília. A autoria roda entre os gestores da divisão; o processo
não deve variar com o autor nem com o horário em que o plantão começa. Este repositório
existe para garantir isso.

Fora dessa janela o comando entende que a execução é ensaio e carimba as saídas
(ver [A janela e o dry run](docs/plantao/01-primeiro-dia.md#a-janela-e-o-dry-run)).

---

## Estrutura

```
comentario_matinal/
├── README.md                   este arquivo — o repositório para quem mexe no código
├── docs/
│   └── plantao/                o manual de quem roda o plantão
│       ├── README.md           índice
│       ├── 01-primeiro-dia.md  o produto, o tempo, as duas formas, a janela
│       ├── 02-instalacao.md    uma vez por máquina
│       ├── 03-runbook.md       os nove passos
│       ├── 04-decisoes.md      o que é do autor decidir
│       └── 05-quando-da-errado.md  os modos de falha e a saída de cada um
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

O formato de `arquivo/` é Markdown por decisão deliberada: o arquivo precisa ser
pesquisável por texto e legível pelo comando. `arquivo/` guarda apenas o que o processo
produz, a partir da primeira rodada em produção. Os comentários antigos em `.docx`, sob
a convenção `AAAA/AAAAMM/`, foram retirados: serviam de contexto e não casavam com o
padrão que o comando lê.

---

## As duas fachadas, e o que as prende

O plantão roda de duas formas — `uv run matinal`, no terminal, e
`notebooks/plantao.ipynb`. Nenhuma das duas o implementa: as duas são fachadas sobre
`src/comentario_matinal/plantao.py` e chamam as mesmas funções, então não podem
divergir no que fazem. O que poderia divergir é a **sequência** — ela existe duas
vezes, no argparse e nas células —, e é isso que `tests/test_notebook.py` prende:
passo novo no núcleo, subcomando novo no terminal ou célula fora da ordem de
`plantao.PASSOS` derrubam o teste até que o notebook seja atualizado junto.

**Parâmetro novo num passo também.** Ou uma célula o exercita, ou ele entra na lista de
exceções do teste com o motivo escrito ao lado. Não ter contrapartida no notebook é
decisão legítima — `--asof`, `--anterior` e `--modelo` são conserto, ensaio e
investigação, e moram no terminal —, mas precisa ser decisão, e não esquecimento.

O núcleo também não escreve instrução de terminal. Ele diz o que falta — "falta a
triagem de 20260817." — e nomeia a falta como dado; a frase que ensina a supri-la é de
cada fachada, porque "rodar `uv run matinal triagem`" é conselho certo no terminal e
errado numa célula, onde não há linha de comando na tela que o autor está olhando.

---

## Instalação

Quem clona para desenvolver precisa exatamente do mesmo que o plantonista: está em
[`docs/plantao/02-instalacao.md`](docs/plantao/02-instalacao.md). Duas instruções de
instalação divergiriam, e a que envelhecesse seria justamente esta.

## As etapas de IA

As três etapas rodam pelo Claude Code em modo não interativo, e exigem o `claude` no
PATH. A chamada ao modelo está isolada em `modelo.py`, atrás de uma função única: trocar
para Copilot CLI, Azure OpenAI ou chamada direta à API é escrever outra classe e apontar
a variável `COMENTARIO_MATINAL_BACKEND`, sem tocar no fluxo das etapas.

Os PDFs viram texto antes de chegar ao modelo, para que o insumo seja o mesmo em
qualquer backend — um lê PDF anexo, outro não.

## Os exemplos

`exemplos/aprovados/` e `exemplos/rejeitados/` são material de trabalho humano, **não
insumo do comando**: nada em `src/` lê essas pastas. Elas guardam os casos brutos —
comentários que a chefia destacou, trechos rejeitados com o motivo no cabeçalho — até
que alguém os transforme em exemplo anotado na seção 12 do guia de estilo. É a seção
12 que chega ao modelo, porque o guia inteiro vai injetado em toda etapa.

Um comentário arquivado em `exemplos/` e nunca promovido ao guia não influencia saída
nenhuma.

---

## Notas

- O bloco de auditoria nunca vai no e-mail.
- Os PDFs das fontes não entram no repositório (ver `.gitignore`). A regra de uso da
  Bloomberg que sustenta isso está no
  [Passo 1](docs/plantao/03-runbook.md#passo-1--coleta-t0), com quem manuseia os
  arquivos.
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
