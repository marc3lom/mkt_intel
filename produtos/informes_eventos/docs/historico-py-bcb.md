# Histórico dos informes no py-bcb

> Trecho de `.techdoc/doc-py-bcb.md` do py-bcb, trazido na migração de setembro de 2026.
> Os caminhos citados (`src/reports/…`) são relativos a esta pasta.
# py-bcb — diário técnico

## 2026-06-17 — Grid intraday de reação de mercado do FOMC (estilo COPOM)

### O que se queria
Há anos a Mesa cola no relatório Word do FOMC um **screenshot do Chart Grid da
Bloomberg**: nove minigráficos intraday lado a lado (Nasdaq, S&P, Russell, UST 2Y,
10Y, a inclinação 2s10s, o OIS forward, o dólar e o VIX). Bonito, mas é uma foto —
estática, sem as marcas dos horários que realmente importam. O pedido foi
*reproduzir* esse painel em Python, no nosso visual COPOM, e cravar três linhas
verticais: a hora da decisão, o início e o fim da coletiva do Powell.

### A pegadinha do fuso (a parte interessante)
Os horários do FOMC são âncoras fixas em **horário de Nova York**: decisão às
14:00 ET, coletiva às 14:30 ET. O que se mexe embaixo dos pés é a *distância* até
Brasília. O Brasil abandonou o horário de verão em 2019 (UTC−3 o ano todo), mas os
EUA não: hoje, em pleno DST americano, NY está em UTC−4 e Brasília fica **1 hora à
frente** (14:00 ET = 15:00 BRT). Quando os EUA saírem do DST (01/nov/2026), NY cai
para UTC−5 e a diferença vira **2 horas** (14:00 ET = 16:00 BRT).

A tentação é deixar o usuário digitar "15:00" e "15:30" na mão e lembrar de trocar
em novembro. Erro clássico de fuso esperando para acontecer. A solução elegante foi
fazer do **ET a fonte-da-verdade** e converter para Brasília com `zoneinfo`
(`America/New_York` → `America/Sao_Paulo`), que conhece as regras de DST de cor.
O notebook expõe três strings ET editáveis (decisão/início/fim), mas a conversão é
automática. Validado nos dois regimes: junho → 15:00/15:30; dezembro → 16:00/16:30.
O fim da coletiva continua manual — é variável por natureza, ninguém sabe quando o
Powell vai parar de falar.

### Armadilhas encontradas pelo caminho
1. **Hook de Read suicida.** Um `PreToolUse` em `settings.local.json` rodava
   `python C:\Users\...\clear_ipynb.py` em *toda* leitura de arquivo. No shell bash
   dos hooks, as barras invertidas do Windows somem (`C:\Users` vira
   `C:Usersmmart...`) e o python não acha o script — bloqueando 100% das leituras,
   inclusive de imagens. Conserto: barras `/` e a guarda `if: Read(/**/*.ipynb)`
   para o hook só rodar em notebooks, que é o seu propósito (limpar outputs).
2. **O screenshot não era PNG.** Apesar da extensão `.png`, o header era `42 4D`
   ("BM") — um BMP. Converti com Pillow para conseguir enxergar o layout.
3. **Python 2 fossilizado.** `data_loader.py` tinha `except RuntimeError, KeyError:`
   — sintaxe Python 2, que é *SyntaxError* no 3.13. O módulo simplesmente não
   importava. Dois `(parênteses)` resolveram.
4. **O `abdib` mentiu sobre o índice.** O backend rust do xbbg 1.0 devolve o
   timestamp numa *coluna* `time` (em UTC), não no índice — o índice é um
   `RangeIndex` inútil. O código antigo fazia `df["close"]` e perdia o horário
   silenciosamente. Agora reindexamos por `time`, que já vem tz-aware em UTC;
   convertemos para ET (para filtrar a janela) e depois para Brasília (exibição).
5. **Caça ao ticker do OIS (resolvida por derivação).** O painel "USD OIS FWD swap
   1Y1Y" foi o vilão. Vários palpites (`USSO1F1`, `USOSFR1F1`...) eram inválidos ou
   eram outra coisa (1Y spot, 18M, 11Y). O nome bateu exato em `S0490FS 1Y1Y BLC2
   Curncy`, mas pontos de curva BLC2 **não têm barras intraday** no `abdib` (zero
   linhas). Solução: em vez de procurar um ticker direto, **derivar** o forward 1Y1Y
   dos OIS 1Y (`USSO1`) e 2Y (`USSO2`), que têm intraday denso. Ver fórmula abaixo.

### Como ficou
- `data_loader.fetch_market_reaction()` busca os 9 tickers, deriva o 2s10s em bps,
  e devolve um DataFrame com índice tz-aware em Brasília.
- `word_export.create_market_reaction_grid()` desenha o 3×3 COPOM: linha por painel,
  rótulo de último valor, linha-referência no nível de abertura, três `axvline`
  (sólida = decisão, tracejada = início, pontilhada = fim) e legenda única. Eixo X
  formatado em hora de Brasília (índice convertido para naive BRT antes de plotar,
  para o matplotlib não reinterpretar o fuso).
- O notebook (`fomc_analysis.ipynb`) ganhou os horários ET no bloco de config e uma
  célula que gera o PNG e redireciona `MARKET_REACTION_PNG` para ele — o screenshot
  manual da Bloomberg vira apenas fallback se o terminal estiver fora do ar.

### Decisões de design que vale lembrar
- **E-mini futures, não índices à vista** (`NQ1`/`ES1`/`RTY1 Index`). A primeira
  versão usou NDX/SPX/RTY cash "por simplicidade", mas o pedido era mostrar os
  dados *desde a abertura da Ásia* — e só os futuros negociam overnight (~23h). Os
  índices cash só abrem às 09:30 ET e não teriam a sessão asiática. Lição: quando o
  gráfico precisa do overnight, futuro contínuo (`...1 Index`), não cash. Os
  genéricos `...A Index` vêm esparsos (NQA/RTYA com dezenas de barras); os `...1`
  vêm densos (1-min, >1000 barras).
- **Janela = dia inteiro** (`session="allday"`, sem corte). `fetch_market_reaction`
  ganhou `start_time`/`end_time` opcionais (default None). O índice converte para
  Brasília; a janela vai de ~21:00 do dia anterior (= 00:00 UTC = abertura de Tóquio)
  até ~21:00 BRT. As 3 linhas de evento marcam a reação dentro desse dia completo.
- **OIS 1Y1Y derivado, não baixado.** Como não há ticker intraday do forward 1Y1Y
  (o `S0490FS 1Y1Y BLC2` tem o nome certo mas zero barras intraday), derivamos de
  `USSO1`/`USSO2` (OIS 1Y/2Y, ambos com intraday denso) por fatores de desconto:
  `f(1y,1y) = (1+S2)²/(1+S1) − 1`. Em curva invertida o forward fica *abaixo* do
  spot — sanity check que confirmou a fórmula.
- O eixo X usa `AutoDateLocator` (não `HourLocator` fixo): com o dia inteiro, hora-a-
  hora daria ~24 ticks ilegíveis.
- Reservamos o vermelho (`COPOM_COLORS[4]`) para as linhas de evento, então nenhum
  painel usa essa cor — as linhas sempre saltam aos olhos.
- A figura é dimensionada (7,0 × 8,5 pol, 150 DPI) para entrar em **docx A4** na
  largura útil da página (`WORD_PAGE_WIDTH_INCHES = 7,0`).

## 2026-07-02 — Grid de reação intraday para o Payroll

O grid 3×3 do FOMC era bom demais para ficar preso a um único evento. Quando surgiu
o pedido de uma versão para o payroll, a tentação óbvia era copiar
`fetch_market_reaction` + `create_market_reaction_grid` para `payroll/core` — mas
os 9 painéis são os mesmos (bolsas, juros, DXY e VIX não mudam porque o evento
mudou) e a única coisa realmente "FOMC" no desenho era o rótulo da linha vertical,
hardcoded na constante `MARKET_REACTION_EVENTS` ("Decisão FOMC").

A solução foi cirúrgica: `create_market_reaction_grid()` ganhou um parâmetro
opcional `events` (lista de tuplas `(chave, rótulo, estilo)`), com default apontando
para a constante FOMC — zero impacto nos chamadores existentes (verificado com
figura sintética: default ainda desenha "Decisão FOMC"). O novo notebook
`src/reports/payroll/notebooks/market_reaction_grid.ipynb` espelha o do FOMC e
importa direto de `reports.fomc.core`, passando
`events=[("payroll", "Payroll", "-")]` e o horário fixo de 8:30 ET (mesma
estratégia de fuso do FOMC: ET é a fonte-da-verdade, zoneinfo converte — 9:30 BRT
no verão de NY, 10:30 no inverno). O eixo X vai até 14:00 BRT: a reação ao payroll
é história da manhã, não precisa das 20:00 do FOMC.

Armadilha encontrada na primeira execução: o default de `RELEASE_DATE` apontava
para 03/07/2026 ("primeira sexta do mês") — mas 04/07 caía num sábado, o feriado
foi observado na sexta (mercado fechado) e o BLS antecipou a divulgação para
quinta 02/07. Data sem pregão (ou futura) faz o `abdib` devolver zero barras para
*todos* os tickers e o `fetch_market_reaction` estoura um genérico "No intraday
data returned from Bloomberg" — que parece problema de terminal, mas é só
calendário. Lição: payroll não é "primeira sexta" por decreto; é o que está em
bls.gov/schedule. O comentário do config agora avisa.

Pensamento para o futuro: se um terceiro evento aparecer (CPI?), aí sim vale
promover o par fetch+grid para `src/classes/` — dois usos ainda não justificam a
mudança de endereço, três justificam.

## 2026-08-07 — O gráfico que mentia sobre o horário (estilo `bloomberg`)

O relato chegou como bug: *"são 10:25 agora, como que a linha aparece em todos os
gráficos até as 16h?"*. Reclamação legítima — um gráfico intraday que finge ter
dado até o fim do dia é pior que gráfico nenhum, porque convida a ler um movimento
que não aconteceu.

Só que o culpado não era o desenho. Era o calendário, **de novo** (ver a armadilha
de 02/07 acima). O `RELEASE_DATE` do notebook ainda apontava para `20260702`, uma
sessão encerrada há mais de um mês. Para uma data no passado o `abdib` devolve o
pregão **inteiro** — medi: dados até 20:59 BRT. Ou seja, a linha ia até as 16h/18h
porque *existia* dado até lá. O bug era o config velho, não o eixo.

Mas a investigação desenterrou um bug de verdade, escondido atrás do primeiro:
`axis_end` era aplicado como `ax.set_xlim(right=axis_end)`, e a docstring prometia
**estender** o eixo ("área em branco à direita"). Quando os dados passavam de
`axis_end`, aquele `set_xlim` **cortava** a série no meio — e junto com ela levava o
rótulo do último valor, desenhado num ponto agora fora dos eixos. Daí a figura de
diagnóstico com 9 painéis e só 2 rótulos visíveis: não era clipping de texto, era o
eixo comendo o fim da série. A correção é uma linha —
`set_xlim(right=max(axis_end, último_tick))` — e ela restaura exatamente o contrato
que a docstring já descrevia. Lição que vale repetir: quando o código e a docstring
divergem, o bug costuma estar no código, e o teste é ler a docstring como
especificação.

### O estilo `bloomberg`
O pedido de fundo era estético: parecer o Chart Grid da Bloomberg (screenshot de
referência). Aqui havia uma bifurcação real, porque
`create_market_reaction_grid()` é compartilhada com `fomc_analysis.ipynb`, que
alimenta o Word. Restilizar in place mudaria o relatório do FOMC de tabela. Seguimos
o mesmo precedente do parâmetro `events`: um `style="word"` (default, FOMC
intocado) / `"bloomberg"` (opt-in). Terceiro parâmetro opcional, terceira vez que a
função se estica sem quebrar chamador — o padrão está se provando.

Decisão de gosto que merece registro: adotamos a **estrutura** da Bloomberg, não o
tema escuro. Área preenchida sob a curva, eixo Y à direita, caixa do último valor
sobre o eixo, ticks de hora sem rotação. Fundo preto renderiza mal em docx e pior
impresso, e a paleta COPOM é a identidade dos relatórios — copiar o dark theme seria
imitar a aparência e perder a função.

O detalhe que de fato resolve a queixa original não é gráfico nenhum, é texto: o
subtítulo `T=valor  variação  %  HH:MM`, no estilo do terminal. Com o horário do
último tick impresso em cada painel, "até quando esse dado vale?" deixa de ser uma
inferência visual sobre onde a linha encosta. E ele expõe de graça a defasagem entre
fontes — hoje os futuros marcavam 11:49, o DXY 11:39, o VIX 11:34. Três relógios
diferentes num mesmo grid, algo que a versão anterior escondia.

Duas armadilhas de matplotlib no caminho:
- **`fill_between` precisa do piso do eixo, e o piso precisa existir antes.** Encher
  até `ax.get_ylim()[0]` com autoscale ligado dá resultado errado, porque o autoscale
  recalcula depois do fill. Ordem obrigatória: calcular min/max da série → `set_ylim`
  explícito → `fill_between` até esse piso.
- **O `AutoDateLocator` não sabe a largura do painel.** Com `maxticks=7` e rótulos
  horizontais em painel estreito, "00:00 04:00 08:00" virava `00:0004:0008:00`. No
  estilo bloomberg baixamos para `maxticks=5` (a rotação de 45° do estilo `word`
  disfarçava o problema — tirar a rotação foi o que o revelou).

Falso positivo que quase virou correção: na figura renderizada o preenchimento
*parecia* passar ~30 min além do fim da linha, em todos os painéis. Antes de mexer,
medi os vértices do `PolyCollection` contra o `xdata` da linha — idênticos nos 9
painéis. Era ilusão de óptica da borda do fill com alpha 0,16 sobre o grid pontilhado.
Lição: em bug visual, medir o objeto, não confiar no olho sobre um PNG reescalado.

### O VIX e os ticks a mais
Observação seguinte, boa: *"o vix aparece com mais major ticks do que os outros
gráficos"*. Verdade, e a causa é bonita — o **VIX não tem cotação overnight**. Os
futuros começam ~21:00 BRT do dia anterior; o VIX só às 04:15. Intervalo visível
mais curto → o `AutoDateLocator` escolhe um passo menor → mais ticks. Medido no
estilo `word`: 8 painéis com passo de 4h (5 ticks) e o VIX com 2h (7 ticks).

A raiz não era o locator, era **cada painel ter seu próprio `xlim`**. Passamos a
calcular uma janela X comum antes do laço (menor início e maior fim entre os 9
painéis, esticada até `axis_end`) e aplicá-la a todos. Consequência elegante: como o
`AutoDateLocator` depende só do intervalo visível, ticks idênticos saem de graça —
não precisa sincronizar locator nenhum. Custo aceito de propósito: o painel do VIX
ganha um vazio à esquerda. É informação, não defeito — mostra que ali não existe
mercado, em vez de esticar a série para preencher o painel.

Com a janela comum garantida, trocamos o `AutoDateLocator` por um `HourLocator` de
passo fixo, ancorado na meia-noite: o passo é escolhido uma vez (menor valor em
1/2/3/4/6/8/12h que caiba ~3 rótulos) e vale para os 9 painéis. Dois ganhos sobre o
automático: o **horário de corte também recebe rótulo** (com `axis_end` em 16:00 dá
exatamente 00:00 / 08:00 / 16:00 — o mesmo do screenshot de referência, por
coincidência feliz), e a consistência passa a ser estrutural em vez de emergente.
Ancorar na meia-noite é o detalhe que faz o rótulo cair em hora redonda; o
`AutoDateLocator` ancorava no início dos dados e parava em 00:00/06:00/12:00,
deixando o corte das 16:00 sem marca.

Nota de escopo: a janela comum vale **só** no estilo `bloomberg`. O `word` mantém o
`xlim` por painel — o VIX continua com seus 7 ticks no relatório do FOMC. Foi
decisão consciente de manter o contrato "`style="word"` é byte-estável", verificada
com um script que imprime `xlim` + ticks de cada painel e conta assinaturas
distintas (1 no bloomberg, 2 no word). Se o FOMC quiser a mesma consistência, é
mover duas linhas para fora do `if bbg`.

### A linha de evento tapava a reação
Último ajuste do dia, e um bom exemplo de sintoma que aponta para a causa errada. O
pedido foi "aumente a transparência da linha vertical, acaba escondendo a linha por
trás" — mas alpha era só metade do problema. A `axvline` do evento é desenhada
**depois** da série, e entre artistas de mesmo `zorder` o matplotlib empilha por
ordem de criação: o vermelho ficava literalmente por cima do movimento. Pior no
payroll que no FOMC, porque a reação do payroll é uma vertical quase colada ao
evento (veja UST 2Y e OIS 1Y1Y: o mergulho acontece *no* minuto da divulgação).

Baixar o alpha sozinho clarearia a marca sem resolver a sobreposição. A correção é
`alpha=0.45` **e** `zorder=1.5` — entre a área preenchida (1) e a série (2). Assim a
linha de evento fica acima do fill, para continuar legível, e abaixo da série, para
nunca comer o dado. O rótulo "Payroll" segue 100% opaco: ele mora na margem
superior, onde não há série para tapar.

Detalhe que deixou o `word` byte-estável de graça: o default de `zorder` da `Line2D`
é exatamente 2 (verificado, não presumido), então `event_zorder = 2` no ramo `word`
reproduz o comportamento anterior sem `if` extra no ponto de desenho.

