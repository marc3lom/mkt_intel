"""O que o comando diz ao autor, e quando.

Os quatro avisos que a extração do `plantao.py` calou foram achados comparando
à mão a saída do comando novo com a do antigo. Cada um é uma linha que o autor
lê numa manhã em que algo já saiu do trilho, e nenhum estava preso por teste —
quem mexer nisto depois não terá os fixtures daquela comparação. Estes prendem.

Nenhum destes testes toca o Bloomberg: as três etapas de IA consomem material já
gravado em `saida/`, e a chamada ao modelo entra como dublê.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

from comentario_matinal.cli import main  # noqa: E402

MARCA = "20260817"
ASOF = "2026-08-17T07:40"

# O bloco direcional é o insumo que as três etapas leem como estado do mercado.
# A linha "Referência:" é a que dá o horário de redação.
PAINEL = """PAINEL DIRECIONAL
Referência: 17/08/2026 07:40 de Brasília (equivalente a 06:40 de Nova York)

O conteúdo não importa aqui; o que se afere é o que o comando diz em volta.
"""

REDACAO = """- Primeiro marcador da redação.
- Segundo marcador da redação.
- Terceiro marcador da redação.
- Quarto marcador da redação.

---

**BLOCO DE AUDITORIA**

Nada a auditar.
"""

REVISAO_LEGIVEL = """## 3) TEXTO REVISADO

```markdown
- Primeiro marcador revisado.
- Segundo marcador revisado.
- Terceiro marcador revisado.
- Quarto marcador revisado.
```
"""

# A seção existe, mas sem o bloco de código que o extrator exige. É a falha real
# que interrompe a revisão depois de o modelo já ter respondido.
REVISAO_ILEGIVEL = """## 3) TEXTO REVISADO

Esqueci o bloco de código.
"""

# O mesmo painel, gravado com um horário de redação longe do `--asof` que a Mesa
# passa. É o que dispara o aviso de divergência.
PAINEL_DE_OUTRA_HORA = PAINEL.replace("17/08/2026 07:40", "17/08/2026 09:30")

MARCADOR = "[[o modelo começou]]"


@dataclass(frozen=True)
class Mesa:
    """As três pastas do plantão, num diretório temporário."""

    saida: Path
    fontes: Path
    arquivo: Path

    def argv(self, *comando: str) -> list[str]:
        return ["matinal", *comando, "--asof", ASOF,
                "--saida", str(self.saida), "--fontes", str(self.fontes),
                "--arquivo", str(self.arquivo)]

    def grava(self, nome: str, conteudo: str) -> Path:
        caminho = self.saida / nome
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho


@pytest.fixture
def mesa(tmp_path):
    pastas = {nome: tmp_path / nome for nome in ("saida", "fontes", "arquivo")}
    for pasta in pastas.values():
        pasta.mkdir()
    return Mesa(**pastas)


@pytest.fixture
def modelo(monkeypatch):
    """Põe um dublê no lugar da chamada ao modelo.

    Devolve a função que o instala, para que cada teste escolha a resposta e, se
    lhe interessar a ordem, um marcador que o dublê escreve no stderr ao ser
    chamado.
    """
    def dubla(resposta: str, marcador: str | None = None):
        def roda(mensagem, etapa, destino, *, web, modelo):
            if marcador:
                import sys
                print(marcador, file=sys.stderr)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(resposta, encoding="utf-8")
            return resposta

        monkeypatch.setattr("comentario_matinal.etapas.roda", roda)

    return dubla


def _indice(linhas: list[str], trecho: str) -> int:
    for i, linha in enumerate(linhas):
        if trecho in linha:
            return i
    raise AssertionError(
        f"nenhuma linha do stderr contém {trecho!r}. Saiu isto:\n"
        + "\n".join(linhas)
    )


def test_enviado_sem_docx_avisa_que_arquivou_sem_conferir(mesa, monkeypatch, capsys):
    """O `.md` vai para o arquivo sem ter sido conferido — e é ele que amanhã vale.

    Sem o `.docx` não há contra o que comparar, e o que entra em `arquivo/` passa
    a ser lido pela triagem seguinte como "o comentário do dia anterior" sem que
    ninguém tenha garantido que é o texto que a diretoria recebeu. O aviso é a
    única sinalização disso, e ele sai num caminho que termina com código 0.

    A ordem também é aferida: `enviado.arquiva` escreve a sua própria linha logo
    depois, e as duas se leem como uma frase só.
    """
    mesa.grava(f"comentario_{MARCA}.md", "- Um marcador.\n\n- Outro marcador.\n")
    monkeypatch.setattr("sys.argv", mesa.argv("enviado", "--forcar"))

    assert main() == 0

    linhas = capsys.readouterr().err.splitlines()
    sem_conferir = _indice(linhas, "não há .docx da data")
    assert sem_conferir < _indice(linhas, "arquivando sem ele"), (
        "o aviso de que o arquivamento foi sem conferência precisa vir antes do "
        "de `enviado.arquiva`; fora de ordem, a segunda linha parece explicar a "
        "primeira quando é o contrário."
    )


def test_enviado_que_falha_nao_repete_o_aviso(mesa, monkeypatch, capsys):
    """O aviso já mostrado não sai de novo junto com o erro.

    Ele viaja duas vezes de propósito — sai na hora em que aparece e volta na
    exceção, para que um notebook possa relê-lo depois. Quem escreve na tela é
    que precisa conciliar as duas coisas.
    """
    monkeypatch.setattr("sys.argv", mesa.argv("enviado", "--forcar"))

    assert main() == 1

    linhas = capsys.readouterr().err.splitlines()
    repetidas = [l for l in linhas if "não há .docx da data" in l]
    assert len(repetidas) == 1, f"o aviso saiu {len(repetidas)} vezes"


@pytest.mark.parametrize("etapa, fala_do_arquivo", [
    ("triagem", True),
    ("revisao", True),
    ("redacao", False),
])
def test_anterior_inexistente_so_e_assunto_de_quem_o_recebe(
        mesa, monkeypatch, capsys, modelo, etapa, fala_do_arquivo):
    """A redação não recebe o comentário do dia anterior, e não reclama dele.

    Reclamar seria pior do que calar: manda o autor procurar um arquivo que a
    etapa não usaria de todo jeito. Quais etapas o recebem é regra do núcleo
    (`plantao.COM_ANTERIOR`), e a fachada consulta em vez de repetir.
    """
    mesa.grava(f"painel_{MARCA}.txt", PAINEL)
    extras = []
    if etapa == "revisao":
        mesa.grava(f"redacao_{MARCA}.md", REDACAO)
        modelo(REVISAO_LEGIVEL)
    elif etapa == "redacao":
        mesa.grava(f"triagem_{MARCA}.md", "## C) ALERTAS\n\nNenhum.\n")
        extras = ["--temas", "dominante | segundo"]
        modelo("saída do dublê\n")
    else:
        modelo("saída do dublê\n")

    ausente = mesa.saida.parent / "nao_existe.md"
    monkeypatch.setattr("sys.argv",
                        mesa.argv(etapa, *extras, "--anterior", str(ausente)))

    assert main() == 0

    erro = capsys.readouterr().err
    if fala_do_arquivo:
        assert str(ausente) in erro, (
            f"a {etapa} recebe o comentário do dia anterior; um --anterior que "
            "não existe precisa ser dito, senão a checagem some em silêncio."
        )
    else:
        assert str(ausente) not in erro, (
            "a redação não recebe o comentário do dia anterior; avisar sobre o "
            "arquivo manda o autor caçar o que não seria usado."
        )


def test_revisao_ilegivel_mostra_o_caminho_do_que_o_modelo_devolveu(
        mesa, monkeypatch, capsys, modelo):
    """Falhar ao extrair não pode esconder onde a resposta ficou gravada.

    O modelo já respondeu e a revisão já está em disco quando o extrator recusa
    o formato. Sem a linha de caminho, o autor recebe só o erro e não sabe qual
    arquivo abrir para salvar o trabalho à mão.
    """
    mesa.grava(f"painel_{MARCA}.txt", PAINEL)
    mesa.grava(f"redacao_{MARCA}.md", REDACAO)
    modelo(REVISAO_ILEGIVEL)
    monkeypatch.setattr("sys.argv", mesa.argv("revisao", "--sem-anterior"))

    assert main() == 1

    saida = capsys.readouterr()
    destino = mesa.saida / f"revisao_{MARCA}.md"
    assert f"Revisao     {destino}" in saida.out, (
        "o caminho da revisão precisa sair na saída padrão, com o mesmo "
        f"alinhamento das outras etapas. Saiu: {saida.out!r}"
    )
    assert "não trouxe bloco de código" in saida.err


def test_avisos_da_etapa_chegam_antes_da_chamada_ao_modelo(
        mesa, monkeypatch, capsys, modelo):
    """Aviso que chega depois da espera não serve para decidir interromper.

    A chamada ao modelo leva minutos. "Sem fontes noticiosas" e "sem o
    comentário do dia anterior" são exatamente as duas coisas que fazem o autor
    parar, resolver e rodar de novo — e só valem enquanto ele ainda não esperou.
    """
    mesa.grava(f"painel_{MARCA}.txt", PAINEL)
    modelo("saída do dublê\n", marcador=MARCADOR)
    monkeypatch.setattr("sys.argv", mesa.argv("triagem"))

    assert main() == 0

    linhas = capsys.readouterr().err.splitlines()
    chamada = _indice(linhas, MARCADOR)
    for trecho in ("nenhum PDF aproveitado",
                   "falta o calendário em texto",
                   "nenhum comentário recente"):
        assert _indice(linhas, trecho) < chamada, (
            f"{trecho!r} saiu depois da chamada ao modelo; o autor só o leria "
            "quando a espera que ele evitaria já tivesse acontecido."
        )


@pytest.mark.parametrize("com_divergencia", [False, True])
def test_o_relatorio_da_conferencia_continua_saindo_com_as_mesmas_palavras(
        mesa, monkeypatch, capsys, com_divergencia):
    """O texto passou a ter um dono só, e estas são as linhas que o autor lê.

    As quatro frases existiam duas vezes — aqui e numa célula do notebook —, e
    agora saem de `enviado.relatorio_da_conferencia`. O que continua sendo de
    terminal é o destino de cada linha (stdout quando não há o que corrigir,
    stderr quando há) e o código de saída.
    """
    from comentario_matinal.enviado import Divergencia

    div = ([Divergencia(1, "o texto que está no md", "o texto que está no docx")]
           if com_divergencia else [])
    monkeypatch.setattr("comentario_matinal.plantao.confere", lambda ctx: div)
    monkeypatch.setattr("sys.argv", mesa.argv("conferir"))

    assert main() == (1 if com_divergencia else 0)

    saida = capsys.readouterr()
    if not com_divergencia:
        assert (f"Conferido:  o .docx e o .md dizem a mesma coisa ({MARCA})."
                in saida.out.splitlines())
        return

    linhas = saida.err.splitlines()
    assert "O .docx e o .md divergem em 1 marcador(es)." in linhas
    assert "  M1" in linhas
    assert ("Se a alteração foi intencional, repetir no .md antes de enviar: é "
            "ele que a triagem de amanhã lê como comentário do dia anterior."
            in linhas)


# O núcleo diz o que falta e para aí; a frase que ensina a suprir é de cada
# fachada, porque "rodar `uv run matinal`" é conselho errado numa célula de
# notebook. Estes prendem as frases do terminal, que não podem mudar.


@pytest.mark.parametrize("etapa, extras, com_painel, esperado", [
    ("triagem", [], False,
     ("Erro: falta o bloco direcional de 20260817. "
      "Rodar `uv run matinal` antes das etapas.")),
    ("redacao", ["--temas", "dominante"], True,
     "Erro: falta a triagem de 20260817. Rodar `uv run matinal triagem` antes."),
    ("revisao", ["--sem-anterior"], True,
     "Erro: falta a redação de 20260817. Rodar `uv run matinal redacao` antes."),
])
def test_a_instrucao_de_suprir_a_falta_continua_falando_de_terminal(
        mesa, monkeypatch, capsys, etapa, extras, com_painel, esperado):
    """A linha inteira, como o autor a lê às 7h da manhã.

    O núcleo passou a mandar só o fato — `falta a triagem de 20260817.` — e o
    comando volta a completá-lo. Se a emenda se perder, o autor fica sabendo o
    que falta e não o que digitar; se ela mudar de forma, a linha que ele
    aprendeu a reconhecer muda com ela.
    """
    if com_painel:
        mesa.grava(f"painel_{MARCA}.txt", PAINEL)
    monkeypatch.setattr("sys.argv", mesa.argv(etapa, *extras))

    assert main() == 1

    assert esperado in capsys.readouterr().err.splitlines(), (
        f"a linha de erro do terminal mudou; esperada: {esperado!r}"
    )


def test_a_instrucao_de_escolher_temas_continua_falando_de_terminal(
        mesa, monkeypatch, capsys):
    """A única falta cuja instrução entra no meio da frase, e não no fim.

    Ela não estava presa: a parametrização acima cobre os três códigos do
    `REMEDIO` e deixa de fora o `REMEDIO_NO_MEIO`. Quando `--temas-numeros`
    entrou e a frase mudou de forma, nada acusou — que é o defeito de sempre,
    numa suíte cujo trabalho é justamente acusar.
    """
    mesa.grava(f"painel_{MARCA}.txt", PAINEL)
    mesa.grava(f"triagem_{MARCA}.md", "### A) TEMAS CANDIDATOS\n")
    monkeypatch.setattr("sys.argv", mesa.argv("redacao"))

    assert main() == 1

    esperado = (
        "Erro: a redação precisa dos temas escolhidos pelo autor. "
        'Passar --temas-numeros "1,3,2", com os números da triagem e o '
        "dominante primeiro, ou --temas / --temas-arquivo para escrevê-los. "
        "A decisão editorial entre a triagem e a redação é humana."
    )
    assert esperado in capsys.readouterr().err.splitlines(), (
        "a linha que ensina a escolher os temas mudou"
    )


def test_o_aviso_de_asof_divergente_continua_nomeando_o_flag(
        mesa, monkeypatch, capsys, modelo):
    """O aviso é o mesmo fato nas duas fachadas, dito com vocabulários diferentes.

    O núcleo o entrega sem nomear flag alguma — num notebook o horário fixado é
    argumento de função, não `--asof` —, e o comando o reescreve na sua língua.
    """
    mesa.grava(f"painel_{MARCA}.txt", PAINEL_DE_OUTRA_HORA)
    modelo("saída do dublê\n")
    monkeypatch.setattr("sys.argv", mesa.argv("triagem", "--sem-anterior"))

    assert main() == 0

    esperado = ("Aviso: --asof (17/08 07h40) diverge da referência do painel "
                "(17/08 09h30). O painel é o material que a etapa analisa; "
                "conferir se é mesmo o do dia.")
    assert esperado in capsys.readouterr().err.splitlines(), (
        f"o aviso do terminal mudou; esperado: {esperado!r}"
    )


def test_o_terminal_tem_frase_para_todo_codigo_do_nucleo():
    """Código novo no núcleo sem frase na fachada some da tela em silêncio.

    O `REMEDIO.get(..., "")` não falha: ele imprime o fato e engole a instrução.
    Este teste é o que transforma esse silêncio em erro visível.
    """
    from comentario_matinal import plantao
    from comentario_matinal.cli import (
        AVISO,
        AVISO_INTACTO,
        REMEDIO,
        REMEDIO_NO_MEIO,
    )

    orfaos = sorted(set(plantao.REMEDIOS) - set(REMEDIO) - REMEDIO_NO_MEIO)
    assert not orfaos, (
        f"{orfaos} não tem frase no terminal. Ou entra em REMEDIO, ou em "
        "REMEDIO_NO_MEIO se a instrução não couber no fim da mensagem."
    )

    mudos = sorted(set(plantao.AVISOS) - set(AVISO) - AVISO_INTACTO)
    assert not mudos, (
        f"{mudos} não tem texto no terminal, e o aviso sairia na forma neutra "
        "do núcleo — que não nomeia flag alguma. Se a forma do núcleo já servir "
        "ao terminal, listar em AVISO_INTACTO com o motivo."
    )
