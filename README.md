# comentario_matinal

Prompts, guia de estilo e utilitários do Comentário Matinal da Mesa de Investimentos
(DEPIN/DIRIN — Banco Central do Brasil).

O comentário é produzido diariamente pela manhã, com envio pretendido até 8h00 de
Brasília. A autoria roda entre os gestores da divisão; o processo não deve variar com o
autor nem com o horário em que o plantão começa. Este repositório existe para garantir
isso.

---

## Estrutura

```
comentario_matinal/
├── README.md                   este arquivo — runbook do plantão
├── prompts/
│   ├── 00_guia_de_estilo.md    fonte única de convenções
│   ├── 01_triagem.md           etapa 1 — seleção de temas
│   ├── 02_redacao.md           etapa 2 — redação
│   ├── 03_revisao.md           etapa 3 — revisão
│   └── project_instructions.md texto a colar no Project do Claude
├── exemplos/
│   ├── aprovados/              comentários exemplares (few-shot)
│   └── rejeitados/             trechos rejeitados, com o motivo no cabeçalho
├── arquivo/
│   └── AAAA/MM/AAAAMMDD.md     comentários enviados
├── scripts/
│   └── gera_painel.py          painel e calendário em texto, via Bloomberg
└── config/
    └── painel.toml             tickers do painel e releases do calendário
```

---

## Configuração inicial (uma vez)

1. Criar um Project no Claude chamado "Comentário Matinal — DEPIN/DIRIN".
2. Colar `prompts/project_instructions.md` nas instruções do projeto.
3. Anexar ao conhecimento do projeto os quatro arquivos de `prompts/`.
4. Instalar as dependências do script: `uv sync` (requer terminal Bloomberg ativo).

Sempre que uma convenção mudar, editar `prompts/00_guia_de_estilo.md`, comitar, e
substituir o arquivo no conhecimento do projeto. Não editar convenções nos prompts de
etapa — eles apenas referenciam o guia.

---

## Runbook do plantão

O roteiro é contado em tempo relativo a partir do término da coleta (T0), não em horário
de relógio. O plantão pode começar às 7h30 ou às 7h50; a sequência e a folga são as
mesmas. Ciclo completo em torno de vinte e cinco minutos.

### Passo 1 — Coleta (T0)

Reunir as fontes do dia: wraps da Bloomberg, First Word, e-mails de sell-side, matérias
do Financial Times ou do Wall Street Journal. Salvar em PDF.

Gerar painel e calendário em texto:

```
uv run scripts/gera_painel.py --saida painel.txt
```

O script carimba o horário de execução no cabeçalho do `painel.txt`. Se o painel for
gerado bem antes da redação, regerá-lo — direção de ativo muda, e o painel é a
referência de coerência do texto.

**Anote o horário em que a coleta terminou. Ele é o horário de redação do dia** e
acompanha o trabalho até a revisão.

### Passo 2 — Triagem (T0 + 5 min)

Abrir uma conversa nova no Project. Anexar os PDFs e o `painel.txt`. Escrever:

```
etapa 1
horário de redação: DD/MM/AAAA, HHhMM de Brasília
```

Informar o horário efetivo, não o horário nominal do plantão. É contra ele que a triagem
classifica cada indicador como divulgado ou pendente.

A saída é a tabela de temas candidatos, o tema dominante proposto, os alertas e a
sugestão de corte.

### Passo 3 — Decisão editorial (T0 + 10 min)

**Este é o único passo que não se delega.** Ler a tabela, conferir os alertas —
sobretudo os de dado ainda não divulgado e os de divergência com o painel — e definir o
tema dominante e os dois ou três temas seguintes, em ordem.

Não pular esta etapa em dia corrido. É onde se evita excesso de temas e dado antecipado.

### Passo 4 — Redação (T0 + 15 min)

Na mesma conversa:

```
etapa 2
tema dominante: [ ]
tema 2: [ ]
tema 3: [ ]
riscos monitorados: [ ] (ou "suprimir")
```

Conferir o bloco de auditoria: contagem total dentro de 350–500, orçamento por marcador,
mapeamento marcador → fonte, ressalvas.

### Passo 5 — Passagem ao revisor

**Regra de folga: a passagem ocorre com pelo menos dez minutos de antecedência sobre o
horário de envio pretendido.** Se a coleta atrasou e essa folga não existe mais, avisar o
revisor antes de mandar, para que ele priorize as correções obrigatórias e trate as
sugestões como descartáveis.

Enviar ao segundo analista: texto, PDFs das fontes, `painel.txt`, bloco de auditoria e
**o horário de redação**.

### Passo 6 — Revisão

O revisor abre conversa nova no Project, anexa tudo e escreve:

```
etapa 3
horário de redação: DD/MM/AAAA, HHhMM de Brasília
```

O horário informado é o do autor, não o do revisor. Um comentário redigido às 7h35 e
outro às 7h55 podem descrever quadros diferentes de forma legítima — releases europeus e
britânicos saem entre 3h e 6h de Nova York, dentro da janela de redação. O revisor precisa
saber contra qual momento está conferindo.

Tratar primeiro as correções obrigatórias; as sugestões são opcionais e ficam a critério
do autor. Enviar o e-mail com o painel de gráficos e o calendário econômico inseridos pela
equipe.

### Referência de fusos

| Brasília | Nova York | Observação                                              |
|----------|-----------|---------------------------------------------------------|
| 07h00    | 06h00     | Releases europeus e britânicos já divulgados             |
| 08h00    | 07h00     | Limite usual de envio                                    |
| 09h30    | 08h30     | Maioria dos releases americanos — sempre após a redação   |

Horários de Nova York consideram o horário de verão americano. Fora dele, subtrair uma
hora adicional da conversão.

### Após o envio

Salvar o texto final em `arquivo/AAAA/MM/AAAAMMDD.md`. Comentários que a chefia
destacar como exemplares vão para `exemplos/aprovados/` e alimentam os exemplos
few-shot do guia de estilo.

---

## Notas

- O bloco de auditoria nunca vai no e-mail.
- Os PDFs da Bloomberg trazem marcação de uso exclusivo e vedação à redistribuição. O
  uso do material em serviço externo de IA deve estar coberto pela governança de IA e
  pelos contratos da instituição antes de o processo virar rotina de divisão.
- Os tickers em `config/painel.toml` devem ser conferidos contra o terminal antes do
  primeiro uso em produção.
