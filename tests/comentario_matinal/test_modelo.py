"""A construção da chamada ao `claude`, que nenhum outro teste alcança.

Todos os demais testes põem um dublê no lugar de `modelo.executa` — é o que os
torna baratos e independentes de rede. O efeito colateral é que a única coisa
que o `modelo.py` de fato faz, montar a linha de comando, nunca foi aferida: uma
bandeira incompatível com a autenticação da máquina atravessou o repositório sem
acender nada e só apareceu às sete da manhã, no meio de um plantão, como
"`claude` saiu com código 1" sem motivo escrito.

Aqui o dublê desce um nível: entra no lugar do `subprocess.run`, e não da etapa.
Assim o comando, o ambiente e a stdin ficam visíveis, sem chamar o modelo nem
gastar um centavo.
"""

from __future__ import annotations

import subprocess

import pytest

from comentario_matinal import _backend_claude as backend
from comentario_matinal import modelo


class Chamada:
    """O que o `executa` mandou ao `subprocess.run`."""

    def __init__(self):
        self.comando: list[str] = []
        self.kwargs: dict = {}

    @property
    def env(self) -> dict:
        return self.kwargs.get("env") or {}


@pytest.fixture
def chamada(monkeypatch):
    """Põe um dublê no `subprocess.run` e devolve o que ele recebeu.

    O `shutil.which` também é dublado: o teste tem de rodar em máquina sem o
    Claude Code instalado — no CI, por exemplo — e o que se afere aqui é a
    montagem do comando, não a presença do executável.
    """
    vista = Chamada()

    def falso_run(comando, **kwargs):
        vista.comando = list(comando)
        vista.kwargs = kwargs
        return subprocess.CompletedProcess(
            comando, 0, stdout="resposta do dublê\n", stderr="")

    monkeypatch.setattr(backend.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(backend.subprocess, "run", falso_run)
    return vista


def executa(**kwargs):
    return backend.ClaudeCode().executa(
        "mensagem da etapa", etapa="triagem",
        **{"web": False, "modelo": None, **kwargs})


def test_o_comando_nao_pede_bare(chamada):
    """O `--bare` é incompatível com a assinatura, e o plantão roda nela.

    A bandeira desliga a descoberta de CLAUDE.md, hooks e skills — que é o que
    se quer, porque a etapa tem de render o mesmo resultado em qualquer máquina
    —, mas o preço está escrito no `--help`: com ela, "Anthropic auth is
    strictly ANTHROPIC_API_KEY or apiKeyHelper", e a sessão do Claude Code
    nunca é lida. Numa máquina autenticada por assinatura, toda etapa morre com
    código 1 antes de chegar ao modelo.
    """
    executa()
    assert "--bare" not in chamada.comando, (
        "O `--bare` voltou. Ele obriga chave de API paga e ignora a sessão do "
        "Claude Code — o plantão inteiro falha com código 1."
    )


def test_o_comando_isola_o_ambiente_do_plantonista(chamada):
    """Tirar o `--bare` não pode devolver o CLAUDE.md do plantonista à etapa.

    O isolamento é de carga: a triagem de quem está de plantão tem de ser a
    mesma de qualquer outro gestor, e este repositório tem um CLAUDE.md e um
    AGENTS.md na raiz que a CLI descobriria de dentro dele. O `--safe-mode`
    desliga a mesma lista que o `--bare` desligava — CLAUDE.md, skills,
    plugins, hooks, MCP, agentes — e, ao contrário dele, deixa a autenticação
    funcionar normalmente.
    """
    executa()
    assert "--safe-mode" in chamada.comando, (
        "Sem `--safe-mode`, a CLI descobre o CLAUDE.md, as skills e os hooks "
        "da máquina de quem está de plantão, e a etapa deixa de ser a mesma "
        "em toda máquina."
    )


def test_a_chave_de_api_nao_chega_ao_subprocesso(chamada, monkeypatch):
    """Uma chave esquecida no ambiente tem precedência sobre a assinatura.

    Foi esse o modo de falha real: um `ANTHROPIC_API_KEY` antigo, de conta sem
    saldo, sombreando uma assinatura perfeitamente válida. A CLI prefere a
    chave, a chave não paga, e a etapa morre. O backend declara por qual porta
    autentica em vez de depender do que sobrou no ambiente.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-de-conta-vazia")
    monkeypatch.setenv("PATH", "/usr/bin")

    executa()

    assert "ANTHROPIC_API_KEY" not in chamada.env, (
        "A chave de API chegou ao `claude`. Se ela estiver sem saldo ou for de "
        "outra conta, sombreia a assinatura e a etapa falha."
    )
    assert chamada.env.get("PATH") == "/usr/bin", (
        "O ambiente foi zerado em vez de podado: o `claude` precisa do PATH e "
        "do resto do ambiente para rodar."
    )


def test_a_falha_diz_o_motivo_ainda_que_ele_saia_pelo_stdout(
        chamada, monkeypatch):
    """"Saiu com código 1" sozinho custa quinze minutos de um plantão de duas horas.

    O código lia só o stderr, e a CLI escreve "Credit balance is too low" no
    stdout — então a mensagem chegava truncada justamente no pedaço que
    resolvia. Entre 7h e 9h não há tempo de reproduzir à mão o que o processo
    já tinha na tela.
    """
    def falso_run(comando, **kwargs):
        return subprocess.CompletedProcess(
            comando, 1, stdout="Credit balance is too low", stderr="")

    monkeypatch.setattr(backend.subprocess, "run", falso_run)

    with pytest.raises(modelo.ErroDoModelo) as erro:
        executa()

    assert "Credit balance is too low" in str(erro.value), (
        "O motivo da falha ficou fora da exceção. A CLI reporta pelo stdout "
        "quando sai com erro, e o stderr vem vazio."
    )


def test_a_mensagem_vai_pela_stdin_e_nao_por_argumento(chamada):
    """O limite de linha de comando do Windows fica em torno de 32 mil caracteres.

    A mensagem de uma etapa passa de 80 mil: só o guia de estilo tem 15 KB, e
    as fontes do dia são bem maiores. Passá-la como argumento daria um erro
    obscuro do sistema operacional, não um erro do pipeline.
    """
    executa()
    assert chamada.kwargs.get("input") == "mensagem da etapa"
    assert "mensagem da etapa" not in chamada.comando


def test_a_web_libera_so_as_ferramentas_de_web(chamada):
    """Sem `web`, nem busca nem leitura de página: a etapa só vê o dia dela.

    O risco não é a ferramenta, é o tema: com acesso à web, o modelo pode
    trazer para a triagem um assunto que não está nas fontes coletadas, e a
    revisão o classificaria como NÃO LOCALIZADO no melhor caso.
    """
    executa(web=False)
    assert "WebSearch" in chamada.comando and "WebFetch" in chamada.comando

    executa(web=True)
    assert "WebSearch" not in chamada.comando
    assert "WebFetch" not in chamada.comando
    assert "Bash" in chamada.comando, (
        "A bandeira `web` liberou mais do que a web."
    )


def test_o_modelo_so_e_fixado_quando_pedido(chamada):
    """Fixar o modelo no código esconderia uma decisão de custo dentro dele."""
    executa(modelo=None)
    assert "--model" not in chamada.comando

    executa(modelo="opus")
    assert chamada.comando[chamada.comando.index("--model") + 1] == "opus"


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


@pytest.mark.xfail(reason="o backend copilot nasce na Task 2", strict=True)
def test_a_variavel_vence_a_deteccao(monkeypatch):
    monkeypatch.setenv("COMENTARIO_MATINAL_BACKEND", "copilot")
    _desliga_opcionais(monkeypatch, True)
    assert modelo.backend_ativo().nome == "copilot"


def test_o_registro_nao_cita_backend_opcional_pelo_nome():
    """O `modelo.py` vai ao branch empresarial, que não pode mencionar o backend local."""
    from pathlib import Path

    texto = Path(modelo.__file__).read_text(encoding="utf-8").lower()
    assert "claude" not in texto
