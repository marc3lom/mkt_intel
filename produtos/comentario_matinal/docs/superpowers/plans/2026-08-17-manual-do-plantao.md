# Manual do plantão — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar a quem vai rodar o plantão um manual próprio, e prender por teste a parte da sincronia com o código que pode ser aferida.

**Architecture:** O README se divide por leitor: o manual em `docs/plantao/` recebe a instalação e o runbook e ganha três páginas novas; o README fica com estrutura e notas de projeto. Nada é duplicado — o que estava num lugar continua num lugar, muda qual. Um teste na suíte de sempre afere comandos, passos, a janela e os caminhos. A cópia no Wiki do GitHub é derivada e carrega o SHA de origem.

**Tech Stack:** Python 3.14, uv, pytest, git.

**Spec:** `docs/superpowers/specs/2026-08-17-manual-do-plantao-design.md`

## Global Constraints

- Python `>=3.14`. Tudo por `uv run`.
- Português em tudo. O manual fala com o plantonista: segunda pessoa, imperativo, e o *porquê* onde o porquê evita um erro.
- **Nenhuma mudança em `src/`** além do módulo novo de publicação e da entrada em `[project.scripts]`. Os 136 testes de hoje continuam verdes.
- **Mover não é reescrever.** O texto que muda de lugar chega ao destino como está, mudando só cabeçalho, ligação entre seções e referência cruzada. Reescrever no mesmo passo esconde o que mudou — a extração do `plantao.py` cobrou essa lição em duas rodadas de correção.
- Ao fim de cada tarefa: `uv run pytest -q` verde e árvore limpa antes de comitar.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `docs/plantao/README.md` | **novo** — índice; é o que o GitHub abre ao navegar a pasta |
| `docs/plantao/01-primeiro-dia.md` | **novo** — orientação |
| `docs/plantao/02-instalacao.md` | **novo** — recebe a configuração inicial do README |
| `docs/plantao/03-runbook.md` | **novo** — recebe os nove passos do README |
| `docs/plantao/04-decisoes.md` | **novo** — o que é do autor decidir |
| `docs/plantao/05-quando-da-errado.md` | **novo** — modos de falha |
| `README.md` | encolhe de 476 para perto de 150 linhas |
| `tests/test_documentacao.py` | **novo** — a rede de sincronia |
| `src/comentario_matinal/wiki.py` | **novo** — o publicador |
| `pyproject.toml` | entrada `publica-wiki` em `[project.scripts]` |

---

### Task 1: O manual, e o que sai do README

**Files:**
- Create: `docs/plantao/{README,01-primeiro-dia,02-instalacao,03-runbook,04-decisoes,05-quando-da-errado}.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: nada.
- Produces: `docs/plantao/`, que a Tarefa 2 afere e a Tarefa 3 publica. O índice em `docs/plantao/README.md` lista as cinco páginas na ordem numérica.

- [ ] **Step 1: Mover, sem reescrever**

Mapa exato, com as linhas do README de hoje. Cada seção vai inteira, mudando só o nível de cabeçalho e as referências cruzadas que apontavam para outra seção do README.

| README (linhas) | Destino |
|---|---|
| `## Estrutura` (16–59) | fica |
| `## Configuração inicial (uma vez)` (60–86) | `02-instalacao.md` |
| `### As etapas de IA` (87–103) | dividida: o parágrafo de `--web` e `--modelo` vai para `03-runbook.md`, junto do Passo 2; a troca de backend por `modelo.py` fica no README |
| `### A janela e o dry run` (104–130) | `01-primeiro-dia.md` |
| `### O Project do Claude` (131–147) | `02-instalacao.md`, como caminho alternativo |
| `### Os exemplos` (148–160) | fica — trata de promover exemplo ao guia, que é manutenção |
| `## Runbook do plantão` (161–167) e `### As duas formas de rodar` (168–203) | `01-primeiro-dia.md` |
| `### Passo 1` a `### Passo 9` (204–421) | `03-runbook.md` |
| `### Referência de fusos` (422–451) | `03-runbook.md`, ao lado do passo que a usa |
| `## Notas` (452–465) e `### A coluna ATUAL` (466–476) | ficam |

- [ ] **Step 2: Escrever as três páginas novas**

**`01-primeiro-dia.md`** — o que você produz e quem lê; quanto tempo leva; o que é seu decidir e o que o comando decide; as duas formas de rodar e como escolher; a janela e o dry run.

**`04-decisoes.md`** — os quatro pontos em que o processo depende do autor:

1. **A escolha de temas**, entre a triagem e a redação. O comando **recusa** fazê-la. A página precisa separar duas coisas que a interface junta: os **números** dizem quais temas entram, e isso é mecânico; a **ressalva dentro do marcador** é o que o autor acrescenta, e é onde o julgamento dele entra. Em 17/08 foi uma ressalva assim — "as moedas estão estáveis na sessão corrente" — que impediu o comentário de afirmar que o dólar caíra no dia, quando o painel mostrava o câmbio estável. Nenhuma escolha de números teria produzido aquilo.
2. **Os "pontos sob julgamento do autor"** que a revisão devolve, e como decidi-los.
3. **Quando uma divergência do `conferir` é intencional** e quando é acidente.
4. **Quando `--forcar` é legítimo**, e as três recusas que ele contorna de uma vez.

**`05-quando-da-errado.md`** — cada modo de falha com o sintoma exato que aparece na tela e a saída:

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

A linha do `conferir` leva o caso concreto de 17/08: quatro palavras sumiram do documento durante a edição manual, entre elas o `swap` de "mercados de swap", e o e-mail saiu com a frase quebrada porque a conferência rodou depois do envio.

- [ ] **Step 3: Encolher o README**

Ele passa a servir um leitor só. No topo, antes de qualquer outra coisa:

```markdown
> **Vai rodar o plantão?** O manual é [`docs/plantao/`](docs/plantao/) — instalação,
> os nove passos, o que é seu decidir e o que fazer quando algo quebra. Este arquivo
> descreve o repositório para quem mexe no código.
```

A seção de configuração vira duas linhas apontando para o manual: quem clona para desenvolver precisa do mesmo `uv sync` que o plantonista, e duas instruções de instalação divergiriam.

- [ ] **Step 4: Conferir que nada se perdeu**

Comparar a soma dos destinos com o README de antes:

```bash
git show HEAD:README.md > /tmp/antes.md
wc -l /tmp/antes.md README.md docs/plantao/*.md
```

Percorrer os cabeçalhos de `/tmp/antes.md` um a um e apontar, para cada um, onde ele está agora. Um cabeçalho sem destino é uma seção perdida.

- [ ] **Step 5: Comitar**

```bash
git add -A
git commit -m "Separa o manual do plantão do README, por leitor

O README servia dois leitores em 476 linhas: quem roda o plantão de
manhã e quem mexe no código. O runbook sozinho eram 282 delas.

O manual em docs/plantao/ recebe a instalação e os nove passos, e
ganha três páginas que não existiam — a orientação do primeiro dia, o
que é do autor decidir, e os modos de falha com o sintoma exato de
cada um, escritos a partir do que a operação de 17/08 expôs.

Nada foi duplicado: o que estava num lugar continua num lugar, muda
qual. E nada foi reescrito além do necessário para fazer sentido no
destino — mover e reescrever no mesmo passo esconde o que mudou."
```

---

### Task 2: A rede de sincronia

**Files:**
- Create: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: `docs/plantao/` da Tarefa 1; `cli.SUBCOMANDOS`; `plantao.PASSOS`; `janela.ABERTURA`/`FECHAMENTO`; as constantes de caminho de `config.py`.
- Produces: nada que outro código use.

- [ ] **Step 1: Escrever o teste**

```python
"""A documentação e o código não podem divergir em silêncio.

Documentação envelhece sem avisar, e quem a lê não tem como saber que
envelheceu. O que dá para aferir por máquina — que comando existe, que passo
existe, que horas a janela tem, que pasta o código usa — é aferido aqui, na
suíte de sempre. O resto é prosa, e prosa é responsabilidade de quem escreve.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
MANUAL = RAIZ / "docs" / "plantao"
DOCUMENTOS = sorted(MANUAL.glob("*.md")) + [RAIZ / "README.md"]

# O guia entra na aferição da janela porque o modelo o lê em toda etapa: uma
# janela errada ali não confunde o leitor, confunde a triagem.
GUIA = RAIZ / "prompts" / "00_guia_de_estilo.md"

# Pares de horas que NÃO são a janela do plantão, com o motivo de cada um. Sem
# esta lista o teste ficaria vermelho num documento correto; com ela, cada par
# novo obriga alguém a dizer o que é.
HORAS_QUE_NAO_SAO_A_JANELA = {
    "3h e 6h": "releases europeus e britânicos, em hora de Nova York",
}

# Um intervalo de horas em qualquer das quatro redações que os documentos usam:
# "entre 7h00 e 9h00", "7h–9h", "7h00 às 9h00", "07h00 a 09h00".
RE_INTERVALO = re.compile(
    r"(\d{1,2})\s*h(?:\d{2})?\s*(?:às|as|até|a|e|–|-)\s*(\d{1,2})\s*h(?:\d{2})?",
    re.IGNORECASE,
)

# Caminho escrito entre crases: `saida/`, `arquivo/AAAA/MM/`, `config/painel.toml`.
RE_CAMINHO = re.compile(r"`([\w.-]+)/[\w./-]*`")

# O que parece pasta e é molde. Mesma ideia da lista de horas: sem ela o teste
# ficaria vermelho num documento correto, e com ela um molde novo obriga alguém
# a dizer que é molde.
CAMINHOS_QUE_SAO_MOLDE = {
    "AAAA": "molde de data em `arquivo/AAAA/MM/AAAAMMDD.md`",
}

# As bandeiras que o manual deliberadamente não ensina, com o motivo. Todas
# apontam para outro lugar as pastas que o plantão usa por padrão, e mexer nelas
# é ensaio ou teste — não é o plantão.
BANDEIRAS_FORA_DO_MANUAL = {
    "--saida": "as saídas do dia vão para `saida/`; apontar outra é reprocessar",
    "--fontes": "os PDFs da manhã ficam em `fontes/`, na raiz",
    "--arquivo": "o comentário do dia anterior sai de `arquivo/`, onde o "
                 "`enviado` o grava",
    "--config": "a lista de ativos do painel é única — `config/painel.toml`",
    "--template": "o documento sai do template da mesa; outro é ensaio de "
                  "formatação",
}


def _texto(caminhos) -> str:
    return "\n".join(c.read_text(encoding="utf-8") for c in caminhos)


def test_todo_subcomando_do_terminal_esta_documentado():
    from comentario_matinal.cli import SUBCOMANDOS

    texto = _texto(DOCUMENTOS)
    faltando = sorted(c for c in SUBCOMANDOS if f"matinal {c}" not in texto)
    assert not faltando, (
        f"Os subcomandos {faltando} existem e a documentação não os menciona. "
        "Quem aprender o plantão por ela não saberá que existem."
    )


def test_todo_comando_documentado_existe():
    """O erro mais provável depois de uma mudança: a documentação segue mostrando
    o que já não há."""
    from comentario_matinal.cli import SUBCOMANDOS

    citados = set(re.findall(r"uv run matinal (\w+)", _texto(DOCUMENTOS)))
    fantasmas = sorted(citados - set(SUBCOMANDOS))
    assert not fantasmas, (
        f"A documentação manda rodar {fantasmas}, que não existe(m). "
        f"Os subcomandos são {list(SUBCOMANDOS)}."
    )


def test_o_manual_decide_sobre_toda_bandeira_do_comando(monkeypatch, capsys):
    """Bandeira nova obriga a decidir se o manual a ensina, ou por que não.

    O teste de subcomandos não alcança bandeira, e é por bandeira que passa uma
    parte do processo — `--temas-numeros` é como a decisão editorial entra no
    fluxo. Em 17/08 ela foi acrescentada e o runbook seguiu mandando escrever os
    temas à mão por uma hora, com o problema conhecido. Este teste é o que teria
    acusado.

    A lista sai do `--help`, e não da introspecção do argparse: é o que o autor
    de fato lê quando procura o que existe.
    """
    from comentario_matinal import cli

    monkeypatch.setattr("sys.argv", ["matinal", "--help"])
    with pytest.raises(SystemExit):
        cli.main()

    bandeiras = set(re.findall(r"--[a-z][a-z-]+", capsys.readouterr().out))
    texto = _texto(DOCUMENTOS)
    faltando = sorted(b for b in bandeiras - {"--help"}
                      if b not in BANDEIRAS_FORA_DO_MANUAL and b not in texto)
    assert not faltando, (
        f"As bandeiras {faltando} existem e o manual não as menciona. Se alguma "
        "não for para o plantonista, ela entra em BANDEIRAS_FORA_DO_MANUAL com o "
        "motivo escrito ao lado."
    )


def test_a_janela_citada_na_prosa_bate_com_o_codigo():
    """Ela aparece escrita de quatro formas diferentes, e nenhuma é a do código.

    Por isso o teste afere as HORAS, e não a redação: obrigar uma única forma
    endureceria a prosa sem ganho algum. Muda-se `janela.ABERTURA` e toda menção
    fica vermelha, qualquer que seja como foi escrita.
    """
    from comentario_matinal.janela import ABERTURA, FECHAMENTO

    esperado = (ABERTURA.hour, FECHAMENTO.hour)
    erradas = []
    for caminho in [*DOCUMENTOS, GUIA]:
        for numero, linha in enumerate(
                caminho.read_text(encoding="utf-8").splitlines(), 1):
            for m in RE_INTERVALO.finditer(linha):
                if m.group(0) in HORAS_QUE_NAO_SAO_A_JANELA:
                    continue
                if (int(m.group(1)), int(m.group(2))) != esperado:
                    erradas.append(f"{caminho.name}:{numero} {m.group(0)!r}")

    assert not erradas, (
        f"A janela do código é {esperado[0]}h–{esperado[1]}h e a prosa diz outra "
        f"coisa em: {erradas}. Se algum desses não for a janela, ele entra em "
        "HORAS_QUE_NAO_SAO_A_JANELA com o motivo."
    )


def test_toda_pasta_citada_existe():
    """Documentação que nomeia pasta inexistente manda o leitor ao lugar errado,
    e ele não tem como saber que o errado é o texto."""
    reais = {p.name for p in RAIZ.iterdir() if p.is_dir()}
    citadas = set(RE_CAMINHO.findall(_texto(DOCUMENTOS)))
    inventadas = sorted(c for c in citadas
                        if c not in reais and c not in CAMINHOS_QUE_SAO_MOLDE)
    assert not inventadas, (
        f"A documentação cita {inventadas}, que não existe(m) na raiz do "
        "repositório. Se algum for molde, e não pasta, ele entra em "
        "CAMINHOS_QUE_SAO_MOLDE com o motivo."
    )


def test_o_readme_aponta_para_o_manual():
    """O README é a porta do repositório; o runbook saiu dele."""
    assert "docs/plantao/" in (RAIZ / "README.md").read_text(encoding="utf-8"), (
        "O README não aponta para o manual, e quem chega pelo repositório não "
        "acha o runbook."
    )
```

- [ ] **Step 2: Rodar e ver passar**

Run: `uv run pytest tests/test_documentacao.py -q`
Expected: `6 passed`

Falhando, **a documentação é que está errada** — corrigi-la, e não o teste. A única exceção é `HORAS_QUE_NAO_SAO_A_JANELA`: um par novo que legitimamente não seja a janela entra ali, com o motivo escrito ao lado.

- [ ] **Step 3: Provar que cada um pega o que promete**

Um a um, restaurando entre eles. Nenhum vale nada sem isto: seis testes que nunca foram vistos vermelhos são seis testes que ninguém sabe se funcionam.

1. Acrescentar `"exportar"` a `cli.SUBCOMANDOS` → o primeiro fica vermelho nomeando-o.
2. Escrever `uv run matinal publicar` numa página do manual → o segundo fica vermelho.
3. Acrescentar uma bandeira `--nova` ao `argparse` → o terceiro fica vermelho nomeando-a.
4. Trocar `janela.ABERTURA` para `time(6, 0)` → o quarto fica vermelho, listando **todas** as menções em prosa, no README, no manual e no guia.
5. Escrever `` `saidas/` `` numa página → o quinto fica vermelho.
6. Apagar a linha do link no README → o sexto fica vermelho.

- [ ] **Step 4: Comitar**

```bash
git add tests/test_documentacao.py
git commit -m "Prende por teste a parte da documentação que o código decide

Documentação envelhece sem avisar, e quem a lê não tem como saber que
envelheceu. Hoje mesmo, entre acrescentar --temas-numeros e perceber
que o runbook seguia mandando escrever os temas à mão, passou uma hora
— sabendo do problema.

O que dá para aferir por máquina passa a ser aferido: que comando
existe, que passo existe, que horas a janela tem, que pasta o código
usa. O resto é prosa, e prosa continua sendo de quem escreve.

O teste da janela afere as horas e não a redação. Ela aparece escrita
de quatro formas diferentes, e nenhuma delas é a do código; exigir uma
só endureceria a prosa sem ganho. Pares de horas que não são a janela
— como os releases europeus, entre 3h e 6h de Nova York — entram numa
lista com o motivo, para que um par novo obrigue alguém a decidir o
que ele é."
```

---

### Task 3: O publicador

**Files:**
- Create: `src/comentario_matinal/wiki.py`
- Modify: `pyproject.toml`
- Modify: `docs/plantao/02-instalacao.md`

**Interfaces:**
- Consumes: `docs/plantao/*.md` da Tarefa 1.
- Produces: `uv run publica-wiki`.

- [ ] **Step 1: O módulo**

`src/comentario_matinal/wiki.py`, com `main()` ligado a `publica-wiki` em `[project.scripts]`, ao lado do `matinal`.

**Fora do `matinal` de propósito.** Publicar documentação não é passo do plantão, e um `matinal wiki` entraria em `SUBCOMANDOS` — onde o teste de sincronia do notebook passaria a cobrar uma célula para ele, ou uma exceção registrada. A fronteira de `SUBCOMANDOS` é "os passos do plantão", e vale preservá-la.

Esqueleto:

```python
"""Publica o manual do plantão no Wiki do GitHub.

A fonte é `docs/plantao/`, que a suíte afere. O que sai daqui é cópia, e cada
página diz isso e de qual commit veio: não há como aferir por teste uma cópia
que mora noutro repositório git, então a honestidade fica no próprio texto,
onde o leitor a encontra sem procurar.
"""

MANUAL = RAIZ / "docs" / "plantao"

FAIXA = (
    "> Gerado a partir de `docs/plantao/{origem}` no commit `{sha}`.\n"
    "> Não editar aqui — a edição se perde na próxima publicação.\n\n"
)

# `01-primeiro-dia.md` vira `Primeiro-dia.md`; o índice vira a capa do wiki.
def _nome_no_wiki(caminho: Path) -> str:
    if caminho.name == "README.md":
        return "Home.md"
    miolo = caminho.stem.split("-", 1)[1]
    return miolo.capitalize().replace("-", "-") + ".md"


def _sha() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, check=True,
                          cwd=RAIZ).stdout.decode().strip()


def monta(destino: Path, sha: str) -> list[Path]:
    """Escreve as páginas no clone do wiki e devolve o que gravou."""


def main() -> int:
    """Clona ou atualiza o wiki, monta as páginas, comita e empurra.

    `--sem-push` para quando quiser conferir antes: monta, comita no clone e
    para, imprimindo o comando que falta.
    """
```

Os links entre páginas mudam de forma: no repositório são `02-instalacao.md`, no wiki são `Instalacao`. A conversão acontece na montagem, e um link que não corresponda a página alguma é erro, não aviso — no wiki ele viraria uma página vazia que o leitor cria sem querer ao clicar.

**O SHA é o que torna o envelhecimento visível.** Não há como aferir por teste uma cópia que mora noutro repositório git; a honestidade fica no próprio texto, onde o leitor a encontra sem procurar.

- [ ] **Step 2: A entrada no `pyproject.toml`**

```toml
[project.scripts]
matinal = "comentario_matinal.cli:main"
publica-wiki = "comentario_matinal.wiki:main"
```

Run: `uv sync`

- [ ] **Step 3: Testar sem empurrar**

O publicador precisa de um modo que monte tudo e pare antes do `push`, para que dê para conferir o resultado. Rodá-lo contra um repositório de wiki falso, criado com `git init --bare` num diretório temporário, e conferir que as páginas saíram com a faixa e o SHA certos.

**Não empurrar para o wiki de verdade.** Publicar é ato do autor.

- [ ] **Step 4: Documentar o passo manual único**

Em `02-instalacao.md`: o GitHub só cria `comentario_matinal.wiki.git` depois que a primeira página nasce pela interface web — antes disso o `git ls-remote` responde "Repository not found", verificado em 17/08. Abrir a aba Wiki, criar qualquer página, e a partir daí o publicador funciona.

- [ ] **Step 5: Comitar**

```bash
git add -A
git commit -m "Publicador do manual para o Wiki do GitHub

Fonte única em docs/plantao/, aferida por teste; a cópia no Wiki é
derivada e diz isso em cada página, com o SHA do commit de origem.
Não há como aferir por teste uma cópia que mora noutro repositório
git, então a honestidade fica no texto, onde o leitor a encontra sem
procurar.

Fora do comando `matinal` de propósito: publicar documentação não é
passo do plantão, e entraria em SUBCOMANDOS, onde o teste de sincronia
do notebook passaria a cobrar uma célula para ele."
```

---

## Verificação final

- [ ] `uv run pytest -q` verde — 136 de hoje mais os 6 novos
- [ ] Nenhum cabeçalho do README de antes ficou sem destino
- [ ] Os seis testes de documentação foram vistos vermelhos, um a um
- [ ] `uv run matinal --help` e `uv run publica-wiki --help` respondem
- [ ] O manual lido do começo ao fim por quem nunca viu o repositório: ele ensina o plantão, ou pressupõe que o leitor já o conhece?
