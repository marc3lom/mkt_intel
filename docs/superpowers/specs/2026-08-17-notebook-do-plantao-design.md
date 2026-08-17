# Notebook do plantão: uma segunda fachada sobre um núcleo único

Data: 17/08/2026

## Contexto

O plantão hoje roda por linha de comando. O autor quer poder rodá-lo também por
notebook, com as duas formas existindo em paralelo, e que alteração numa se reflita na
outra.

Essa última exigência é o problema inteiro. Duas descrições do mesmo processo divergem, e
divergem em silêncio — este repositório passou 17/08 pagando essa conta em quatro
frentes: a separação `daily`/`comentario_matinal`, que foi colapsada; o
`project_instructions.md`, do qual as convenções duplicadas foram arrancadas porque "a
segunda envelheceria em silêncio na primeira revisão do guia"; o `.docx` contra o `.md`,
que divergiu de fato e mandou uma frase quebrada à mesa; e uma segunda lista de ativos
que a revisão final apontou como defeito.

Em todos, o que falhou foi exatamente o que se pede aqui: a intenção de manter duas
coisas iguais. Então o desenho não é "escrever um notebook", e sim **construir o
mecanismo que faz a sincronia acontecer sozinha, ou falhar alto**.

## Decisão

Nem o comando nem o notebook implementam o plantão. Ambos são fachadas finas sobre um
núcleo novo, `plantao.py`, extraído do `cli.py`. O que mantém os dois em sincronia é que
não há o que sincronizar: há uma implementação só.

O que **não** é evitável é a duplicação da *sequência* — a ordem dos passos existe no
`argparse` e nas células. Essa parte ganha um teste que fica vermelho quando as duas
divergem.

## O núcleo: `src/comentario_matinal/plantao.py`

### O contexto

Hoje o pacote de argumentos comuns — configuração, `asof`, pasta de saída, marca da data
e a decisão de dry run — é montado dentro do `main()`, entre as linhas 107 e 134. Se o
notebook o remontasse por conta própria, seria a primeira coisa a divergir, e a primeira
a errar seria o dry run: uma célula rodada às 15h produziria saída idêntica à das 7h30.

```python
@dataclass(frozen=True)
class Contexto:
    cfg: Config
    asof: datetime
    saida: Path
    marca: str          # AAAAMMDD
    dry_run: bool

def contexto(asof: datetime | str | None = None,
             saida: Path = SAIDA_PADRAO,
             config: Path = CONFIG_PADRAO) -> Contexto
```

`dry_run` sai de `not na_janela(agora())` — relógio real, nunca o `asof`, como hoje. A
regra continua num lugar só.

### Os passos

As quatro seções que o `main()` já separa por comentário viram funções. As costuras
existem; o trabalho é torná-las chamáveis.

```python
def coleta_mercado(ctx) -> Mercado
def desenha_painel(ctx, mercado) -> Painel
def prepara_calendario(ctx) -> Calendario
def monta_bloco(ctx, mercado, painel, calendario: Calendario | None) -> Bloco

def roda_etapa(ctx, nome, fontes, arquivo, *, temas=None, anterior=None,
               web=False, modelo=None) -> Etapa
def monta_documento(ctx, comentario, template, painel, calendario) -> Path
def confere(ctx) -> list[Divergencia]      # Divergencia vem de enviado.py
def fecha_plantao(ctx, arquivo, fontes, forcar=False) -> Fechamento
```

A garantia de coleta única não vem de os passos serem uma função só; vem do fluxo de
dados. `desenha_painel` e `monta_bloco` exigem o `Mercado` que `coleta_mercado`
devolveu, então não há caminho que colete duas vezes.

Duas escolhas de nome que a primeira versão deste spec errou, registradas para que a
implementação não as repita:

- **`prepara_calendario`, não `coleta_calendario`.** O módulo `calendario.py` já exporta
  uma função com esse nome, e o núcleo a chama. Duas funções homônimas no mesmo fluxo de
  import é confusão gratuita. E "prepara" é mais honesto: ela consulta o BQL, desenha a
  tabela e grava a versão em texto que as etapas de IA leem.
- **`--sem-calendario` não vira parâmetro do núcleo.** A fachada simplesmente não chama
  `prepara_calendario`, e `monta_bloco` recebe `None`. Passar uma bandeira de "não faça
  seu trabalho" para dentro da função que faz o trabalho é vocabulário de terminal
  vazando para o núcleo. O `calendario_vazio` que o `monta_texto` exige passa a ser
  `calendario is None or calendario.eco is None or calendario.eco.empty`, no lugar do
  `args.sem_calendario or …` de hoje.

### Os resultados

```python
@dataclass(frozen=True)
class Mercado:
    referencia: pd.DataFrame
    intraday: dict[str, pd.Series]
    indisponiveis: list[str]

@dataclass(frozen=True)
class Painel:
    figura: Figure
    metricas: dict[str, dict]
    caminho: Path

@dataclass(frozen=True)
class Calendario:
    eco: pd.DataFrame | None
    bancos: pd.DataFrame | None
    figura: Figure | None
    caminho_png: Path | None
    caminho_md: Path | None
    avisos: list[str]

@dataclass(frozen=True)
class Bloco:
    texto: str
    caminho: Path
    avisos: list[str]

@dataclass(frozen=True)
class Etapa:
    nome: str
    texto: str
    caminho: Path
    asof: datetime            # o horário de redação efetivamente usado
    comentario: Path | None   # só a revisão produz
    avisos: list[str]

@dataclass(frozen=True)
class Fechamento:
    arquivados: list[Path]
    removidos: int
```

### Erro e aviso deixam de ser `print`

Hoje o `cli.py` mistura três coisas: fazer, avisar e decidir o código de saída. O núcleo
separa as três.

- **Erro** levanta exceção. Uma hierarquia mínima: `ErroDePlantao(RuntimeError)`, com
  `SemDadoDeMercado` (a consulta de referência voltou vazia) e `FaltaInsumo` (falta o
  bloco direcional, faltam os temas). `FileNotFoundError` e `DestinoOcupado`, que já
  existem, continuam como estão.
- **Aviso** viaja no objeto de resultado, na lista `avisos`. Hoje esses avisos vão ao
  stderr e somem — "N ativos sem dado de referência", "sem dados para renderizar a
  tabela", "PDF sem OCR", "arquivo não-PDF ignorado", "`--asof` diverge da referência do
  painel". Passando a ser dado, ficam inspecionáveis pelas duas fachadas e aferíveis por
  teste.
- **Código de saída** é vocabulário de terminal e não entra no núcleo.

Isto é melhoria de projeto embutida na mudança, não escopo novo: sem ela, o notebook
receberia `1` e uma string impressa no lugar errado.

## As duas fachadas

**`cli.py`** vira tradução: argumentos → chamada → formatação → código de saída. Deve
cair de 559 linhas para perto de 300. A tradução de bandeira para argumento fica aqui —
`--temas "a | b | c"` virar lista, `--temas-arquivo` virar texto, `--sem-anterior` e
`--anterior` resolverem o comentário do dia anterior. Isso é vocabulário de terminal.

**`notebooks/plantao.ipynb`** chama as mesmas funções e mostra os objetos: a figura
inline, o `DataFrame` de referência, as métricas por ticker, o texto do bloco. Entre as
células, markdown com o que conferir antes de seguir.

O dry run é desenhado como faixa visível — HTML no notebook, não linha de log. É a
diferença que mais importa entre as duas fachadas: no terminal o banner de stderr
interrompe a leitura; numa célula, passa batido.

## O alcance do notebook

Passos 1 a 8 do runbook: coleta, triagem, escolha de temas, redação, revisão, montagem
do `.docx`, conferência.

**O `enviado` fica só no terminal.** É o único passo destrutivo — apaga `fontes/` e
`saida/` e grava o arquivo que a triagem do dia seguinte lê como comentário anterior — e
notebook é onde se re-executa célula sem querer. Um "Run All" descuidado o dispararia.

## O mecanismo de sincronia

Três testes. O segundo é a resposta direta ao "quando houver alteração em uma a outra tem
de se adaptar".

### a) Caracterização, escrito ANTES de mover uma linha

Roda o caminho de coleta inteiro com `coleta_referencia`, `coleta_intraday` e
`calendario.coleta_calendario` falsificados por `monkeypatch`, e afere os quatro arquivos
produzidos: `painel_AAAAMMDD.png`, `calendario_AAAAMMDD.png`, `calendario_AAAAMMDD.md`,
`painel_AAAAMMDD.txt`. Verde contra o `main()` atual, verde depois da extração.

Os 101 testes de hoje cobrem módulos, não orquestração: quase nada em `cli.py` é
exercitado, e um `main()` quebrado passaria verde. Esta é a rede que não existe, e ela
precisa existir antes, não depois.

### b) Cobertura do notebook

Lê o `.ipynb` com `nbformat` e afere que cada nome de `plantao.__all__`, exceto
`fecha_plantao`, aparece em alguma célula de código; e que cada subcomando da lista
`choices` do `argparse`, exceto `enviado`, também. Passo novo sem célula nova → vermelho.

`plantao.__all__` é o contrato: declarar a superfície pública explicitamente é o que
torna o teste possível.

### c) Saídas limpas

O notebook comitado não pode ter `outputs` nem `execution_count`. Sem isso, rodar o
plantão de manhã e comitar enfia dados de mercado e o texto do comentário — antes de ele
ter sido enviado — no histórico do git.

Junto vai `.gitattributes` com `*.ipynb filter=nbstripout`, que limpa no `git add`, e uma
linha na configuração inicial mandando rodar `uv run nbstripout --install`. O teste é a
rede para o clone novo onde o filtro não foi instalado.

## Dependências

Ao grupo `dev`, que o `uv sync` já instala por padrão:

| Pacote | Para quê |
|---|---|
| `ipykernel` | executar o notebook |
| `nbformat` | os testes (b) e (c) leem o `.ipynb` |
| `nbstripout` | o filtro do `.gitattributes` |

O `jupyterlab` fica de fora: quem usa VS Code não precisa dele, e é dependência pesada
para quem só usa o comando.

## Sequenciamento

Três commits, nesta ordem:

1. **Teste de caracterização**, verde contra o código atual.
2. **Extração do `plantao.py`** e o `cli.py` reduzido a fachada. O teste de caracterização
   continua verde.
3. **Notebook**, os dois testes de sincronia, o `.gitattributes` e as dependências.

Reverter o commit 2 devolve o `cli.py` que funcionou em produção em 17/08, sem tocar no
resto.

## Fora de escopo

- O wiki, que é o segundo subprojeto e documentará o resultado deste.
- A fronteira do `render/` que a revisão de 17/08 levantou — `config.py` importar
  `ItemDaGrade` da camada de desenho é dependência invertida, mas é outro assunto.
- Qualquer mudança de comportamento. Isto é mudança de lugar mais uma fachada nova.
- Executar o notebook nos testes. Exigiria terminal Bloomberg; a aferição é estática.

## Riscos

| Risco | Mitigação |
|---|---|
| A extração quebra o plantão de amanhã | Teste de caracterização antes de mover, e o commit 2 isolado para `git revert` |
| Uma célula rodada fora da janela passa por plantão | `dry_run` vem do `Contexto`, e o notebook o desenha como faixa, não como log |
| Dados de mercado vazam para o git | Teste (c) mais filtro `nbstripout` |
| Passo novo entra no comando e não no notebook | Teste (b) |
| `_roda_etapa` é a função mais densa a extrair — validação, avisos e resolução de `asof` misturados | Extrair preservando a ordem das checagens; os avisos viram lista, e o teste de caracterização não a cobre — cobrir com teste próprio de `roda_etapa` sobre insumos sintéticos |

## Critérios de aceitação

1. `uv run matinal` e todos os subcomandos se comportam como hoje — mesmas saídas, mesmas
   mensagens, mesmos códigos de saída.
2. O teste de caracterização passa antes e depois da extração.
3. `plantao.py` não importa `argparse` nem chama `sys.exit`; `cli.py` não contém regra de
   negócio.
4. O notebook cobre os oito passos e não menciona `fecha_plantao`.
5. Os testes (b) e (c) falham quando provocados — provar cada um, não afirmar.
6. `git add` de um notebook executado não leva `outputs` para o índice.
