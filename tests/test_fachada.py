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
