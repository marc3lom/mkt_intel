# Backend Copilot e branch empresarial — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer os notebooks do comentário matinal e do FOMC/payroll rodarem numa máquina do BC só com VS Code + GitHub Copilot Free, Python, uv, git e GitHub, e gerar o branch órfão `empresarial` que vai ao GitHub do BC.

**Architecture:** Um backend novo, `copilot`, entra no registro de backends dos dois pacotes (`comentario_matinal/modelo.py` e a cópia `reports/_modelo.py`): grava a mensagem da etapa num arquivo, espera o agente do Copilot — disparado por um prompt file de `.github/prompts/` — gravar a resposta, e confere um código de leitura. O backend Claude sai para um módulo descoberto por prefixo (`_backend_*.py`), para que nada que vá ao branch o mencione. Um script regenera o branch órfão a partir da `main`, nos moldes do `py-mpc`.

**Tech Stack:** Python ≥3.14, uv, pytest, python-docx, pypdf, nbformat, git (plumbing: `ls-tree`, `update-index`, `commit-tree`, `bundle`), prompt files do VS Code.

**Spec:** `docs/superpowers/specs/2026-09-29-copilot-e-branch-empresarial-design.md`

## Ajustes em relação à spec

Descobertos ao ler o código; nenhum muda o que foi aprovado, só como se faz.

1. **`_claude.py` vira `_backend_claude.py`, descoberto por prefixo.** Um `import comentario_matinal._claude` em `modelo.py` poria a palavra no arquivo que vai ao branch. O registro importa todo módulo do pacote cujo nome começa por `_backend_` e lê o atributo `BACKEND`. A detecção "`claude` no PATH" também vai para lá, como `ClaudeCode.disponivel()`.
2. **Prompt files com prefixo de produto.** `revisao` existe nos dois produtos; os comandos são `/matinal-triagem`, `/matinal-redacao`, `/matinal-revisao`, `/fomc-resumo`, `/fomc-bancos`, `/fomc-revisao`. As etapas do FOMC são as que o `drafting.py` passa ao backend: `resumo`, `bancos`, `revisao`.
3. **O `SYSTEM_PROMPT` vai dentro do arquivo de mensagem.** Assim as regras de execução têm uma fonte só, e os prompt files ficam pura mecânica.
4. **`reports._paths.ENV_FILE` não existe hoje** — o `test_paths.py` afirma a ausência. Ele nasce, apontando para `etc/.env`, e o teste muda.
5. **O template do FOMC perde também as imagens órfãs.** Esvaziar o corpo não tira do pacote as imagens do informe de origem; o script de geração derruba as relações de imagem do corpo, e um teste confere que toda mídia restante é do cabeçalho ou do rodapé.

## Global Constraints

- Só uv; nunca `pip install`. Python ≥3.14. Nenhuma dependência nova; `onepassword-sdk` sai.
- `comentario_matinal`: identificadores, mensagens e comentários em português. `reports`: identificadores, mensagens de log e de erro em inglês; docstrings e comentários em pt-BR.
- Um pacote não importa o outro (`tests/informes_eventos/test_independence.py`). Código igual nos dois é cópia.
- Caminho só se acha em `comentario_matinal/config.py` e `reports/_paths.py`.
- Nenhum arquivo que vai ao branch pode conter "claude" (sem distinção de caixa): `src/` exceto `_backend_claude.py` e `wiki.py`; `notebooks/` exceto `comentario_matinal/plantao.ipynb`; `prompts/` exceto `project_instructions.md`; `templates/`, `config/`, `.github/prompts/`, `etc/`, `README_empresarial.md`, `pyproject.toml`, `uv.lock`, `.gitattributes`, `.gitignore` (este tem as linhas do Claude retiradas pelo script).
- Pastas do Copilot: `output/comentario_matinal/copilot/` e `output/informes_eventos/copilot/`. Arquivos: `<etapa>.mensagem.md` e `<etapa>.resposta.md`.
- Linha de leitura: `<!-- leitura: <8 hex> -->`, gerada com `secrets.token_hex(4)`.
- Ferramentas dos prompt files, exatamente: `['read/readFile', 'edit/createFile', 'edit/editFiles']`. Nada de `execute/*` nem `web/*`.
- Espera pela resposta: teto `TEMPO_LIMITE`/`TIMEOUT` = 900 s (os valores atuais).
- Chave do FRED: variável `FRED_API_KEY`, senão `etc/.env`. `etc/.env.exemplo` versionado.
- Portão: `uv run pytest`, na raiz. Nunca verificar rodando `uv run matinal`.
- Sigilo: nunca ler, imprimir ou resumir `input/`, `output/`, `.env`, `etc/.env`.
- Commit: direto na `main`, **só com autorização do usuário**; mensagem em português, terceira pessoa do presente, ≤72 caracteres, sem prefixo nem ponto final, corpo em prosa; trailers `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e `Claude-Session: <id da sessão>`. Nunca empurrar sem pedido.
- `docs/comentario_matinal/AGENTS.md` (linha da tabela "Verificar") e `docs/comentario_matinal/CLAUDE.md` anunciam a contagem de testes de `tests/comentario_matinal`, e `test_documentacao.py` cobra. Toda tarefa que muda essa contagem atualiza os dois.

## Review Focus

1. **O agente grava a resposta em dois passos** — o backend não pode ler a primeira metade. Teste de gravação parcial na Task 2 (e cópia na Task 3).
2. **Resposta velha de uma execução anterior** na pasta do Copilot — tem de ser apagada antes da espera, senão a etapa devolve a resposta de ontem. Teste na Task 2 e na Task 3.
3. **Resposta gravada com BOM** (o VS Code e o Bloco de Notas podem gravar UTF-8 com BOM) — a linha de leitura continua sendo reconhecida. Teste na Task 2.
4. **`etc/.env` editado no Bloco de Notas** — com BOM, espaços em volta do `=` e valor entre aspas. Teste na Task 6.
5. **O PDF do dia anterior com outra caixa ou sufixo** (`Anterior_2026-09-28.PDF`) — tem de ser reconhecido e não pode ir para as fontes. Teste na Task 5.

---

### Task 1: O backend Claude do matinal em módulo próprio, e a escolha automática

**Files:**
- Create: `src/comentario_matinal/_backend_claude.py`
- Modify: `src/comentario_matinal/modelo.py` (inteiro)
- Modify: `src/comentario_matinal/cli.py:175-177` (ajuda do `--modelo`)
- Modify: `tests/comentario_matinal/test_modelo.py` (imports e alvos dos dublês)
- Modify: `docs/comentario_matinal/AGENTS.md` (§2, bullets do backend; tabela, contagem), `docs/comentario_matinal/CLAUDE.md` (contagem)

**Interfaces:**
- Produces: `modelo.BACKENDS: dict[str, type[Backend]]` (continua), `modelo.backend_ativo() -> Backend`, `modelo.padrao() -> str`, `modelo.SYSTEM_PROMPT`, `modelo.TEMPO_LIMITE`, `modelo.ErroDoModelo`, `modelo.SEPARADOR`; `_backend_claude.ClaudeCode` com `nome = "claude-code"`, `executa(...)` e `@staticmethod disponivel() -> bool`; `_backend_claude.BACKEND = ClaudeCode`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `tests/comentario_matinal/test_modelo.py`:

```python
# --- escolha do backend -------------------------------------------------------


def _desliga_opcionais(monkeypatch, disponivel: bool):
    """Faz todo backend opcional responder `disponivel()` como pedido."""
    for classe in modelo.BACKENDS.values():
        if hasattr(classe, "disponivel"):
            monkeypatch.setattr(classe, "disponivel", staticmethod(lambda: disponivel))


def test_sem_variavel_e_com_backend_local_ele_e_o_padrao(monkeypatch):
    """Na máquina que tem a CLI, nada muda: o padrão continua sendo ela."""
    monkeypatch.delenv("COMENTARIO_MATINAL_BACKEND", raising=False)
    _desliga_opcionais(monkeypatch, True)
    assert modelo.backend_ativo().nome == "claude-code"


def test_sem_variavel_e_sem_backend_local_vale_o_copilot(monkeypatch):
    """Na máquina do BC não há CLI alguma, e ninguém precisa configurar nada."""
    monkeypatch.delenv("COMENTARIO_MATINAL_BACKEND", raising=False)
    _desliga_opcionais(monkeypatch, False)
    assert modelo.padrao() == "copilot"


def test_a_variavel_vence_a_deteccao(monkeypatch):
    monkeypatch.setenv("COMENTARIO_MATINAL_BACKEND", "copilot")
    _desliga_opcionais(monkeypatch, True)
    assert modelo.backend_ativo().nome == "copilot"


def test_o_registro_nao_cita_backend_opcional_pelo_nome():
    """O `modelo.py` vai ao branch empresarial, que não pode mencionar o backend local."""
    from pathlib import Path

    texto = Path(modelo.__file__).read_text(encoding="utf-8").lower()
    assert "claude" not in texto
```

E trocar, no topo do arquivo, `from comentario_matinal import modelo` por:

```python
from comentario_matinal import _backend_claude as backend
from comentario_matinal import modelo
```

Nos testes já existentes do arquivo, substituir `modelo.ClaudeCode` por `backend.ClaudeCode`, `modelo.shutil` por `backend.shutil` e `modelo.subprocess` por `backend.subprocess` (as ocorrências estão no fixture `chamada`, em `executa()` e em `test_a_falha_diz_o_motivo_ainda_que_ele_saia_pelo_stdout`). `modelo.ErroDoModelo` continua como está.

`test_a_variavel_vence_a_deteccao` precisa do `Copilot` registrado, que só nasce na Task 2; nesta tarefa ele fica marcado (o `padrao()` já devolve `"copilot"` sem registro algum, então o outro teste passa desde já):

```python
@pytest.mark.xfail(reason="o backend copilot nasce na Task 2", strict=True)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/comentario_matinal/test_modelo.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'comentario_matinal._backend_claude'`.

- [ ] **Step 3: Criar `src/comentario_matinal/_backend_claude.py`**

Mover para cá, do `modelo.py`, a classe `ClaudeCode`, `FERRAMENTAS_BLOQUEADAS`, `FERRAMENTAS_WEB` e os comentários que as acompanham — sem mudar uma linha da lógica. O arquivo fica:

```python
"""O backend local: a CLI do Claude Code em modo não interativo.

Módulo próprio, e não classe dentro do `modelo.py`, porque o registro de lá
descobre backends opcionais pelo prefixo `_backend_` do nome do módulo. Assim o
`modelo.py` não cita este backend, e uma cópia do repositório sem este arquivo
continua funcionando com os demais.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from comentario_matinal.modelo import SYSTEM_PROMPT, TEMPO_LIMITE, ErroDoModelo

# Sem ferramenta alguma por padrão. Tudo o que a etapa precisa vai injetado na
# mensagem, então acesso a arquivo só acrescentaria não-determinismo — e, no caso
# da web, o risco de o modelo introduzir tema que não está nas fontes do dia.
FERRAMENTAS_BLOQUEADAS = [
    "Bash", "Read", "Write", "Edit", "NotebookEdit", "Glob", "Grep",
    "Task", "WebSearch", "WebFetch",
]
FERRAMENTAS_WEB = ["WebSearch", "WebFetch"]


class ClaudeCode:
    """Backend local: o Claude Code em modo não interativo."""

    nome = "claude-code"

    @staticmethod
    def disponivel() -> bool:
        """Há CLI nesta máquina? É o que decide o padrão, sem variável de ambiente."""
        return shutil.which("claude") is not None

    # (corpo de `executa` idêntico ao atual, com todos os comentários: o
    # --safe-mode, o --model opcional, a retirada da ANTHROPIC_API_KEY, o motivo
    # lido do stdout)


BACKEND = ClaudeCode
```

O comentário que hoje fica acima do `SYSTEM_PROMPT` em `modelo.py` ("A CLI do Claude Code roda por padrão como agente…") vem para cá, acima da classe, porque é o motivo de *este* backend passar `--system-prompt`.

- [ ] **Step 4: Reescrever `src/comentario_matinal/modelo.py`**

```python
"""A chamada ao modelo, atrás de uma função única.

Todo o fluxo das etapas passa por ``executa``. Trocar de backend é escrever
outra classe e registrá-la; nem a montagem das mensagens nem o encadeamento
entre etapas mudam.

Backends opcionais moram em módulos ``_backend_*.py`` deste pacote, cada um com
um atributo ``BACKEND``, e são registrados na importação. Um backend opcional
que responde ``disponivel()`` verdadeiro vira o padrão; sem nenhum, o padrão é
o que não depende de programa algum instalado.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import sys
from typing import Protocol

# As etapas mandam mensagens longas: só o guia de estilo passa de 15 KB, e as
# fontes do dia costumam ser bem maiores.
TEMPO_LIMITE = 900

SEPARADOR = "\n\n" + "=" * 70 + "\n\n"

# As regras de uma execução automatizada. Valem para todo backend: o que roda
# um programa as passa como papel do sistema; o que conversa por arquivo as põe
# no topo do arquivo.
SYSTEM_PROMPT = """..."""  # texto atual, sem mudança

ENV_BACKEND = "COMENTARIO_MATINAL_BACKEND"


class ErroDoModelo(RuntimeError):
    """Falha na chamada ao backend."""


class Backend(Protocol):
    nome: str

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str: ...


BACKENDS: dict[str, type[Backend]] = {}


def _registra_opcionais() -> None:
    """Importa cada ``_backend_*.py`` do pacote e registra o ``BACKEND`` dele."""
    import comentario_matinal

    for info in pkgutil.iter_modules(comentario_matinal.__path__):
        if info.name.startswith("_backend_"):
            modulo = importlib.import_module(f"comentario_matinal.{info.name}")
            BACKENDS.setdefault(modulo.BACKEND.nome, modulo.BACKEND)


def padrao() -> str:
    """O backend sem variável de ambiente: o opcional disponível, senão o copilot."""
    for nome, classe in BACKENDS.items():
        disponivel = getattr(classe, "disponivel", None)
        if disponivel is not None and disponivel():
            return nome
    return "copilot"


def backend_ativo() -> Backend:
    nome = os.environ.get(ENV_BACKEND) or padrao()
    if nome not in BACKENDS:
        raise ErroDoModelo(
            f"Backend desconhecido: {nome!r}. Disponíveis: "
            f"{', '.join(sorted(BACKENDS))}."
        )
    return BACKENDS[nome]()


def executa(mensagem: str, *, etapa: str, web: bool = False,
            modelo: str | None = None) -> str:
    """Manda a mensagem ao modelo e devolve a resposta em texto."""
    b = backend_ativo()
    print(f"Chamando o modelo ({b.nome}) para a etapa {etapa}. "
          f"Mensagem com {len(mensagem):,} caracteres"
          f"{', com web' if web else ''}...", file=sys.stderr)
    return b.executa(mensagem, etapa=etapa, web=web, modelo=modelo)


_registra_opcionais()
```

O `_registra_opcionais()` fica na última linha de propósito: o `_backend_claude` importa `SYSTEM_PROMPT`, `TEMPO_LIMITE` e `ErroDoModelo` daqui, e eles já existem quando a importação circular acontece. O `SYSTEM_PROMPT` mantém o texto atual, que não cita nenhum backend.

- [ ] **Step 5: Ajuda do `--modelo` em `cli.py`**

Trocar `"configuração da CLI do Claude Code."` por `"configuração do backend."` (linha 177).

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run pytest tests/comentario_matinal/test_modelo.py -q`
Expected: PASS, com 1 xfail.

- [ ] **Step 7: Documentação e contagem**

Em `docs/comentario_matinal/AGENTS.md` §2, trocar os dois bullets "A única variável de ambiente…" e "A autenticação do backend…" por:

```markdown
- A única variável de ambiente que o código lê é `COMENTARIO_MATINAL_BACKEND`. Sem ela, vale o backend local (`claude-code`) se o executável `claude` estiver no PATH, e o `copilot` se não estiver. O backend local mora em `src/comentario_matinal/_backend_claude.py`, descoberto pelo prefixo `_backend_`; o `modelo.py` não o cita, porque vai ao branch empresarial.
- **A autenticação do backend local é a sessão do Claude Code**, não chave de API. O `_backend_claude.py` roda o `claude` com `--safe-mode` — que desliga CLAUDE.md, hooks, skills, plugins, MCP e agentes do ambiente de quem está de plantão, para a etapa render o mesmo em qualquer máquina — e retira `ANTHROPIC_API_KEY` do ambiente do subprocesso, porque uma chave esquecida ali tem precedência e uma chave sem saldo derruba a etapa com código 1.
```

Run: `uv run pytest tests/comentario_matinal -q` e anotar o total N de testes coletados (passados + xfail). Substituir `186 testes` por `N testes` em `docs/comentario_matinal/AGENTS.md` e `docs/comentario_matinal/CLAUDE.md`.

- [ ] **Step 8: Portão e commit**

Run: `uv run pytest -q` — Expected: tudo verde (xfail contam como verde).

```bash
git add src/comentario_matinal/_backend_claude.py src/comentario_matinal/modelo.py src/comentario_matinal/cli.py tests/comentario_matinal/test_modelo.py docs/comentario_matinal/AGENTS.md docs/comentario_matinal/CLAUDE.md
git commit   # "Separa o backend local do registro de backends do matinal"
```

---

### Task 2: O backend `copilot` do matinal

**Files:**
- Modify: `src/comentario_matinal/modelo.py` (acrescentar a seção do Copilot antes de `_registra_opcionais()`)
- Create: `tests/comentario_matinal/test_copilot.py`
- Modify: `tests/comentario_matinal/test_modelo.py` (retirar os dois `xfail`)
- Modify: `docs/comentario_matinal/AGENTS.md`, `docs/comentario_matinal/CLAUDE.md` (contagem)

**Interfaces:**
- Consumes: `modelo.SYSTEM_PROMPT`, `modelo.SEPARADOR`, `modelo.TEMPO_LIMITE`, `modelo.ErroDoModelo`, `modelo.BACKENDS` (Task 1); `config.SAIDA_PADRAO`.
- Produces: `modelo.Copilot` (`nome = "copilot"`), `modelo.PASTA_COPILOT: Path`, `modelo.INTERVALO: float`, `modelo.ESTAVEL: float`, `modelo.COMANDO = "matinal"`, `modelo.mensagem_para_o_copilot(mensagem: str, codigo: str) -> str`, `modelo.tira_codigo(resposta: str, codigo: str, etapa: str) -> str`, `modelo.espera_resposta(caminho: Path, etapa: str) -> str`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/comentario_matinal/test_copilot.py`:

```python
"""O backend que conversa com o Copilot do VS Code por arquivo.

Nenhum Copilot de verdade aqui: uma thread faz o papel do agente — espera o
arquivo de mensagem aparecer, lê o código de leitura e grava a resposta.
"""

from __future__ import annotations

import re
import threading
import time

import pytest

from comentario_matinal import modelo

RE_CODIGO = re.compile(r"<!-- leitura: ([0-9a-f]+) -->")


@pytest.fixture
def pasta(monkeypatch, tmp_path):
    destino = tmp_path / "copilot"
    monkeypatch.setattr(modelo, "PASTA_COPILOT", destino)
    monkeypatch.setattr(modelo, "INTERVALO", 0.01)
    monkeypatch.setattr(modelo, "ESTAVEL", 0.05)
    monkeypatch.setattr(modelo, "TEMPO_LIMITE", 5)
    return destino


def agente(pasta, etapa, *partes, codigo=None, pausa=0.0):
    """Faz o papel do Copilot: grava a resposta em uma ou mais partes."""
    def age():
        pedido = pasta / f"{etapa}.mensagem.md"
        while not pedido.exists():
            time.sleep(0.01)
        time.sleep(0.02)
        lido = RE_CODIGO.search(pedido.read_text(encoding="utf-8")).group(1)
        resposta = pasta / f"{etapa}.resposta.md"
        texto = f"<!-- leitura: {codigo or lido} -->\n"
        for parte in partes:
            texto += parte
            resposta.write_text(texto, encoding="utf-8")
            time.sleep(pausa)

    t = threading.Thread(target=age, daemon=True)
    t.start()
    return t


def executa(etapa="triagem", web=False, modelo_=None):
    return modelo.Copilot().executa("MENSAGEM DA ETAPA", etapa=etapa, web=web,
                                    modelo=modelo_)


def test_devolve_a_resposta_sem_a_linha_de_leitura(pasta):
    agente(pasta, "triagem", "## A) TEMAS\n\n| 1 | tema |\n")
    assert executa() == "## A) TEMAS\n\n| 1 | tema |"


def test_a_mensagem_leva_as_regras_o_pedido_e_o_codigo_no_fim(pasta):
    agente(pasta, "triagem", "ok")
    executa()
    texto = (pasta / "triagem.mensagem.md").read_text(encoding="utf-8")
    assert texto.startswith(modelo.SYSTEM_PROMPT)
    assert "MENSAGEM DA ETAPA" in texto
    # O código vai na última linha: só quem leu até o fim o conhece.
    assert RE_CODIGO.search(texto.rstrip().splitlines()[-1])


def test_codigo_de_outra_execucao_e_recusado(pasta):
    agente(pasta, "triagem", "ok", codigo="deadbeef")
    with pytest.raises(modelo.ErroDoModelo, match="outra execução"):
        executa()


def test_resposta_sem_linha_de_leitura_diz_que_a_mensagem_nao_foi_lida(pasta):
    def age():
        while not (pasta / "triagem.mensagem.md").exists():
            time.sleep(0.01)
        (pasta / "triagem.resposta.md").write_text("só a resposta", encoding="utf-8")

    threading.Thread(target=age, daemon=True).start()
    with pytest.raises(modelo.ErroDoModelo, match="até o fim"):
        executa()


def test_resposta_vazia_e_erro(pasta):
    agente(pasta, "triagem", "   \n")
    with pytest.raises(modelo.ErroDoModelo, match="vazia"):
        executa()


def test_gravacao_em_duas_partes_nao_e_lida_pela_metade(pasta):
    """O agente pode gravar em mais de um passo; ler no meio entregaria metade."""
    agente(pasta, "redacao", "- primeiro marcador\n", "- segundo marcador\n",
           pausa=0.02)
    assert executa("redacao") == "- primeiro marcador\n- segundo marcador"


def test_resposta_velha_e_apagada_antes_da_espera(pasta):
    """A resposta de ontem na pasta não pode passar pela de hoje."""
    pasta.mkdir(parents=True)
    (pasta / "triagem.resposta.md").write_text(
        "<!-- leitura: 00000000 -->\nvelha", encoding="utf-8")
    agente(pasta, "triagem", "nova")
    assert executa() == "nova"


def test_resposta_com_bom_e_aceita(pasta):
    def age():
        pedido = pasta / "triagem.mensagem.md"
        while not pedido.exists():
            time.sleep(0.01)
        time.sleep(0.02)
        lido = RE_CODIGO.search(pedido.read_text(encoding="utf-8")).group(1)
        (pasta / "triagem.resposta.md").write_text(
            f"\ufeff<!-- leitura: {lido} -->\ncom BOM", encoding="utf-8")

    threading.Thread(target=age, daemon=True).start()
    assert executa() == "com BOM"


def test_sem_resposta_no_prazo_e_erro(pasta, monkeypatch):
    monkeypatch.setattr(modelo, "TEMPO_LIMITE", 0.2)
    with pytest.raises(modelo.ErroDoModelo, match="/matinal-triagem"):
        executa()


def test_web_e_recusada(pasta):
    with pytest.raises(modelo.ErroDoModelo, match="web"):
        executa(web=True)


def test_o_pedido_ensina_o_comando(pasta, capsys):
    agente(pasta, "revisao", "ok")
    executa("revisao")
    assert "/matinal-revisao" in capsys.readouterr().err


def test_o_copilot_esta_registrado():
    assert modelo.BACKENDS["copilot"] is modelo.Copilot
```

Em `tests/comentario_matinal/test_modelo.py`, retirar o `@pytest.mark.xfail(...)` da Task 1.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/comentario_matinal/test_copilot.py -q`
Expected: FAIL — `AttributeError: module 'comentario_matinal.modelo' has no attribute 'PASTA_COPILOT'`.

- [ ] **Step 3: Implementar em `modelo.py`**

Acrescentar aos imports: `import re`, `import secrets`, `import time`, `from pathlib import Path`, `from comentario_matinal.config import SAIDA_PADRAO`. Antes de `_registra_opcionais()`:

```python
# --------------------------------------------------------------------------
# Copilot: a conversa é por arquivo
# --------------------------------------------------------------------------

# Pasta fixa porque os prompt files de `.github/prompts/` a citam por caminho: o
# agente do Copilot não recebe argumento, lê e grava onde o prompt manda.
PASTA_COPILOT = SAIDA_PADRAO / "copilot"
COMANDO = "matinal"

# Olhar o arquivo a cada segundo, e só aceitá-lo depois de dois segundos sem
# mudar de tamanho: o agente pode gravar a resposta em mais de um passo, e ler
# no meio entregaria metade dela à etapa seguinte.
INTERVALO = 1.0
ESTAVEL = 2.0

RE_LEITURA = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")


def mensagem_para_o_copilot(mensagem: str, codigo: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e, no fim, o código.

    O código vai na última linha de propósito. O arquivo é longo, o agente o lê
    em trechos, e só quem chegou ao fim sabe qual código devolver — é a prova
    de que as fontes do dia foram lidas inteiras, e não só o começo.
    """
    return (
        SYSTEM_PROMPT + SEPARADOR + mensagem.rstrip() + SEPARADOR
        + "## FIM DA MENSAGEM\n\n"
        "A primeira linha do arquivo de resposta é exatamente "
        f"`<!-- leitura: {codigo} -->`; a saída pedida começa na linha "
        "seguinte.\n"
    )


def tira_codigo(resposta: str, codigo: str, etapa: str) -> str:
    """Confere o código de leitura e o tira da resposta."""
    texto = resposta.lstrip("\ufeff")
    achado = RE_LEITURA.search(texto[:500])
    if achado is None:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} não traz a linha de leitura: a "
            "mensagem não foi lida até o fim. Rodar a célula de novo e, no "
            "chat, repetir o comando."
        )
    if achado.group(1) != codigo:
        raise ErroDoModelo(
            f"A resposta da etapa {etapa} traz o código de outra execução. "
            "Rodar a célula de novo e repetir o comando no chat."
        )
    corpo = (texto[:achado.start()] + texto[achado.end():]).strip()
    if not corpo:
        raise ErroDoModelo(f"A etapa {etapa} devolveu resposta vazia.")
    return corpo


def espera_resposta(caminho: Path, etapa: str) -> str:
    """Espera o arquivo de resposta aparecer e parar de crescer."""
    limite = time.monotonic() + TEMPO_LIMITE
    tamanho, desde = -1, 0.0
    while time.monotonic() < limite:
        if caminho.is_file():
            atual = caminho.stat().st_size
            if atual > 0 and atual == tamanho:
                if time.monotonic() - desde >= ESTAVEL:
                    return caminho.read_text(encoding="utf-8")
            else:
                tamanho, desde = atual, time.monotonic()
        time.sleep(INTERVALO)
    raise ErroDoModelo(
        f"Nenhuma resposta da etapa {etapa} em {TEMPO_LIMITE}s. No chat do "
        f"Copilot, em modo agente, o comando é /{COMANDO}-{etapa}."
    )


class Copilot:
    """O GitHub Copilot do VS Code, pelo chat em modo agente.

    Não há programa a chamar: a mensagem vai para um arquivo, a pessoa roda o
    comando da etapa no chat, e o agente grava a resposta noutro. A célula fica
    esperando enquanto isso — interromper o kernel cancela a espera.
    """

    nome = "copilot"

    def executa(self, mensagem: str, *, etapa: str, web: bool,
                modelo: str | None) -> str:
        if web:
            raise ErroDoModelo(
                "O backend copilot não libera a web: o prompt file da etapa só "
                "lê e grava arquivos. Rodar a etapa com web=False."
            )
        PASTA_COPILOT.mkdir(parents=True, exist_ok=True)
        pedido = PASTA_COPILOT / f"{etapa}.mensagem.md"
        resposta = PASTA_COPILOT / f"{etapa}.resposta.md"
        # A de uma execução anterior passaria pela de agora.
        resposta.unlink(missing_ok=True)

        codigo = secrets.token_hex(4)
        pedido.write_text(mensagem_para_o_copilot(mensagem, codigo),
                          encoding="utf-8")
        if modelo:
            print(f"Aviso: o modelo {modelo!r} não se escolhe daqui; vale o "
                  "escolhido no chat do Copilot.", file=sys.stderr)
        print(f"\nNo chat do Copilot (Ctrl+Alt+I), em modo agente, digite "
              f"/{COMANDO}-{etapa} e espere. A resposta chega em {resposta}.",
              file=sys.stderr, flush=True)

        return tira_codigo(espera_resposta(resposta, etapa), codigo, etapa)


BACKENDS["copilot"] = Copilot
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/comentario_matinal/test_copilot.py tests/comentario_matinal/test_modelo.py -q`
Expected: PASS, sem xfail.

- [ ] **Step 5: Contagem, portão e commit**

Atualizar a contagem de `tests/comentario_matinal` nos dois documentos (ver Global Constraints). Run: `uv run pytest -q` — verde.

```bash
git add src/comentario_matinal/modelo.py tests/comentario_matinal/test_copilot.py tests/comentario_matinal/test_modelo.py docs/comentario_matinal/AGENTS.md docs/comentario_matinal/CLAUDE.md
git commit   # "Acrescenta o backend copilot, que conversa por arquivo"
```

---

### Task 3: O mesmo no `reports`: backend local em módulo próprio e backend `copilot`

**Files:**
- Create: `src/reports/_backend_claude.py`
- Modify: `src/reports/_modelo.py`
- Modify: `tests/informes_eventos/test_modelo.py`
- Create: `tests/informes_eventos/test_copilot.py`
- Modify: `docs/informes_eventos/AGENTS.md` (seção "Etapas de modelo do FOMC")

**Interfaces:**
- Consumes: `reports._paths.OUTPUT`.
- Produces: `_modelo.BACKENDS`, `_modelo.active_backend()`, `_modelo.default_backend() -> str`, `_modelo.SYSTEM_PROMPT`, `_modelo.TIMEOUT`, `_modelo.ModelError`, `_modelo.MISSING_INPUT_MARK`, `_modelo.SEPARATOR`, `_modelo.Copilot` (`name = "copilot"`), `_modelo.COPILOT_DIR`, `_modelo.POLL_INTERVAL`, `_modelo.STABLE_FOR`, `_modelo.COMMAND = "fomc"`, `_modelo.copilot_message(message, code)`, `_modelo.strip_read_mark(response, code, stage)`, `_modelo.wait_for_response(path, stage)`; `reports._backend_claude.ClaudeCode` (`name = "claude-code"`, `run(...)`, `disponivel()` → aqui `available()`), `reports._backend_claude.BLOCKED_TOOLS`, `reports._backend_claude.BACKEND`.

- [ ] **Step 1: Testes que falham**

Em `tests/informes_eventos/test_modelo.py`:
- trocar o import por `from reports import _backend_claude, _modelo`;
- em `TestClaudeCode`, substituir `_modelo.ClaudeCode` → `_backend_claude.ClaudeCode`, `_modelo.shutil` → `_backend_claude.shutil`, `_modelo.subprocess` → `_backend_claude.subprocess`, `_modelo.BLOCKED_TOOLS` → `_backend_claude.BLOCKED_TOOLS` (o `_modelo.SYSTEM_PROMPT` e o `_modelo.TIMEOUT` ficam);
- substituir `test_default_is_claude_code` por:

```python
    def test_default_is_the_local_backend_when_available(self, monkeypatch):
        monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
        monkeypatch.setattr(_backend_claude.ClaudeCode, "available", staticmethod(lambda: True))
        assert _modelo.active_backend().name == "claude-code"

    def test_default_is_copilot_without_a_local_backend(self, monkeypatch):
        monkeypatch.delenv("INFORMES_EVENTOS_BACKEND", raising=False)
        monkeypatch.setattr(_backend_claude.ClaudeCode, "available", staticmethod(lambda: False))
        assert _modelo.default_backend() == "copilot"

    def test_registry_module_does_not_name_the_local_backend(self):
        from pathlib import Path

        assert "claude" not in Path(_modelo.__file__).read_text(encoding="utf-8").lower()
```

Criar `tests/informes_eventos/test_copilot.py`, espelho em inglês do da Task 2:

```python
"""O backend Copilot do `reports`: cópia do matinal, conversa por arquivo."""

from __future__ import annotations

import re
import threading
import time

import pytest

from reports import _modelo

READ = re.compile(r"<!-- leitura: ([0-9a-f]+) -->")


@pytest.fixture
def folder(monkeypatch, tmp_path):
    target = tmp_path / "copilot"
    monkeypatch.setattr(_modelo, "COPILOT_DIR", target)
    monkeypatch.setattr(_modelo, "POLL_INTERVAL", 0.01)
    monkeypatch.setattr(_modelo, "STABLE_FOR", 0.05)
    monkeypatch.setattr(_modelo, "TIMEOUT", 5)
    return target


def fake_agent(folder, stage, *parts, code=None, pause=0.0):
    def act():
        request = folder / f"{stage}.mensagem.md"
        while not request.exists():
            time.sleep(0.01)
        time.sleep(0.02)
        seen = READ.search(request.read_text(encoding="utf-8")).group(1)
        response = folder / f"{stage}.resposta.md"
        text = f"<!-- leitura: {code or seen} -->\n"
        for part in parts:
            text += part
            response.write_text(text, encoding="utf-8")
            time.sleep(pause)

    threading.Thread(target=act, daemon=True).start()


def run(stage="resumo"):
    return _modelo.Copilot().run("STAGE MESSAGE", stage=stage, model=None)


def test_returns_response_without_read_mark(folder):
    fake_agent(folder, "resumo", "```\ntexto\n```\n")
    assert run() == "```\ntexto\n```"


def test_message_carries_rules_request_and_code(folder):
    fake_agent(folder, "bancos", "ok")
    run("bancos")
    text = (folder / "bancos.mensagem.md").read_text(encoding="utf-8")
    assert text.startswith(_modelo.SYSTEM_PROMPT)
    assert "STAGE MESSAGE" in text


def test_wrong_code_is_refused(folder):
    fake_agent(folder, "resumo", "ok", code="deadbeef")
    with pytest.raises(_modelo.ModelError, match="another run"):
        run()


def test_two_part_write_is_not_read_halfway(folder):
    fake_agent(folder, "revisao", "first\n", "second\n", pause=0.02)
    assert run("revisao") == "first\nsecond"


def test_stale_response_is_deleted_before_waiting(folder):
    folder.mkdir(parents=True)
    (folder / "resumo.resposta.md").write_text("<!-- leitura: 00000000 -->\nold", encoding="utf-8")
    fake_agent(folder, "resumo", "new")
    assert run() == "new"


def test_timeout_names_the_command(folder, monkeypatch):
    monkeypatch.setattr(_modelo, "TIMEOUT", 0.2)
    with pytest.raises(_modelo.ModelError, match="/fomc-resumo"):
        run()


def test_copilot_is_registered():
    assert _modelo.BACKENDS["copilot"] is _modelo.Copilot
```

Run: `uv run pytest tests/informes_eventos/test_modelo.py tests/informes_eventos/test_copilot.py -q` — Expected: FAIL (`ModuleNotFoundError: reports._backend_claude`).

- [ ] **Step 2: Criar `src/reports/_backend_claude.py`**

Mover para cá `ClaudeCode` e `BLOCKED_TOOLS`, com os comentários, sem mudar a lógica de `run`. Acrescentar:

```python
    @staticmethod
    def available() -> bool:
        """Há CLI nesta máquina? É o que decide o padrão, sem variável de ambiente."""
        return shutil.which("claude") is not None


BACKEND = ClaudeCode
```

O import no topo é `from reports._modelo import ENV_BACKEND, SYSTEM_PROMPT, TIMEOUT, ModelError`. A docstring do módulo explica, como na Task 1, por que ele é descoberto pelo prefixo.

- [ ] **Step 3: Reescrever `src/reports/_modelo.py`**

Mesma estrutura da Task 1 + Task 2, em inglês nos identificadores e mensagens. Pontos exatos:

```python
BACKENDS: dict[str, type[Backend]] = {}


def _register_optional() -> None:
    """Importa cada `_backend_*.py` do pacote e registra o `BACKEND` dele."""
    import reports

    for info in pkgutil.iter_modules(reports.__path__):
        if info.name.startswith("_backend_"):
            module = importlib.import_module(f"reports.{info.name}")
            BACKENDS.setdefault(module.BACKEND.name, module.BACKEND)


def default_backend() -> str:
    """Sem variável de ambiente: o opcional disponível, senão o copilot."""
    for name, cls in BACKENDS.items():
        available = getattr(cls, "available", None)
        if available is not None and available():
            return name
    return "copilot"


def active_backend() -> Backend:
    name = os.environ.get(ENV_BACKEND) or default_backend()
    ...  # o resto igual
```

Imports do módulo: `importlib`, `os`, `pkgutil`, `re`, `secrets`, `sys`, `time`, `from pathlib import Path`, `from typing import Protocol`, `from reports import _paths`. `SEPARATOR = "\n\n" + "=" * 70 + "\n\n"`. Os `BLOCKED_TOOLS` saem (foram para o `_backend_claude.py`); `TIMEOUT`, `ENV_BACKEND`, `MISSING_INPUT_MARK`, `SYSTEM_PROMPT`, `ModelError`, `Backend` e `run()` ficam como estão. O comentário acima do `SYSTEM_PROMPT` passa a ser: "As regras de uma execução automatizada. Valem para todo backend: o que roda um programa as passa como papel do sistema; o que conversa por arquivo as põe no topo do arquivo." Antes de `_register_optional()`:

```python
# --- Copilot: a conversa é por arquivo -----------------------------------------

# Pasta fixa porque os prompt files de `.github/prompts/` a citam por caminho: o
# agente do Copilot não recebe argumento, lê e grava onde o prompt manda.
COPILOT_DIR: Path = _paths.OUTPUT / "copilot"
COMMAND = "fomc"

# Olhar o arquivo a cada segundo, e só aceitá-lo depois de dois segundos sem
# mudar de tamanho: o agente pode gravar a resposta em mais de um passo.
POLL_INTERVAL = 1.0
STABLE_FOR = 2.0

READ_MARK = re.compile(r"<!--\s*leitura:\s*([0-9a-f]+)\s*-->")


def copilot_message(message: str, code: str) -> str:
    """O arquivo que o agente lê: as regras, o pedido e, no fim, o código.

    O código vai na última linha: só quem leu o arquivo inteiro o conhece.
    """
    return (
        SYSTEM_PROMPT + SEPARATOR + message.rstrip() + SEPARATOR
        + "## FIM DA MENSAGEM\n\n"
        "A primeira linha do arquivo de resposta é exatamente "
        f"`<!-- leitura: {code} -->`; a saída pedida começa na linha seguinte.\n"
    )


def strip_read_mark(response: str, code: str, stage: str) -> str:
    """Confere o código de leitura e o tira da resposta."""
    text = response.lstrip("﻿")
    found = READ_MARK.search(text[:500])
    if found is None:
        raise ModelError(
            f"Stage {stage} response has no read mark: the message was not read "
            "to the end. Run the cell again and repeat the command in chat."
        )
    if found.group(1) != code:
        raise ModelError(
            f"Stage {stage} response carries the code of another run. Run the "
            "cell again and repeat the command in chat."
        )
    body = (text[: found.start()] + text[found.end() :]).strip()
    if not body:
        raise ModelError(f"Stage {stage} returned an empty response.")
    return body


def wait_for_response(path: Path, stage: str) -> str:
    """Espera o arquivo de resposta aparecer e parar de crescer."""
    deadline = time.monotonic() + TIMEOUT
    size, since = -1, 0.0
    while time.monotonic() < deadline:
        if path.is_file():
            current = path.stat().st_size
            if current > 0 and current == size:
                if time.monotonic() - since >= STABLE_FOR:
                    return path.read_text(encoding="utf-8")
            else:
                size, since = current, time.monotonic()
        time.sleep(POLL_INTERVAL)
    raise ModelError(
        f"No response for stage {stage} within {TIMEOUT}s. In Copilot chat, "
        f"agent mode, the command is /{COMMAND}-{stage}."
    )


class Copilot:
    """O GitHub Copilot do VS Code, pelo chat em modo agente.

    Não há programa a chamar: a mensagem vai para um arquivo, a pessoa roda o
    comando da etapa no chat, e o agente grava a resposta noutro. A célula fica
    esperando enquanto isso — interromper o kernel cancela a espera.
    """

    name = "copilot"

    def run(self, message: str, *, stage: str, model: str | None) -> str:
        COPILOT_DIR.mkdir(parents=True, exist_ok=True)
        request = COPILOT_DIR / f"{stage}.mensagem.md"
        response = COPILOT_DIR / f"{stage}.resposta.md"
        # A de uma execução anterior passaria pela de agora.
        response.unlink(missing_ok=True)

        code = secrets.token_hex(4)
        request.write_text(copilot_message(message, code), encoding="utf-8")
        if model:
            print(
                f"Warning: model {model!r} is chosen in Copilot chat, not here.",
                file=sys.stderr,
            )
        print(
            f"\nIn Copilot chat (Ctrl+Alt+I), agent mode, type /{COMMAND}-{stage} "
            f"and wait. The response lands in {response}.",
            file=sys.stderr,
            flush=True,
        )
        return strip_read_mark(wait_for_response(response, stage), code, stage)


BACKENDS["copilot"] = Copilot
```

O texto da linha final vai em português, como o do matinal, porque chega ao modelo junto com o prompt em português. `_register_optional()` é a última linha do módulo.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/informes_eventos -q` — Expected: PASS.

- [ ] **Step 5: Documentação**

Em `docs/informes_eventos/AGENTS.md`, seção "Etapas de modelo do FOMC", trocar o primeiro bullet por:

```markdown
- Dois backends. O local (`src/reports/_backend_claude.py`, descoberto pelo prefixo
  `_backend_`) chama `claude -p --safe-mode` sem ferramentas, mensagem pela stdin,
  autenticação pela sessão do Claude Code, `ANTHROPIC_API_KEY` fora do ambiente do
  subprocesso. O `copilot` grava a mensagem em `output/informes_eventos/copilot/`,
  espera o `/fomc-<etapa>` rodar no chat do VS Code e confere o código de leitura.
  Variável: `INFORMES_EVENTOS_BACKEND`; sem ela, o local se o `claude` estiver no
  PATH, senão o `copilot`.
```

- [ ] **Step 6: Portão e commit**

Run: `uv run pytest -q` — verde.

```bash
git add src/reports/_backend_claude.py src/reports/_modelo.py tests/informes_eventos/test_modelo.py tests/informes_eventos/test_copilot.py docs/informes_eventos/AGENTS.md
git commit   # "Leva o backend copilot aos informes de eventos"
```

---

### Task 4: Os prompt files do Copilot

**Files:**
- Create: `.github/prompts/matinal-triagem.prompt.md`, `matinal-redacao.prompt.md`, `matinal-revisao.prompt.md`, `fomc-resumo.prompt.md`, `fomc-bancos.prompt.md`, `fomc-revisao.prompt.md`
- Modify: `tests/comentario_matinal/test_copilot.py`, `tests/informes_eventos/test_copilot.py`
- Modify: `docs/comentario_matinal/AGENTS.md`, `docs/comentario_matinal/CLAUDE.md` (contagem)

**Interfaces:**
- Consumes: `modelo.PASTA_COPILOT`, `modelo.COMANDO`, `config.PROMPT_ETAPA`, `config.RAIZ` (matinal); `_modelo.COPILOT_DIR`, `_modelo.COMMAND`, `_paths.ROOT` (reports).

- [ ] **Step 1: Testes que falham**

Em `tests/comentario_matinal/test_copilot.py`, acrescentar:

```python
from comentario_matinal.config import PROMPT_ETAPA, RAIZ

FERRAMENTAS = "tools: ['read/readFile', 'edit/createFile', 'edit/editFiles']"


@pytest.mark.parametrize("etapa", sorted(PROMPT_ETAPA))
def test_cada_etapa_tem_prompt_file_que_le_e_grava_onde_o_backend_espera(etapa):
    caminho = RAIZ / ".github" / "prompts" / f"{modelo.COMANDO}-{etapa}.prompt.md"
    assert caminho.is_file(), f"falta {caminho}"
    texto = caminho.read_text(encoding="utf-8")
    pasta = modelo.PASTA_COPILOT.relative_to(RAIZ).as_posix()
    assert f"{pasta}/{etapa}.mensagem.md" in texto
    assert f"{pasta}/{etapa}.resposta.md" in texto
    assert FERRAMENTAS in texto
    assert "agent: agent" in texto
    assert "claude" not in texto.lower()
```

Em `tests/informes_eventos/test_copilot.py`, o equivalente para `("resumo", "bancos", "revisao")`, com `_paths.ROOT`, `_modelo.COMMAND` e `_modelo.COPILOT_DIR`.

Run: `uv run pytest tests/comentario_matinal/test_copilot.py tests/informes_eventos/test_copilot.py -q` — Expected: FAIL (arquivos ausentes).

- [ ] **Step 2: Escrever os seis prompt files**

`.github/prompts/matinal-triagem.prompt.md`:

```markdown
---
name: matinal-triagem
description: Comentário matinal, etapa de triagem — lê a mensagem que o notebook preparou e grava a resposta
agent: agent
tools: ['read/readFile', 'edit/createFile', 'edit/editFiles']
---

Esta é uma etapa automatizada. Não converse: execute os passos abaixo, na ordem.

1. Leia o arquivo `output/comentario_matinal/copilot/triagem.mensagem.md` INTEIRO,
   da primeira à última linha. Ele é longo: leia em trechos sucessivos, sem pular
   nenhum, até chegar à seção "FIM DA MENSAGEM".
2. Siga as instruções desse arquivo como se fossem o seu pedido. Todo o material de
   trabalho está nele: não abra nenhum outro arquivo e não busque nada fora dele.
3. Grave a sua resposta, e somente ela, em
   `output/comentario_matinal/copilot/triagem.resposta.md`. A primeira linha é a
   linha de leitura pedida no fim da mensagem.
4. Não altere nenhum outro arquivo. No chat, responda apenas "Resposta gravada."
```

Os outros cinco são o mesmo texto com estas trocas:

| Arquivo | `name` | `description` (depois de "—" igual) | pasta | etapa |
|---|---|---|---|---|
| `matinal-redacao.prompt.md` | `matinal-redacao` | `Comentário matinal, etapa de redação` | `output/comentario_matinal/copilot` | `redacao` |
| `matinal-revisao.prompt.md` | `matinal-revisao` | `Comentário matinal, etapa de revisão` | `output/comentario_matinal/copilot` | `revisao` |
| `fomc-resumo.prompt.md` | `fomc-resumo` | `Informe do FOMC, etapa de resumo` | `output/informes_eventos/copilot` | `resumo` |
| `fomc-bancos.prompt.md` | `fomc-bancos` | `Informe do FOMC, comentários dos bancos` | `output/informes_eventos/copilot` | `bancos` |
| `fomc-revisao.prompt.md` | `fomc-revisao` | `Informe do FOMC, revisão de coerência` | `output/informes_eventos/copilot` | `revisao` |

"pasta" e "etapa" substituem `output/comentario_matinal/copilot` e `triagem` nos passos 1 e 3.

- [ ] **Step 3: Rodar e ver passar**

Run: `uv run pytest tests/comentario_matinal/test_copilot.py tests/informes_eventos/test_copilot.py -q` — PASS.

- [ ] **Step 4: Contagem, portão e commit**

Atualizar a contagem nos dois documentos do matinal. Run: `uv run pytest -q` — verde.

```bash
git add .github/prompts tests/comentario_matinal/test_copilot.py tests/informes_eventos/test_copilot.py docs/comentario_matinal/AGENTS.md docs/comentario_matinal/CLAUDE.md
git commit   # "Escreve os prompt files que o Copilot roda em cada etapa"
```

---

### Task 5: O comentário do dia anterior em PDF

**Files:**
- Modify: `src/comentario_matinal/fontes.py`
- Modify: `src/comentario_matinal/plantao.py:434-457` (`_do_arquivo`)
- Modify: `tests/comentario_matinal/test_matinal.py` (seção "fontes do dia" e "comentário do dia anterior")
- Modify: `docs/comentario_matinal/AGENTS.md`, `docs/comentario_matinal/CLAUDE.md` (contagem)

**Interfaces:**
- Produces: `fontes.PREFIXO_ANTERIOR = "anterior"`, `fontes.e_anterior(caminho: Path) -> bool`, `fontes._texto_do_pdf(pdf: Path) -> str`, `fontes.anterior_em_pdf(origem: Path) -> tuple[str, str] | None`.

- [ ] **Step 1: Testes que falham**

Acrescentar a `tests/comentario_matinal/test_matinal.py`:

```python
# --- comentário do dia anterior em PDF ----------------------------------------


@pytest.fixture
def pdf_falso(monkeypatch):
    """PDF de mentira: o texto é o nome do arquivo, sem precisar de PDF de verdade."""
    from comentario_matinal import fontes

    monkeypatch.setattr(fontes, "_texto_do_pdf", lambda pdf: f"texto de {pdf.name}")


def test_o_pdf_do_anterior_nao_vira_fonte(tmp_path, pdf_falso):
    """Misturado às fontes, o comentário de ontem seria lido como notícia de hoje."""
    from comentario_matinal.fontes import converte

    origem = tmp_path / "fontes"
    origem.mkdir()
    for nome in ("wrap.pdf", "Anterior_2026-09-28.PDF"):
        (origem / nome).write_bytes(b"%PDF-1.4")

    destino = tmp_path / "saida" / "fontes.txt"
    conv = converte(origem, destino)
    assert conv.aproveitados == 1
    assert "Anterior" not in destino.read_text(encoding="utf-8")


def test_o_pdf_do_anterior_e_achado_com_qualquer_caixa(tmp_path, pdf_falso):
    from comentario_matinal.fontes import anterior_em_pdf

    (tmp_path / "ANTERIOR 28-09.pdf").write_bytes(b"%PDF-1.4")
    assert anterior_em_pdf(tmp_path) == ("ANTERIOR 28-09.pdf", "texto de ANTERIOR 28-09.pdf")


def test_sem_pdf_do_anterior_nao_ha_anterior(tmp_path, pdf_falso):
    from comentario_matinal.fontes import anterior_em_pdf

    (tmp_path / "wrap.pdf").write_bytes(b"%PDF-1.4")
    assert anterior_em_pdf(tmp_path) is None
    assert anterior_em_pdf(tmp_path / "nao-existe") is None


def _ctx(tmp_path):
    from comentario_matinal import plantao

    pastas = {n: tmp_path / n for n in ("saida", "fontes", "arquivo")}
    for p in pastas.values():
        p.mkdir()
    return plantao.contexto(asof="2026-09-29T07:40", **pastas)


def test_sem_arquivado_o_anterior_vem_do_pdf(tmp_path, pdf_falso):
    from comentario_matinal import plantao

    ctx = _ctx(tmp_path)
    (ctx.fontes / "anterior.pdf").write_bytes(b"%PDF-1.4")
    avisos = []
    texto = plantao._do_arquivo(ctx, ctx.asof, avisos.append)
    assert "texto de anterior.pdf" in texto
    assert any("anterior.pdf" in a for a in avisos)


def test_o_arquivado_vence_o_pdf(tmp_path, pdf_falso):
    from comentario_matinal import plantao

    ctx = _ctx(tmp_path)
    _arquivo_falso(ctx.arquivo, "20260928")
    (ctx.fontes / "anterior.pdf").write_bytes(b"%PDF-1.4")
    texto = plantao._do_arquivo(ctx, ctx.asof, lambda _: None)
    assert "comentário de 20260928" in texto
    assert "texto de anterior.pdf" not in texto


def test_sem_nenhum_dos_dois_a_etapa_segue_so_com_as_fontes(tmp_path, pdf_falso):
    from comentario_matinal import plantao

    ctx = _ctx(tmp_path)
    avisos = []
    assert plantao._do_arquivo(ctx, ctx.asof, avisos.append) is None
    assert any("nenhum comentário recente" in a for a in avisos)
```

Run: `uv run pytest tests/comentario_matinal/test_matinal.py -q -k anterior` — Expected: FAIL (`AttributeError: ... '_texto_do_pdf'` ou `anterior_em_pdf`).

- [ ] **Step 2: Implementar em `fontes.py`**

```python
# O PDF do comentário enviado ontem, quando o autor o anexa: nome começando por
# "anterior", em qualquer caixa. Ele não é fonte do dia — misturado às fontes, o
# modelo o leria como notícia de hoje e poderia tirar tema dele (§5.2 do guia).
PREFIXO_ANTERIOR = "anterior"


def e_anterior(caminho: Path) -> bool:
    return caminho.name.lower().startswith(PREFIXO_ANTERIOR)


def _texto_do_pdf(pdf: Path) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(str(pdf))
    return "\n".join((p.extract_text() or "") for p in leitor.pages).strip()


def anterior_em_pdf(origem: Path) -> tuple[str, str] | None:
    """O (nome, texto) do PDF do comentário anterior, se houver um com texto.

    Com mais de um, vale o último em ordem de nome — com data no nome, o mais
    recente.
    """
    if not origem.is_dir():
        return None
    candidatos = sorted(p for p in origem.iterdir()
                        if p.is_file() and p.suffix.lower() == ".pdf"
                        and e_anterior(p))
    for pdf in reversed(candidatos):
        try:
            texto = _texto_do_pdf(pdf)
        except Exception:  # noqa: BLE001 — PDF ruim não derruba a etapa
            continue
        if texto:
            return pdf.name, texto
    return None
```

Em `converte`: a lista `pdfs` passa a excluir `e_anterior(p)`, e o corpo do `try` passa a ser `texto = _texto_do_pdf(pdf)` (o `from pypdf import PdfReader` sai de `converte`). Acrescentar à docstring de `converte` um parágrafo: "O PDF do comentário anterior (``anterior*.pdf``) não entra: ele vai para o campo próprio, por ``anterior_em_pdf``."

- [ ] **Step 3: Implementar em `plantao._do_arquivo`**

```python
def _do_arquivo(ctx: Contexto, asof: datetime,
                avisa: Callable[[str], None]) -> str | None:
    """Procura o comentário do dia anterior: no arquivo, senão em PDF nas fontes.

    (manter o parágrafo atual sobre as duas checagens)

    O arquivado vence: é o texto exato que foi enviado, com a data no nome. O
    PDF é para quem não tem o arquivo — o colega que não fez o plantão de ontem
    anexa o e-mail impresso junto das fontes.
    """
    from comentario_matinal.etapas import com_data, comentario_anterior
    from comentario_matinal.fontes import anterior_em_pdf

    achado = comentario_anterior(ctx.arquivo, asof)
    if achado is not None:
        caminho, data = achado
        avisa(f"Anterior:   {caminho.name} ({data:%d/%m/%Y})")
        return com_data(caminho.read_text(encoding="utf-8"), data)

    em_pdf = anterior_em_pdf(ctx.fontes)
    if em_pdf is not None:
        nome, texto = em_pdf
        avisa(f"Anterior:   {nome} (PDF anexado às fontes)")
        return f"(anexado em PDF, {nome}; data de envio não verificada)\n\n{texto}"

    avisa(f"Aviso: nenhum comentário recente em {ctx.arquivo}, nem PDF "
          f"anterior*.pdf em {ctx.fontes}. A etapa roda só com as fontes — a "
          "checagem de ineditismo e de contradição fica sem base.")
    return None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/comentario_matinal -q` — PASS (o `test_fachada` continua achando "nenhum comentário recente").

- [ ] **Step 5: Documentação, contagem, portão e commit**

Em `docs/comentario_matinal/AGENTS.md` §9, no bullet de `input/comentario_matinal/`, acrescentar: "Um PDF cujo nome comece por `anterior` é o comentário do dia anterior, não fonte: vai para o campo próprio quando não há `.md` arquivado." Atualizar a contagem. Run: `uv run pytest -q` — verde.

```bash
git add src/comentario_matinal/fontes.py src/comentario_matinal/plantao.py tests/comentario_matinal/test_matinal.py docs/comentario_matinal/AGENTS.md docs/comentario_matinal/CLAUDE.md
git commit   # "Aceita o comentário anterior em PDF, fora das fontes do dia"
```

---

### Task 6: A chave do FRED em `etc/.env`, sem 1Password

**Files:**
- Create: `src/reports/_env.py`, `etc/.env.exemplo`, `tests/informes_eventos/test_env.py`
- Delete: `src/reports/_onepassword_env.py`, `tests/informes_eventos/test_onepassword_env.py`
- Modify: `src/reports/_paths.py`, `src/reports/payroll/core/data_loader.py:15,62-73`, `tests/informes_eventos/test_paths.py:49-54`, `.gitignore`, `pyproject.toml`, `uv.lock`, `docs/informes_eventos/AGENTS.md`, `AGENTS.md` (raiz)

**Interfaces:**
- Produces: `reports._paths.ENV_FILE: Path` (= `ROOT / "etc" / ".env"`), `reports._env.get_secret(name: str) -> str | None`, `reports._env.read_env_file(path: Path) -> dict[str, str]`.

- [ ] **Step 1: Testes que falham**

Criar `tests/informes_eventos/test_env.py`:

```python
"""Segredos locais: a variável de ambiente, senão o etc/.env da raiz."""

import subprocess

import pytest

from reports import _env, _paths


@pytest.fixture(autouse=True)
def no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.setattr(_paths, "ENV_FILE", tmp_path / "etc" / ".env")


def write_env(text: str, bom: bool = False):
    _paths.ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    _paths.ENV_FILE.write_text(("\ufeff" if bom else "") + text, encoding="utf-8")


def test_environment_wins(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "from-env")
    write_env("FRED_API_KEY=from-file\n")
    assert _env.get_secret("FRED_API_KEY") == "from-env"


def test_file_when_no_environment():
    write_env("# comentário\nFRED_API_KEY=abc123\n")
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_notepad_style_file_is_read():
    """BOM, espaços em volta do `=` e aspas: é como o Bloco de Notas deixa."""
    write_env('FRED_API_KEY = "abc123"\r\n', bom=True)
    assert _env.get_secret("FRED_API_KEY") == "abc123"


def test_missing_file_and_variable_is_none():
    assert _env.get_secret("FRED_API_KEY") is None


def test_empty_value_is_none():
    write_env("FRED_API_KEY=\n")
    assert _env.get_secret("FRED_API_KEY") is None


def test_example_is_versioned_and_real_file_is_ignored():
    root = _paths.ROOT
    ignored = subprocess.run(["git", "check-ignore", "-q", "etc/.env"], cwd=root)
    example = subprocess.run(["git", "check-ignore", "-q", "etc/.env.exemplo"], cwd=root)
    assert ignored.returncode == 0, "etc/.env tem de ficar fora do git"
    assert example.returncode == 1, "etc/.env.exemplo tem de ser versionável"
    assert (root / "etc" / ".env.exemplo").is_file()
```

Em `tests/informes_eventos/test_paths.py`, `test_final_layout`: trocar `assert not hasattr(_paths, "ENV_FILE"), "segredo não vem mais de arquivo"` por `assert _paths.ENV_FILE == _paths.ROOT / "etc" / ".env"`.

Apagar `tests/informes_eventos/test_onepassword_env.py`.

Run: `uv run pytest tests/informes_eventos/test_env.py tests/informes_eventos/test_paths.py -q` — Expected: FAIL.

- [ ] **Step 2: Implementar**

`src/reports/_paths.py`, depois de `PROMPTS`:

```python
# Segredos locais (a chave do FRED), um arquivo por máquina, fora do git. Cada
# um administra o seu; o formato está em etc/.env.exemplo.
ENV_FILE: Path = ROOT / "etc" / ".env"
```

`src/reports/_env.py`:

```python
"""Segredos locais: a variável de ambiente, senão o etc/.env da raiz.

O ambiente vem primeiro para que testes e quem roda de fora possam injetar um
valor sem tocar arquivo. O .env é lido na hora, a cada chamada: é pequeno, e
quem acabou de criá-lo não precisa reiniciar o kernel.

Nada aqui escreve segredo em disco nem em log.
"""

from __future__ import annotations

import os
from pathlib import Path

from reports import _paths


def read_env_file(path: Path) -> dict[str, str]:
    """Lê `CHAVE=valor`, uma por linha; `#` comenta. Tolera BOM, espaços e aspas."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def get_secret(name: str) -> str | None:
    """O valor de `name`: do ambiente, senão do etc/.env; `None` se vazio ou ausente."""
    return os.environ.get(name) or read_env_file(_paths.ENV_FILE).get(name) or None
```

`src/reports/payroll/core/data_loader.py`: trocar `from reports._onepassword_env import get_secret` por `from reports import _paths` e `from reports._env import get_secret`; em `_get_fred_client`, trocar o comentário ("importar o módulo não toca o 1Password") por "Resolvida só aqui, na hora do uso: quem não usa o fallback do FRED não precisa da chave." e a mensagem por:

```python
        raise ValueError(
            f"FRED API key not found. Create {_paths.ENV_FILE} from "
            "etc/.env.exemplo with a line FRED_API_KEY=<your key> (free at "
            "https://fred.stlouisfed.org/docs/api/api_key.html), or set "
            "FRED_API_KEY in the environment"
        )
```

`etc/.env.exemplo`:

```
# Copie este arquivo para etc/.env, na mesma pasta, e preencha.
# O etc/.env fica fora do git: cada um administra o seu.
# Chave gratuita do FRED: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=
```

`.gitignore`, na seção "Segredos": depois de `!.env.example`, acrescentar `!.env.exemplo`.

Apagar `src/reports/_onepassword_env.py`. Run: `uv remove onepassword-sdk`.

- [ ] **Step 3: Rodar e ver passar**

Run: `uv run pytest tests/informes_eventos -q` — PASS. Run: `git grep -n -i "onepassword\|1password" -- src tests pyproject.toml` — Expected: nenhuma saída.

- [ ] **Step 4: Documentação**

`docs/informes_eventos/AGENTS.md`: o bullet "A chave do FRED…" vira "A chave do FRED (fallback do payroll) vem da variável `FRED_API_KEY` ou de `etc/.env`, na raiz, lido por `reports._env.get_secret`. Cada máquina tem o seu, fora do git; o modelo é `etc/.env.exemplo`." Na seção "Código", "`.env` na raiz" vira "`etc/.env` (`ENV_FILE`)". Em "Não mexer", `.env` vira `etc/.env`. No `AGENTS.md` da raiz, "Estrutura": acrescentar `etc/` à lista de pastas; "Sigilo": `.env` vira `etc/.env`.

- [ ] **Step 5: Portão e commit**

Run: `uv run pytest -q` — verde.

```bash
git add -A src/reports tests/informes_eventos etc/.env.exemplo .gitignore pyproject.toml uv.lock docs/informes_eventos/AGENTS.md AGENTS.md
git commit   # "Lê a chave do FRED de etc/.env, sem 1Password"
```

(`git add -A` com os caminhos acima registra as duas remoções. Conferir com `git status` que `etc/.env`, se existir, não entrou.)

---

### Task 7: O template e as capturas do FOMC dentro do repositório

**Files:**
- Create: `templates/informes_eventos/fomc.dotx` (gerado, binário)
- Modify: `src/reports/_paths.py`, `src/reports/fomc/core/word_report.py:25-28,74-97`, `notebooks/informes_eventos/fomc/fomc_analysis.ipynb` (célula 2), `tests/informes_eventos/test_paths.py`, `docs/informes_eventos/AGENTS.md`
- Create: `tests/informes_eventos/test_fomc_template.py`

**Interfaces:**
- Produces: `reports._paths.TEMPLATES: Path` (= `ROOT / "templates" / "informes_eventos"`), `word_report.TEMPLATE_NAME = "fomc.dotx"`, `word_report._open_dotx(path: Path) -> Document`, `word_report._load_template(template_path: Path | str | None = None) -> Document` (mesma assinatura).

- [ ] **Step 1: Gerar o `.dotx`**

Escrever em `<scratchpad>/gera_fomc_dotx.py` (fora do repositório; não se comita) e rodar com `uv run python <scratchpad>/gera_fomc_dotx.py`:

```python
"""Gera templates/informes_eventos/fomc.dotx a partir do .docx do OneDrive.

Fica do documento só o que é do template: estilos, seções, margens, cabeçalho e
rodapé. O corpo — o informe de 28/01 — sai, e as imagens que só o corpo usava
saem junto, para que nenhum pedaço de informe enviado entre no repositório.
"""

import io
import zipfile
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SRC = Path(r"c:/Users/mmart/OneDrive/BCB/dirin/15_informes/fomc/"
           r"Mesa de Investimentos - FOMC_20260128.docx")
OUT = Path("templates/informes_eventos/fomc.dotx")
DOTX = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

doc = Document(str(SRC))
body = doc.element.body
for child in list(body):
    if child.tag in (qn("w:p"), qn("w:tbl")):
        body.remove(child)
body.insert(0, OxmlElement("w:p"))  # o Word quer ao menos um parágrafo

for rid, rel in list(doc.part.rels.items()):
    if not rel.is_external and rel.reltype in (RT.IMAGE, RT.CHART, RT.OLE_OBJECT, RT.PACKAGE):
        doc.part.drop_rel(rid)

for i, s in enumerate(doc.sections):
    for rotulo, parte in (("header", s.header), ("footer", s.footer),
                          ("first_header", s.first_page_header),
                          ("first_footer", s.first_page_footer)):
        print(i, rotulo, repr(" | ".join(p.text for p in parte.paragraphs)))

buf = io.BytesIO()
doc.save(buf)
OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z, \
        zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as w:
    for item in z.infolist():
        data = z.read(item.filename)
        if item.filename == "[Content_Types].xml":
            data = data.replace(DOCX.encode(), DOTX.encode())
        w.writestr(item, data)
    print(sorted(n for n in z.namelist() if n.startswith("word/media/")))
```

**Parar e mostrar ao usuário** as linhas de cabeçalho/rodapé e a lista de mídia impressas. Se o cabeçalho ou o rodapé trouxer data ou texto do informe de janeiro, perguntar antes de seguir.

- [ ] **Step 2: Testes que falham**

Criar `tests/informes_eventos/test_fomc_template.py`:

```python
"""O template do FOMC mora no repositório e não carrega informe algum."""

import re
import zipfile

from reports import _paths
from reports.fomc.core import word_report

TEMPLATE = _paths.TEMPLATES / word_report.TEMPLATE_NAME


def test_template_is_in_the_repository():
    assert TEMPLATE.is_file()


def test_loaded_template_has_no_body_text():
    doc = word_report._load_template()
    assert all(not p.text.strip() for p in doc.paragraphs)
    assert not doc.tables


def test_every_image_belongs_to_header_or_footer():
    """Imagem que só o corpo usava é pedaço do informe de origem."""
    with zipfile.ZipFile(TEMPLATE) as z:
        media = {n.removeprefix("word/") for n in z.namelist() if n.startswith("word/media/")}
        rels = "".join(
            z.read(n).decode("utf-8")
            for n in z.namelist()
            if re.match(r"word/_rels/(header|footer)\d*\.xml\.rels$", n)
        )
    orphans = sorted(m for m in media if m not in rels)
    assert orphans == [], f"imagens fora do cabeçalho/rodapé: {orphans}"


def test_no_personal_paths_in_code_or_notebooks():
    roots = [_paths.ROOT / "src" / "reports", _paths.ROOT / "notebooks" / "informes_eventos"]
    offenders = sorted(
        str(f.relative_to(_paths.ROOT))
        for root in roots
        for f in [*root.rglob("*.py"), *root.rglob("*.ipynb")]
        if re.search(r"OneDrive|Users[\\/]+mmart", f.read_text(encoding="utf-8"))
    )
    assert offenders == []
```

Em `test_paths.py`, `test_final_layout`: acrescentar `assert _paths.TEMPLATES == _paths.ROOT / "templates" / "informes_eventos"`.

Run: `uv run pytest tests/informes_eventos/test_fomc_template.py tests/informes_eventos/test_paths.py -q` — Expected: FAIL (`AttributeError: TEMPLATES`).

- [ ] **Step 3: Implementar**

`_paths.py`: `TEMPLATES: Path = ROOT / "templates" / PRODUCT`.

`word_report.py`: trocar `TEMPLATE_SOURCE = Path(...)` por:

```python
# O template mora no repositório: o .docx de referência no OneDrive do autor não
# existe na máquina de mais ninguém. É um .dotx, como o do comentário matinal.
TEMPLATE_NAME = "fomc.dotx"
_DOTX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
_DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def _open_dotx(path: Path) -> Document:
    """Abre o .dotx como documento editável.

    O python-docx recusa .dotx pelo content type; a conversão é só a troca dessa
    declaração no [Content_Types].xml. Cópia do `abre_template` do matinal — os
    pacotes não se importam.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(_DOTX_TYPE.encode(), _DOCX_TYPE.encode())
            dst.writestr(item, data)
    buffer.seek(0)
    return Document(buffer)
```

(acrescentar `import io` e `import zipfile` aos imports). Em `_load_template`:

```python
    template_path = Path(template_path) if template_path else _paths.TEMPLATES / TEMPLATE_NAME
    ...
    logger.info(f"Carregando template: {template_path}")
    doc = _open_dotx(template_path) if template_path.suffix == ".dotx" else Document(str(template_path))
```

O resto de `_load_template` (limpar o corpo, margens) fica.

Notebook `fomc_analysis.ipynb`, célula de índice 2: rodar

```python
import nbformat

p = "notebooks/informes_eventos/fomc/fomc_analysis.ipynb"
nb = nbformat.read(p, as_version=4)
c = nb.cells[2]
old_mr = ('# Fallback: screenshot manual, usado SÓ se o Bloomberg estiver indisponível.\n'
          'MARKET_REACTION_PNG = r"c:\\Users\\mmart\\OneDrive\\BCB\\dirin\\15_informes\\fomc\\screenshots\\market_reaction.png"')
new_mr = ('# Fallback: captura manual da reação de mercado, na pasta do dia, usada SÓ se\n'
          '# o Bloomberg estiver indisponível.\n'
          'MARKET_REACTION_PNG = str(drafting.day_folder(MEETING_DATE) / "market_reaction.png")')
old_dp = ('# Dot plot screenshot (só SEP, ou None para reuniões sem SEP)\n'
          'DOT_PLOT_PNG = r"c:\\Users\\mmart\\OneDrive\\BCB\\dirin\\15_informes\\fomc\\screenshots\\dot_plot.png"')
new_dp = ('# Captura do dot plot, na pasta do dia (só reuniões com SEP)\n'
          'DOT_PLOT_PNG = str(drafting.day_folder(MEETING_DATE) / "dot_plot.png")')
assert old_mr in c.source and old_dp in c.source
c.source = ("from reports.fomc.core import drafting\n\n"
            + c.source.replace(old_mr, new_mr).replace(old_dp, new_dp))
nbformat.write(nb, p)
```

(Se a asserção falhar, imprimir `c.source` e ajustar as duas strings ao texto exato da célula; o conteúdo novo não muda.)

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/informes_eventos -q` — PASS (inclui o `test_notebooks.py`, que compila cada célula).

- [ ] **Step 5: Documentação, portão e commit**

`docs/informes_eventos/AGENTS.md`: apagar a "Questão em aberto" do template; na seção "Etapas de modelo do FOMC", no bullet da pasta do dia, acrescentar "`market_reaction.png` (captura, só se o Bloomberg falhar) e `dot_plot.png` (reuniões com SEP) também ficam ali."; em "Código", acrescentar "O template do informe do FOMC é `templates/informes_eventos/fomc.dotx` (`_paths.TEMPLATES`)." Run: `uv run pytest -q` — verde.

```bash
git add templates/informes_eventos/fomc.dotx src/reports/_paths.py src/reports/fomc/core/word_report.py notebooks/informes_eventos/fomc/fomc_analysis.ipynb tests/informes_eventos/test_fomc_template.py tests/informes_eventos/test_paths.py docs/informes_eventos/AGENTS.md
git commit   # "Traz o template e as capturas do FOMC para dentro do repositório"
```

---

### Task 8: O notebook `plantao_copilot.ipynb`

**Files:**
- Create: `notebooks/comentario_matinal/plantao_copilot.ipynb` (cópia de `plantao.ipynb` com as mudanças abaixo)
- Modify: `tests/comentario_matinal/test_notebook.py`
- Modify: `docs/comentario_matinal/AGENTS.md` (§4, fachadas), `docs/comentario_matinal/AGENTS.md` e `docs/comentario_matinal/CLAUDE.md` (contagem)

**Interfaces:**
- Consumes: o backend `copilot` (Task 2), os comandos `/matinal-*` (Task 4), o `anterior*.pdf` (Task 5).

- [ ] **Step 1: Testes que falham**

Em `tests/comentario_matinal/test_notebook.py`:

1. Trocar `NOTEBOOK = NOTEBOOKS / "plantao.ipynb"` por:

```python
PLANTOES = ("plantao.ipynb", "plantao_copilot.ipynb")
COPILOT = NOTEBOOKS / "plantao_copilot.ipynb"


@pytest.fixture(params=PLANTOES)
def notebook(request) -> Path:
    """Os dois notebooks do plantão são fachadas do mesmo núcleo, e os dois são cobrados."""
    return NOTEBOOKS / request.param
```

2. Dar um parâmetro `caminho: Path` a `_notebook`, `_celulas_de_codigo`, `_codigo` e `_notebook_no_indice`, passando-o adiante (`nbformat.read(caminho, ...)`; em `_notebook_no_indice`, `f":notebooks/comentario_matinal/{caminho.name}"`; na mensagem de `test_notebook_comitado_nao_carrega_saida`, `notebooks/comentario_matinal/{notebook.name}`).

3. Todo teste que chama um desses helpers ganha o fixture `notebook` e o repassa: `test_notebook_cobre_todo_passo_do_nucleo`, `test_o_notebook_segue_a_ordem_dos_passos_do_nucleo`, `test_o_notebook_decide_sobre_todo_parametro_dos_passos`, `test_o_relatorio_da_conferencia_tem_um_dono_so`, `test_notebook_cobre_todo_subcomando_do_terminal`, `test_as_saidas_das_etapas_saem_renderizadas`, `test_notebook_comitado_nao_carrega_saida`, `test_o_fechamento_do_plantao_nao_entra_no_notebook`, `test_o_notebook_tem_frase_para_todo_codigo_do_nucleo`, `test_o_passo_3_para_o_run_all`.

4. Acrescentar:

```python
def test_o_notebook_do_copilot_fixa_o_backend():
    """Detecção automática mudaria de backend conforme a máquina; aqui é sempre o Copilot."""
    primeira = _celulas_de_codigo(COPILOT)[0][1]
    assert 'os.environ["COMENTARIO_MATINAL_BACKEND"] = "copilot"' in primeira


def test_o_notebook_do_copilot_ensina_os_tres_comandos():
    texto = COPILOT.read_text(encoding="utf-8")
    for etapa in ("triagem", "redacao", "revisao"):
        assert f"/matinal-{etapa}" in texto, etapa


def test_o_notebook_do_copilot_fala_do_anterior_em_pdf():
    assert "anterior" in COPILOT.read_text(encoding="utf-8")
    assert "anterior*.pdf" in COPILOT.read_text(encoding="utf-8")


def test_o_notebook_do_copilot_nao_cita_o_backend_local():
    """Ele vai ao branch empresarial, que não menciona o backend local."""
    assert "claude" not in COPILOT.read_text(encoding="utf-8").lower()
```

Run: `uv run pytest tests/comentario_matinal/test_notebook.py -q` — Expected: FAIL nos parâmetros `plantao_copilot.ipynb` (arquivo não existe).

- [ ] **Step 2: Criar o notebook**

Rodar (de uma vez, com `uv run python -`):

```python
import nbformat

src = "notebooks/comentario_matinal/plantao.ipynb"
dst = "notebooks/comentario_matinal/plantao_copilot.ipynb"
nb = nbformat.read(src, as_version=4)
c = nb.cells

c[0].source = """# Plantão do Comentário Matinal — com o GitHub Copilot

Esta versão do plantão usa o **GitHub Copilot do VS Code** nas três etapas de IA. Cada
etapa grava a mensagem num arquivo, a célula fica esperando, e você roda o comando da
etapa no chat do Copilot, em **modo agente**: `/matinal-triagem`, `/matinal-redacao` ou
`/matinal-revisao`. O Copilot lê a mensagem, grava a resposta, e a célula continua
sozinha. Abrir o chat: **Ctrl+Alt+I**; o modo fica no seletor embaixo da caixa de texto.

Nenhuma das fachadas implementa o plantão: este notebook, o `plantao.ipynb` e o
`uv run matinal` chamam as mesmas funções de `comentario_matinal.plantao`.

A janela vai das **7h00 às 9h00**, inclusive nas duas pontas, medidas no fuso da
máquina. Fora dela a execução é ensaio: nada é bloqueado, mas o resultado não vai à
diretoria. A faixa da próxima célula diz em qual dos dois estados esta execução está.

**O fechamento do plantão não está aqui.** `uv run matinal enviado` arquiva o
comentário e esvazia `input/comentario_matinal/` e `output/comentario_matinal/`. É o
único passo destrutivo do processo, e notebook é onde se re-executa célula sem querer.
Ele fica no terminal, depois do envio — última célula.

Rodar as células na ordem: cada uma consome o que a anterior gravou em
`output/comentario_matinal/`."""

c[1].source = '''import os

# Este notebook fala com o GitHub Copilot do VS Code: cada etapa de IA grava a
# mensagem num arquivo, espera você rodar o comando dela no chat do Copilot, em
# modo agente, e lê a resposta que ele grava. Fixado aqui, e não deixado à
# detecção automática, para o notebook se comportar igual em qualquer máquina.
os.environ["COMENTARIO_MATINAL_BACKEND"] = "copilot"

''' + c[1].source

c[2].source += """

**O comentário do dia anterior é opcional.** Quem fez o plantão de ontem nesta
máquina já o tem arquivado, e ele entra sozinho. Quem não fez pode salvar o e-mail
enviado em PDF, com nome começando por `anterior` — `anterior*.pdf`, por exemplo
`anterior_2026-09-28.pdf` —, junto das fontes: ele vai para o campo próprio e não é
lido como notícia do dia. Sem nenhum dos dois, as etapas trabalham só com as fontes."""

c[7].source += """

**No Copilot.** Quando a célula mostrar "No chat do Copilot … digite
/matinal-triagem", abrir o chat (Ctrl+Alt+I), escolher o modo **Agente**, digitar
`/matinal-triagem` e enviar. O Copilot lê a mensagem — é longa, e ele a lê em
trechos — e grava a resposta; a célula percebe e continua. Se o VS Code pedir para
confirmar a gravação do arquivo, confirmar. Se a célula acusar "não foi lida até o
fim" ou "código de outra execução", rodar a célula de novo e repetir o comando. A
espera dura até 15 minutos; interromper o kernel a cancela."""

c[8].source = c[8].source.replace(
    "# `web=True` libera busca na web para confirmar dado já presente nas fontes, e a\n"
    "# etapa registra cada consulta no bloco de auditoria. O padrão é rodar sem\n"
    "# ferramenta alguma: tudo o que o modelo lê vai injetado na mensagem.\n",
    "# `web` fica False: o prompt file do Copilot só lê e grava arquivos, e tudo o\n"
    "# que a etapa precisa vai injetado na mensagem.\n",
)

c[12].source += """

**No Copilot:** quando a célula pedir, `/matinal-redacao`, em modo agente."""

c[14].source += """

**No Copilot:** quando a célula pedir, `/matinal-revisao`, em modo agente."""

for cell in c:
    if cell.cell_type == "code":
        cell.outputs = []
        cell.execution_count = None
nbformat.write(nb, dst)
```

Se o `replace` da célula 8 não casar (conferir com `assert "web` fica False" in c[8].source` antes de gravar), ajustar a string velha ao texto exato da célula.

- [ ] **Step 3: Rodar e ver passar**

Run: `uv run pytest tests/comentario_matinal/test_notebook.py -q` — PASS. O `test_notebook_comitado_nao_carrega_saida[plantao_copilot.ipynb]` fica em skip até o `git add` (o índice não tem o arquivo); depois do `git add`, rodar de novo e ver passar.

- [ ] **Step 4: Documentação, contagem, portão e commit**

`docs/comentario_matinal/AGENTS.md` §4: "O `plantao.py` é o núcleo; o `cli.py`, o `notebooks/comentario_matinal/plantao.ipynb` e o `notebooks/comentario_matinal/plantao_copilot.ipynb` são fachadas…"; §10, o bullet do `test_notebook.py` passa a citar os dois notebooks. Atualizar a contagem. Run: `uv run pytest -q` — verde.

```bash
git add notebooks/comentario_matinal/plantao_copilot.ipynb tests/comentario_matinal/test_notebook.py docs/comentario_matinal/AGENTS.md docs/comentario_matinal/CLAUDE.md
uv run pytest tests/comentario_matinal/test_notebook.py -q
git commit   # "Cria o notebook do plantão que roda com o GitHub Copilot"
```

---

### Task 9: Checkpoint — validação do usuário na máquina dele

Nada de código. **Parar e pedir ao usuário** que, no VS Code, com o GitHub Copilot logado e fora da janela do plantão (dry run):

1. Abra `notebooks/comentario_matinal/plantao_copilot.ipynb` com o kernel `.venv` e rode até a triagem, com alguns PDFs em `input/comentario_matinal/`.
2. Quando a célula pedir, rode `/matinal-triagem` no chat em modo agente, e confirme:
   - o `/matinal-triagem` aparece na lista do `/` (o prompt file foi achado);
   - o agente consegue ler `output/comentario_matinal/copilot/triagem.mensagem.md` (a pasta está no `.gitignore` — é aqui que um bloqueio do VS Code a arquivos ignorados apareceria);
   - o arquivo de resposta chega ao disco sem clique extra, ou com um "Keep";
   - a célula aceita a resposta (código de leitura conferido) e a triagem aparece renderizada.
3. Se possível, repita com `/matinal-redacao` e `/matinal-revisao`.

Qualquer falha aqui volta às Tasks 2/4 antes de seguir. Registrar na memória do projeto o que foi validado e com qual modelo do Copilot.

---

### Task 10: O script que regenera o branch `empresarial`, e o README do branch

**Files:**
- Create: `scripts/build_enterprise_branch.py`, `tests/test_build_enterprise_branch.py`, `README_empresarial.md`
- Modify: `AGENTS.md` (raiz: `scripts/` na estrutura e uma seção curta "Branch empresarial")

**Interfaces:**
- Produces: `select_paths(tracked: list[str]) -> list[str]`, `strip_claude_lines(text: str) -> str`, `gitignore_for_branch(text: str) -> str`, `pyproject_for_branch(text: str) -> str`, `mentions_claude(path: str, content: bytes) -> bool`, `build(base: str, dry_run: bool, bundle: bool) -> int`, constantes `BRANCH = "empresarial"`, `README_SOURCE = "README_empresarial.md"`, `BUNDLE = Path("output/empresarial.bundle")`.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_build_enterprise_branch.py`:

```python
"""Regra de seleção do branch `empresarial`.

O que decide o que vai ao GitHub do BC é puro e mora aqui; a parte que mexe no
git (índice temporário, `commit-tree`, bundle) é conferida na Task 11 do plano,
contra o repositório real.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_enterprise_branch.py"
_spec = importlib.util.spec_from_file_location("build_enterprise", _SCRIPT)
build_enterprise = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_enterprise)


def test_selection_keeps_only_what_runs():
    tracked = [
        ".claude/settings.json", ".gitattributes", ".gitignore", ".python-version",
        ".github/prompts/matinal-triagem.prompt.md", ".superpowers/x.md",
        "AGENTS.md", "CLAUDE.md", "README.md", "README_empresarial.md",
        "arquivo/comentario_matinal/2026/09/20260922.md",
        "config/comentario_matinal/painel.toml",
        "docs/comentario_matinal/plantao/01-primeiro-dia.md",
        "etc/.env.exemplo",
        "exemplos/comentario_matinal/aprovados/.gitkeep",
        "notebooks/comentario_matinal/imagens.ipynb",
        "notebooks/comentario_matinal/plantao.ipynb",
        "notebooks/comentario_matinal/plantao_copilot.ipynb",
        "notebooks/informes_eventos/fomc/fomc_analysis.ipynb",
        "prompts/comentario_matinal/00_guia_de_estilo.md",
        "prompts/comentario_matinal/project_instructions.md",
        "pyproject.toml", "scripts/build_enterprise_branch.py",
        "src/comentario_matinal/_backend_claude.py",
        "src/comentario_matinal/modelo.py",
        "src/comentario_matinal/wiki.py",
        "src/reports/_backend_claude.py", "src/reports/_modelo.py",
        "templates/informes_eventos/fomc.dotx",
        "tests/comentario_matinal/test_modelo.py", "uv.lock",
    ]
    assert build_enterprise.select_paths(tracked) == [
        ".gitattributes",
        ".github/prompts/matinal-triagem.prompt.md",
        ".python-version",
        "config/comentario_matinal/painel.toml",
        "etc/.env.exemplo",
        "notebooks/comentario_matinal/imagens.ipynb",
        "notebooks/comentario_matinal/plantao_copilot.ipynb",
        "notebooks/informes_eventos/fomc/fomc_analysis.ipynb",
        "prompts/comentario_matinal/00_guia_de_estilo.md",
        "pyproject.toml",
        "src/comentario_matinal/modelo.py",
        "src/reports/_modelo.py",
        "templates/informes_eventos/fomc.dotx",
        "uv.lock",
    ]


def test_gitignore_loses_claude_lines_and_gains_the_branch_rules():
    text = "# --- Editores ---\n.claude/settings.local.json\n.vscode/\n\n\n/input/\n"
    out = build_enterprise.gitignore_for_branch(text)
    assert "claude" not in out.lower()
    assert ".vscode/" in out and "/input/" in out
    assert "/arquivo/" in out.splitlines()
    assert "/etc/.env" in out.splitlines()
    assert "\n\n\n" not in out


def test_pyproject_loses_the_wiki_publisher_only():
    text = (
        '[project.scripts]\nmatinal = "comentario_matinal.cli:main"\n'
        'publica-wiki = "comentario_matinal.wiki:main"\n\n[build-system]\n'
    )
    out = build_enterprise.pyproject_for_branch(text)
    assert "publica-wiki" not in out
    assert 'matinal = "comentario_matinal.cli:main"' in out
    assert "[build-system]" in out


@pytest.mark.parametrize("path, content, expected", [
    ("src/x.py", b"# usa o Claude Code", True),
    ("src/x.py", b"# nada aqui", False),
    ("README.md", b"CLAUDE.md", True),
    ("templates/x.dotx", b"PK\x03\x04 claude", False),  # binário não é lido
])
def test_mentions_claude(path, content, expected):
    assert build_enterprise.mentions_claude(path, content) is expected
```

Run: `uv run pytest tests/test_build_enterprise_branch.py -q` — Expected: FAIL (script ausente).

- [ ] **Step 2: Escrever `scripts/build_enterprise_branch.py`**

Partir do `C:\Users\mmart\Github\marc3lom\py-mpc\scripts\build_enterprise_branch.py` (ler inteiro antes). Mantém: `_git`, `_ls_tree`, `_hash`, `_branch_tip`, `_config`, `_identity_env`, a montagem por índice temporário, o `commit-tree` com `-S` quando `commit.gpgsign`, o `update-ref` com o valor antigo, `--dry-run`, `--base`. Sai: tudo de LFS e de `in/`. Muda o docstring (a regra de seleção deste repositório, abaixo) e a seleção:

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
BRANCH = "empresarial"
README_SOURCE = "README_empresarial.md"
BUNDLE = REPO_ROOT / "output" / "empresarial.bundle"

INCLUDED_DIRS = ("src/", "notebooks/", "prompts/", "templates/", "config/",
                 ".github/prompts/", "etc/")
ROOT_FILES = ("pyproject.toml", "uv.lock", ".python-version", ".gitattributes")
EXCLUDED = frozenset({
    "notebooks/comentario_matinal/plantao.ipynb",
    "prompts/comentario_matinal/project_instructions.md",
    "src/comentario_matinal/wiki.py",
})
# Arquivos de texto: só neles a busca por menção ao backend local faz sentido.
TEXT_SUFFIXES = (".py", ".ipynb", ".md", ".toml", ".lock", ".txt", ".exemplo",
                 ".gitignore", ".gitattributes", ".python-version")

BRANCH_IGNORE = """
# --- Deste branch --------------------------------------------------------------
# O arquivo de comentários enviados é de cada máquina e nunca vai ao repositório.
/arquivo/
# Segredos locais (a chave do FRED): cada um administra o seu.
/etc/.env
"""


def select_paths(tracked: list[str]) -> list[str]:
    """Os caminhos da base que vão ao branch, ordenados (sem .gitignore e README)."""
    def keep(path: str) -> bool:
        if path in EXCLUDED or Path(path).name.startswith("_backend_"):
            return False
        return path in ROOT_FILES or path.startswith(INCLUDED_DIRS)
    return sorted(p for p in tracked if keep(p))


def strip_claude_lines(text: str) -> str:
    # igual ao do py-mpc


def gitignore_for_branch(text: str) -> str:
    return strip_claude_lines(text).rstrip("\n") + "\n" + BRANCH_IGNORE


def pyproject_for_branch(text: str) -> str:
    """Tira o publicador do manual: ele escreve no GitHub pessoal do autor."""
    return "".join(line for line in text.splitlines(keepends=True)
                   if not line.startswith("publica-wiki ="))


def mentions_claude(path: str, content: bytes) -> bool:
    if not path.endswith(TEXT_SUFFIXES) and Path(path).name not in TEXT_SUFFIXES:
        return False
    return b"claude" in content.lower()
```

Em `build(base, dry_run, bundle)`: montar `lines` com os caminhos de `select_paths`; `pyproject.toml` entra por `_hash(pyproject_for_branch(...))`; `.gitignore` por `_hash(gitignore_for_branch(...))`; `README_empresarial.md` entra com o blob dela sob o caminho `README.md` (erro se não existir na base). Para cada arquivo que entra (inclusive os transformados), ler o conteúdo e, se `mentions_claude`, **acumular**; ao fim, se a lista não estiver vazia, imprimir cada caminho em stderr e `raise SystemExit(f"{len(...)} file(s) mention the local backend; branch not updated")` — antes de qualquer `write-tree`. A mensagem de commit: `f"Sincroniza com a origem ({base_sha[:7]})\n\n{len(lines)} arquivos: o necessário para rodar os notebooks.\n"`. Com `bundle=True`, depois do `update-ref` (ou quando nada mudou), rodar `_git("bundle", "create", str(BUNDLE), BRANCH)` e imprimir o caminho. `main()` ganha `--bundle`.

- [ ] **Step 3: Escrever `README_empresarial.md`**

Sem a palavra "claude" em lugar algum. Conteúdo:

```markdown
# mkt_intel

Disseminação de informação e inteligência de mercado da Mesa de Investimentos
(DEPIN/DIRIN): o **comentário matinal** e os **informes de eventos** (FOMC e payroll).
Tudo roda em notebooks, no VS Code, com o GitHub Copilot nas etapas de texto.

## Do que precisa

VS Code (com as extensões Python, Jupyter e GitHub Copilot, logado), Python 3.14, uv,
git e acesso a este repositório. O terminal Bloomberg aberto e logado, na mesma
máquina, para as coletas.

## Instalação (uma vez)

    git clone <endereço deste repositório>
    cd mkt_intel
    uv sync
    uv run nbstripout --install

O `nbstripout` tira as saídas dos notebooks antes de qualquer commit: elas carregam
dados de mercado e texto ainda não enviado.

Para o payroll (fallback do FRED): copiar `etc/.env.exemplo` para `etc/.env` e pôr a
sua chave do FRED (gratuita, em https://fred.stlouisfed.org/docs/api/api_key.html).
O `etc/.env` é seu e nunca vai ao repositório.

No VS Code: abrir a pasta `mkt_intel`, abrir um notebook e escolher o kernel `.venv`.

## Comentário matinal

Notebook: `notebooks/comentario_matinal/plantao_copilot.ipynb`. As fontes do dia, em
PDF, vão em `input/comentario_matinal/`. O comentário do dia anterior é opcional: se
você o tiver, salve-o em PDF ali mesmo com nome começando por `anterior`.

Nas três etapas de texto a célula grava a mensagem e espera. Abra o chat do Copilot
(Ctrl+Alt+I), escolha o modo **Agente** e digite o comando que a célula pedir:
`/matinal-triagem`, `/matinal-redacao`, `/matinal-revisao`. Quando o Copilot gravar a
resposta, a célula continua sozinha.

Depois de enviado o e-mail, no terminal: `uv run matinal enviado`. Ele arquiva o
comentário em `arquivo/` (só nesta máquina) e esvazia `input/` e `output/` do dia.

## Informes de eventos

- FOMC: `notebooks/informes_eventos/fomc/fomc_analysis.ipynb`. Pasta do dia:
  `input/informes_eventos/fomc/<AAAAMMDD>/`. Etapas de texto: `/fomc-resumo`,
  `/fomc-bancos`, `/fomc-revisao`, do mesmo jeito.
- Payroll: `notebooks/informes_eventos/payroll/`.

## Sigilo

Nunca comitar `input/`, `output/`, `arquivo/` nem `etc/.env` (o `.gitignore` já os
exclui). Nunca colar fonte, número de painel ou minuta em commit, issue ou chat fora
daqui.

## Quando algo dá errado

- **A célula acusa "não foi lida até o fim" ou "código de outra execução":** rodar a
  célula de novo e repetir o comando no chat.
- **O comando `/matinal-…` não aparece no chat:** conferir que a pasta aberta no VS
  Code é a raiz do repositório e que o chat está no modo Agente.
- **Bloomberg sem dados (`no cached response`):** o terminal pode abrir sem o
  `bbcomm`; iniciar `C:\blp\...\bbcomm.exe` à mão e rodar a célula de novo.
- **`git` sem acesso ao GitHub pela rede do BC:** configurar o proxy no repositório
  (`git config http.proxy …`, `http.proxyAuthMethod negotiate`, `http.sslBackend schannel`).
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_build_enterprise_branch.py -q` — PASS. Run: `uv run python scripts/build_enterprise_branch.py --dry-run` — Expected: lista de arquivos, "dry run: branch not updated", **nenhuma** menção acusada. Se acusar, corrigir o arquivo acusado (reescrever o comentário/texto sem a palavra) e repetir.

- [ ] **Step 5: Documentação, portão e commit**

`AGENTS.md` da raiz: acrescentar `scripts/` à lista de pastas, e ao fim:

```markdown
## Branch empresarial

O branch órfão `empresarial` é a cópia que vai ao GitHub do BC: só o que os notebooks
precisam, sem nada que cite o backend local. Regenerar com
`uv run python scripts/build_enterprise_branch.py` (`--dry-run`, `--bundle`); a regra
de seleção vive só no script. O e-mail dos commits vem de `git config
empresarial.email`. O push ao BC é do autor, pelo bundle, a partir da máquina do BC.
```

Run: `uv run pytest -q` — verde.

```bash
git add scripts/build_enterprise_branch.py tests/test_build_enterprise_branch.py README_empresarial.md AGENTS.md
git commit   # "Escreve o gerador do branch que vai ao GitHub do BC"
```

---

### Task 11: Gerar e validar o branch, e o bundle

Nada de código novo; é a verificação que a Task 10 não alcança. O branch é local — nada é empurrado.

- [ ] **Step 1: Identidade dos commits do branch**

Perguntar ao usuário o e-mail corporativo (no `py-mpc` foi `marcelo.martinelli@bcb.gov.br`) e rodar `git config empresarial.email <e-mail>`.

- [ ] **Step 2: Gerar**

Run: `uv run python scripts/build_enterprise_branch.py`
Expected: `empresarial -> <sha>`. Run: `git log --format='%an <%ae>%n%B' -1 empresarial` — autor com o e-mail corporativo, mensagem sem trailer.

- [ ] **Step 3: Validar num worktree descartável**

```bash
git worktree add "<scratchpad>/empresarial" empresarial
cd "<scratchpad>/empresarial"
git grep -n -i claude; echo "exit=$?"            # esperado: nenhuma linha, exit=1
ls -a                                              # sem AGENTS.md, CLAUDE.md, docs/, tests/, arquivo/
uv sync --frozen
uv run python -c "import comentario_matinal.plantao, comentario_matinal.modelo as m, reports.fomc.core.drafting, reports.payroll.core.data_loader, reports._modelo as r; print(sorted(m.BACKENDS), m.backend_ativo().nome, sorted(r.BACKENDS), r.active_backend().name)"
```

Expected da última linha: `['copilot'] copilot ['copilot'] copilot`.

Depois: `cd` de volta à raiz do repositório e `git worktree remove "<scratchpad>/empresarial"`.

- [ ] **Step 4: Bundle**

Run: `uv run python scripts/build_enterprise_branch.py --bundle` — Expected: "already up to date" e o caminho `output/empresarial.bundle`. Run: `git bundle verify output/empresarial.bundle`.

- [ ] **Step 5: Entregar ao usuário**

Relatar: sha do branch, contagem de arquivos, resultado da validação, caminho do bundle. Os passos do BC (criar `mkt_intel` na organização, `git fetch <bundle> empresarial`, commit assinado, push) são dele. Atualizar a memória `copilot-e-branch-empresarial.md` com o estado.
