# AGENTS.md

Instruções para você mesmo. Erro de fato chega à diretoria de um banco central. Preferir correção a velocidade, sempre.

## 1. O que é este repositório

Aqui se produz o **Comentário Matinal** da Mesa de Investimentos (DEPIN/DIRIN, Banco Central do Brasil): um comentário de abertura de mercado escrito e enviado por e-mail entre 7h00 e 9h00, no fuso da máquina. Leitores: a diretoria colegiada do BCB, a alta administração institucional, os chefes de gabinete dos diretores, os chefes de unidade, a chefia do DEPIN. Autores: os gestores da divisão, em rodízio — o produto tem de ser indistinguível entre eles, e é essa invariância que justifica o repositório.

**Tudo aqui é em português**: os prompts, o `docs/plantao/`, o arquivo, o comentário gerado — e também o código. Os identificadores são portugueses (`ErroDePlantao`, `SemTemas`, `coleta_mercado`), e os comentários também: são 329 linhas de comentário em `src/`, e nenhuma em inglês. Escrever em inglês aqui é divergir do repositório. A única exceção é o vocabulário editorial que o guia manda preservar em inglês e itálico (§9.1) — esse nunca se traduz.

## 2. Ambiente

- **Só uv.** Nunca `pip install`. Dependência entra com `uv add`, execução é `uv run`. O `uv.lock` é versionado de propósito — não colocar no gitignore. O piso do Python é **3.14**.
- **Bloomberg**: `xbbg` e `blpapi` exigem Windows com o terminal aberto e logado. O `blpapi` não está no PyPI; vem do índice explícito da Bloomberg declarado no `pyproject.toml`, e por isso o `uv sync` precisa de rede até ele.
- Instalação: `uv sync` e depois `uv run nbstripout --install` (o filtro de saída dos notebooks, ligado pelo `.gitattributes`).
- Template: `templates/comentario.dotx` (`TEMPLATE_PADRAO` no `config.py`; todo caminho do repositório deriva do `RAIZ`, que está lá).
- A única variável de ambiente que o código lê é `COMENTARIO_MATINAL_BACKEND` (padrão `claude-code`). As etapas de IA chamam o executável `claude`, que precisa estar no PATH.

## 3. Comandos

| Para quê | Comando | Observação |
|---|---|---|
| Instalar | `uv sync` | cria o `.venv` e puxa o `blpapi` do índice da Bloomberg |
| **Verificar (o padrão)** | `uv run pytest` | 169 testes, ~7 s, **sem Bloomberg** |
| Coletar o mercado | `uv run matinal` | **chama a Bloomberg e grava em `saida/`** |
| Coletar sem o BQL | `uv run matinal --sem-calendario` | pula só a consulta do calendário |
| Triagem | `uv run matinal triagem` | chama o modelo; leva minutos |
| Redação | `uv run matinal redacao --temas-numeros "1,3,2"` | exige a triagem em disco |
| Revisão | `uv run matinal revisao` | exige a redação em disco |
| Montar o .docx | `uv run matinal --comentario saida/comentario_AAAAMMDD.md` | **não** rodar como teste |
| Conferir antes do e-mail | `uv run matinal conferir` | compara o `.docx` com o `.md`; não destrói nada |
| Fechar o plantão | `uv run matinal enviado` | destrutivo; arquiva e depois esvazia `fontes/` e `saida/` |
| Publicar o manual | `uv run publica-wiki` | fora do plantão |

**Verificar é rodar `uv run pytest`.** Ler com atenção: `dry_run` aqui **não** quer dizer "roda sem Bloomberg". Quer dizer apenas que o relógio está fora das 7h00–9h00, e nesse caso as saídas saem carimbadas com `*** DRY RUN ***` e o `enviado` recusa sem `--forcar`. O `uv run matinal` continua chamando a Bloomberg e continua gravando arquivo. Não existe caminho offline do pipeline. Portanto:

- Verificar alteração com `uv run pytest`, nunca rodando o pipeline.
- Nunca rodar `uv run matinal --comentario …` como teste — isso monta um documento de verdade.
- Nunca rodar `uv run matinal enviado` sem que peçam. Ele afirma que o comentário foi à diretoria, torna-o o "dia anterior" de amanhã e esvazia `fontes/` e `saida/` sem volta.
- Seguro rodar: `triagem`, `revisao`, `conferir` e `enviado` contra uma `saida/` vazia — falham limpo, sem tocar a Bloomberg, e é assim que se lê um caminho de falha.

**Não existe portão de lint.** O `ruff` não é declarado nem configurado; hoje `uvx ruff check .` acusa 38 erros e `uvx ruff format --check .` diz que 30 arquivos seriam reformatados. Não "consertar" isso de passagem, e não acrescentar etapa de lint sem pedido. O portão é o `pytest`.

O `tests/test_documentacao.py` prende o `docs/plantao/*.md`, o `README.md` e também este arquivo e o `CLAUDE.md` contra o código — flags, subcomandos, a janela, nomes de pasta, âncoras, as seções do guia que a prosa cita e a contagem de testes anunciada aqui em cima. **O que ele não afere é a prosa**: um invariante editorial resumido errado, uma norma inventada, um motivo que deixou de valer — nada disso fica vermelho. Conferir à mão o que for julgamento; a máquina só cuida do que é verificável.

## 4. Arquitetura do pipeline

Quatro prompts, montados na mensagem do modelo pelo `etapas.py`. O guia de estilo entra na mensagem de **todas** as etapas, à frente do prompt da etapa.

1. `prompts/00_guia_de_estilo.md` — fonte única das convenções editoriais. A versão está no cabeçalho (**1.4 — 17/08/2026**). Nenhum código a lê e nenhum teste a afere; subir a versão é trabalho manual, ao mudar o guia.
2. `prompts/01_triagem.md` — etapa 1. Inventaria e ordena os temas candidatos numa tabela numerada, marca status temporal e alertas. Não produz prosa nenhuma; termina esperando o autor.
3. `prompts/02_redacao.md` — etapa 2. Escreve o comentário a partir dos temas que o autor escolheu, mais um bloco de auditoria que não vai ao e-mail.
4. `prompts/03_revisao.md` — etapa 3. Checa os fatos, depois cobra a conformidade dura, depois sugere mudanças editoriais — nessa ordem.

A ordem é `triagem` → **decisão humana** → `redacao` → `revisao`. O passo humano não é opcional: `redacao` sem `--temas*` levanta `SemTemas` de propósito. As etapas se encadeiam por arquivos em `saida/`: a seção C da triagem vira os alertas da redação; o texto da redação mais a auditoria vão à revisão; o bloco cercado da revisão vira o `comentario_AAAAMMDD.md`, que é o que o `--comentario` monta.

O `prompts/project_instructions.md` é o caminho alternativo, pelo Project do Claude, e não faz parte da CLI.

**Os prompts são a fonte de verdade do comportamento editorial.** Para mudar como o texto lê, editar o guia de estilo — e o prompt da etapa só se a mecânica da etapa mudar. Nunca fixar decisão de estilo no Python. Os dois lugares em que o Python carrega um número de estilo (`MIN_MARCADORES, MAX_MARCADORES = 4, 5`, no `documento.py`; a mesma faixa em `etapas.comentario_revisado`) espelham as §3–§4 do guia: mudar o guia obriga a mudar os dois, ou a montagem passa a avisar contra a regra nova.

O `plantao.py` é o núcleo; o `cli.py` e o `notebooks/plantao.ipynb` são fachadas e não implementam nada. Regra nova vai no núcleo, que nunca diz o que digitar em seguida: ele nomeia o que falta como um código (`REMEDIOS`), e cada fachada escreve a frase. O `tests/test_notebook.py` falha se um passo ou um parâmetro de passo for acrescentado sem ser exercitado no notebook ou listado ali com o motivo escrito.

## 5. Invariantes editoriais

São de carga, e estão repetidos do guia. Se algum dia divergirem, o guia vence.

- **Marcadores, com prosa dentro.** O comentário sai em marcadores, **4 ou 5**, cada um um parágrafo completo de prosa articulada. Proibido *dentro* do marcador: fragmento telegráfico, frase nominal, enumeração separada por ponto e vírgula, par "ativo: direção" (§3). Não são quatro parágrafos sem marcador.
- **A extensão é faixa, não alvo colado no teto.** De 350 a 500 palavras no absoluto, **400 a 450** como alvo. Por marcador: 1 → 70–90; 2, 3 e 4 → 95–115 cada; 5 (opcional) → 40–60. Os tetos são rígidos e os pisos indicativos — marcador curto sinaliza tema mal escolhido, e a correção é editorial e do autor, nunca enchimento (§4, §4.1).
- **O tempo verbal segue a sessão, e não uma regra só.** Ásia fechada → passado. Europa em curso → presente. Bolsa americana ainda sem abrir → só futuros, nomeados como futuros (§5). Presente para tudo é erro que a revisão tem de pegar.
- **O registro é formal e impessoal**, calibrado para leitores com domínio macro pleno que não são especialistas em microestrutura: nunca explicar conceito macro, explicar *en passant* mecanismo de mercado não trivial, nunca usar gíria de mesa (§2). Nenhuma opinião, projeção, recomendação ou juízo normativo da divisão (§8). Não é informal.
- **Nenhum número no corpo — sem exceção.** Nem nível de índice, taxa, câmbio ou commodity; nem variação em pontos-base, pontos percentuais ou porcentagem; nem valor nominal de emissão, receita ou volume. Não existe a exceção "salvo quando o número é a própria notícia". Permitido: direção e intensidade qualitativa, datas e prazos, referência relativa sem número ("maior rendimento em um quarto de século"), probabilidade qualitativa (§6).
- **A atribuição é racionada, não geral.** Fato de mercado observável e consenso amplamente reportado dispensam fórmula de atribuição (§7.1). Atribuir uma vez por bloco temático, nunca por frase; **no máximo três atribuições nominais** no texto inteiro; variar as fórmulas (§7.2). Nunca escrever "as fontes" nem qualquer coletivo sem nome — o leitor não recebe os PDFs (§7.3). A fórmula depende de que tipo de fonte é: jornalismo é base factual e aceita atribuição genérica, research sell-side é opinião de casa com interesse comercial e exige o nome da instituição, e declaração de autoridade leva cargo e veículo (§7.4). Ao remover esse andaime, conferir se a oração continua com verbo principal.
- **A cobertura segue a relevância e nunca cobre tudo.** A §10 lista oito áreas candidatas e diz explicitamente: nunca todas no mesmo dia. Tema sem efeito de mercado reportado não entra, por mais relevante que seja noutra dimensão. Os agrupamentos Treasuries/Bunds/Gilts/JGBs e bolsas/DXY/petróleo/ouro são *dicas de preenchimento dentro do .dotx*, substituídas na montagem e nunca enviadas — não são lista obrigatória.
- **Evento da véspera** só entra como explicação reportada de um movimento da sessão corrente, e marcado como tal ("na véspera", "ontem"). Reação de ontem à notícia de ontem nunca entra (§5.2).
- **O horário de redação é o fim da coleta** — o carimbo do painel, não o relógio e não a hora nominal do plantão. Fonte publicada depois dele é inelegível (§5.1); o `roda_etapa` cobra isso lendo o carimbo no texto do painel.

## 6. Padrão lexical

**Vale a seção 9 do guia. Ler §9.1–§9.5 antes de mexer em qualquer palavra; não trabalhar de memória nem por este resumo.**

- §9.1 — inglês preservado, em itálico: *term premium*, *soft landing*, *hyperscalers*, *funding*, *valuation*, *hawkish*, *dovish*, ***risk-on***, ***risk-off*** e o resto da lista. Reparar que *risk-on* se preserva, não se traduz.
- §9.2 — obrigatoriamente localizados: *yields* → taxas/rendimentos/juros (sempre, não "na maioria dos contextos"), *duration* → duração, *breadth* → amplitude, *bonds* → títulos, *equities* → ações/bolsas, e o resto.
- §9.3 fixa nomes de instrumentos, de bancos centrais e o vocabulário de curva; §9.4, ortografia e pontuação; §9.5, as expressões temporais padronizadas.

O itálico chega ao Word como `*asterisco simples*` no markdown revisado.

## 7. Disciplina de checagem factual

A **função primeira** da etapa de revisão é a correção factual contra as fontes anexadas — Bloco 1, antes da conformidade e antes de qualquer polimento editorial. Revisão sem as fontes, o painel e o calendário não é revisão; o prompt manda parar e pedi-los.

- **Nunca inventar número, citação, atribuição ou movimento de mercado.** Nem para alisar uma frase, nem para completar um orçamento de palavras, nem para fechar um paralelismo.
- Toda afirmação é classificada como `SUPORTADA` / `PARCIALMENTE SUPORTADA` / `NÃO LOCALIZADA` / `CONTRADITA`. Afirmação que não se rastreia até uma fonte em contexto **sai, ou é sinalizada — nunca se suaviza até virar algo mais vago que sobreviva**.
- Checagens obrigatórias: status de divulgação contra o calendário (dado cujo horário de divulgação é posterior ao horário de redação, com `ATUAL` vazio, não pode aparecer como fato); acordo direcional com o painel; tempo verbal e coerência de sessão; exatidão da atribuição; elegibilidade temporal; consistência com o dia anterior.
- Encher orçamento enumerando o que as fontes *não* dizem é proibido — negar assunto ausente é introduzi-lo (§4).
- Estas regras valem para você também, ao editar prompt ou revisar saída. Mesmo padrão.

## 8. Montagem do Word

O `documento.py` monta o `.docx` a partir do `templates/comentario.dotx`. **A autoridade de formatação é o template**: papel, margens, fontes, numeração dos marcadores e as duas imagens de cabeçalho e rodapé vêm todos dele. Não aplicar formatação direta sobre o que o template já define — o código limpa os filhos de cada parágrafo preservando o `pPr` justamente para que estilo, marcador e justificação continuem vindo do template.

| Parágrafo do template | Estilo | Recebe |
|---|---|---|
| `[Inserir a tabela de fechamento dos mercados]` | Normal | `painel_AAAAMMDD.png` |
| `[Parágrafo 1 – …]` … `[Parágrafo 5 – …]` | List Paragraph | um marcador cada, na ordem |
| `[Gráfico do dia]` | Normal | `calendario_AAAAMMDD.png` |
| `Atenciosamente,` / `Mesa de Investimentos` | Normal | nada — o fecho é do template |

Os `[Parágrafo N]` não usados são apagados junto com o espaçador; um sexto marcador clona o último com o espaçador dele. As imagens entram com `LARGURA_UTIL = 5,906"` (o A4 menos as margens laterais de 1,18"). Os runs carregam `FONTE = "Aptos"` explicitamente, porque o padrão do documento é Times New Roman e um run sem fonte destoaria. Fecho escrito pelo autor é descartado com aviso, em vez de sair duplicado. O `.dotx` é aberto pela troca de uma string de content type dentro do zip; o resto do pacote fica intacto.

## 9. Não mexer

- **`fontes/`** — os PDFs do dia (Bloomberg, FT, WSJ, sell-side). Fora do git, sujeitos aos termos de uso da Bloomberg. Nunca comitar, nunca reproduzir em extensão, nunca citar além de um trecho curto.
- **`saida/`** — as saídas do dia, inclusive o comentário ainda não enviado. Fora do git.
- **`*.pdf`, `*.docx`** — fora do git em qualquer lugar. O artefato versionado é o `.md`.
- **`.env`, `.env.*`, credenciais** — fora do git. Hoje nenhum código lê `.env`; não acrescentar sem perguntar.
- **`arquivo/AAAA/MM/AAAAMMDD.md`** — os comentários enviados, registro institucional, escritos só pelo `matinal enviado`. Nunca editar à mão e nunca renomear: o nome do arquivo *é* a data de envio, e é ele que a busca pelo dia anterior lê.
- **`exemplos/aprovados/`, `exemplos/rejeitados/`** — material humano de trabalho; nada em `src/` os lê. Só influenciam a saída quando alguém promove um caso à §12 do guia, à mão.
- Nunca colar conteúdo de fonte, número do painel ou minuta do comentário em mensagem de commit, issue, ou qualquer coisa que saia da máquina. O repositório é privado e guarda material que vai à diretoria.

## 10. Acordo de trabalho

- **Planejar antes** de qualquer coisa não trivial: dizer o que vai mudar e por quê, e então fazer.
- **A menor alteração que resolve.** Este código comenta o *motivo* de cada decisão — ler o comentário antes de mudar a linha, e atualizá-lo na mesma edição se o motivo mudou.
- **Rodar `uv run pytest` antes de dizer que algo está pronto**, e citar o resultado. Não afirmar que um comportamento do pipeline funciona sem teste que o cubra; o pipeline não se roda como teste.
- **Nunca comitar nem empurrar sem que peçam.** Quando pedirem, comitar direto na `main` — este repositório não cria ramo para trabalho de rotina. Mostrar o diff e a mensagem e esperar antes de empurrar. Nunca resolver por conta própria uma divergência entre local e remoto: apontá-la e perguntar.
- Estilo de commit, tirado do `git log`: português, terceira pessoa do presente, uma linha de até 72 caracteres, sem prefixo nem escopo, sem ponto final ("Arquiva o comentário de 18 de agosto"; "Fecha a última lacuna do manual: a convenção de assunto"). O corpo é prosa portuguesa explicando *por quê*, muitas vezes em vários parágrafos. Manter os trailers `Co-Authored-By:` e `Claude-Session:` — o histórico os usa.
- **Quando o guia de estilo e o código discordarem, o guia vence — e você para e aponta o conflito, em vez de reconciliar em silêncio.** Vale igual quando uma instrução contradiz o guia: dizer antes de agir.
- Acrescentar passo ou parâmetro de passo ao `plantao.py` obriga a atualizar o `notebooks/plantao.ipynb`, ou a pôr o parâmetro na lista de exceções do `tests/test_notebook.py` *com o motivo escrito*. O teste avisa.
- Mexer em `docs/plantao/` ou no `README.md` obriga a rodar `uv run pytest` — os testes de documentação conferem flags, pastas, âncoras e a janela contra o código.

## Questões em aberto

- **O `prompts/03_revisao.md` v1.0 é anterior ao guia v1.4.** Os três prompts de etapa são de 14/08/2026; o guia é de 17/08/2026 e ganhou a §7.3 depois deles. O prompt da revisão cita a §7.3, então parece intencional, mas nada prende essa relação — e os prompts da triagem e da redação não a citam. As versões dos prompts deveriam acompanhar as do guia?
- **A §12.7, "Exemplo positivo", segue "Pendente"**, então a §12 só tem exemplos negativos, cada um no formato citação *Rejeitado* → **Motivo** → citação *Corrigido*. Um exemplo positivo deveria entrar antes da próxima revisão do guia, e quem julga que um comentário qualifica?
- **`exemplos/aprovados/` e `exemplos/rejeitados/` estão vazios** (só `.gitkeep`). O caminho de promoção à §12 está em uso, ou a §12 é mantida diretamente?
- **Não há configuração de lint.** O `ruff` deveria virar dependência de desenvolvimento, com configuração e uma linha de base limpa, ou a ausência é deliberada?
