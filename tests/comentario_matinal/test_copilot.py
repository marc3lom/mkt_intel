"""O backend que conversa com o Copilot do VS Code por arquivo.

Nenhum Copilot de verdade aqui: uma thread faz o papel do agente — espera o
arquivo de mensagem aparecer, junta os trechos do código de leitura e grava a
resposta entre a linha de leitura e a de fim.
"""

from __future__ import annotations

import re
import threading
import time

import pytest

from comentario_matinal import modelo

RE_TRECHO = re.compile(r"<!-- trecho de leitura (\d)/4: ([0-9a-f]+) -->")


@pytest.fixture
def pasta(monkeypatch, tmp_path):
    destino = tmp_path / "copilot"
    monkeypatch.setattr(modelo, "PASTA_COPILOT", destino)
    monkeypatch.setattr(modelo, "INTERVALO", 0.01)
    monkeypatch.setattr(modelo, "ESTAVEL", 0.05)
    monkeypatch.setattr(modelo, "TEMPO_LIMITE", 5)
    return destino


def codigo_da(texto: str) -> str:
    """O que o agente faz ao ler a mensagem inteira: junta os quatro trechos."""
    trechos = sorted(RE_TRECHO.findall(texto))
    assert [n for n, _ in trechos] == ["1", "2", "3", "4"], trechos
    return "".join(t for _, t in trechos)


def espera_o_pedido(pasta, etapa) -> str:
    pedido = pasta / f"{etapa}.mensagem.md"
    while not pedido.exists():
        time.sleep(0.01)
    time.sleep(0.02)
    return pedido.read_text(encoding="utf-8")


def agente(pasta, etapa, *partes, codigo=None, pausa=0.0, fim=True, bom=False):
    """Faz o papel do Copilot: grava a resposta em uma ou mais partes.

    A linha de fim só entra na última gravação — é o que um agente que grava em
    dois passos faz.
    """
    def age():
        pedido = espera_o_pedido(pasta, etapa)
        lido = codigo or codigo_da(pedido)
        resposta = pasta / f"{etapa}.resposta.md"
        texto = ("\ufeff" if bom else "") + f"<!-- leitura: {lido} -->\n"
        for i, parte in enumerate(partes):
            texto += parte
            final = texto + (f"\n<!-- fim: {lido} -->\n" if fim and i == len(partes) - 1 else "")
            resposta.write_text(final, encoding="utf-8")
            time.sleep(pausa)

    t = threading.Thread(target=age, daemon=True)
    t.start()
    return t


def executa(etapa="triagem", web=False, modelo_=None):
    return modelo.Copilot().executa("MENSAGEM DA ETAPA", etapa=etapa, web=web,
                                    modelo=modelo_)


def test_devolve_a_resposta_sem_as_linhas_de_leitura_e_de_fim(pasta):
    agente(pasta, "triagem", "## A) TEMAS\n\n| 1 | tema |\n")
    assert executa() == "## A) TEMAS\n\n| 1 | tema |"


def test_a_mensagem_leva_as_regras_o_pedido_e_os_trechos(pasta):
    agente(pasta, "triagem", "ok")
    executa()
    texto = (pasta / "triagem.mensagem.md").read_text(encoding="utf-8")
    assert texto.startswith(modelo.SYSTEM_PROMPT)
    assert "MENSAGEM DA ETAPA" in texto
    assert len(codigo_da(texto)) == 8


def test_os_trechos_ficam_espalhados_pela_mensagem():
    """Quem lê o começo e salta para o fim não conhece o código inteiro."""
    blocos = [f"parágrafo {i}\ncontinua {i}" for i in range(100)]
    mensagem = "\n\n".join(blocos)
    texto = modelo.mensagem_para_o_copilot(mensagem, "0123abcd")
    assert codigo_da(texto) == "0123abcd"

    posicao = {n: texto.index(f"trecho de leitura {n}/4") for n in "1234"}
    meio = texto.index("MENSAGEM DA ETAPA") if "MENSAGEM DA ETAPA" in texto else 0
    assert meio < posicao["1"] < texto.index("parágrafo 30")
    assert texto.index("parágrafo 40") < posicao["2"] < texto.index("parágrafo 60")
    assert texto.index("parágrafo 70") < posicao["3"] < texto.index("parágrafo 99")
    assert posicao["4"] > texto.index("FIM DA MENSAGEM")


def test_os_trechos_nao_partem_um_paragrafo():
    """Um trecho no meio de uma tabela a desmancharia para o modelo."""
    mensagem = "\n\n".join(f"| {i} | a |\n| {i} | b |" for i in range(40))
    texto = modelo.mensagem_para_o_copilot(mensagem, "0123abcd")
    corpo = texto[:texto.index("FIM DA MENSAGEM")].splitlines()
    onde = [i for i, linha in enumerate(corpo) if RE_TRECHO.search(linha)]
    assert len(onde) == 3
    for i in onde:
        assert not corpo[i - 1].strip() and not corpo[i + 1].strip(), corpo[i - 2:i + 3]


def test_codigo_de_outra_execucao_e_recusado(pasta):
    agente(pasta, "triagem", "ok", codigo="deadbeef")
    with pytest.raises(modelo.ErroDoModelo, match="outra execução"):
        executa()


def test_resposta_sem_linha_de_leitura_diz_que_a_mensagem_nao_foi_lida(pasta):
    def age():
        espera_o_pedido(pasta, "triagem")
        (pasta / "triagem.resposta.md").write_text(
            "só a resposta\n<!-- fim: 00000000 -->\n", encoding="utf-8")

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


def test_pausa_maior_que_a_estabilidade_nao_entrega_metade(pasta):
    """Entre duas gravações o modelo gera o texto: a pausa é de segundos, não de
    milissegundos, e passa da janela de estabilidade. Sem a linha de fim a
    primeira metade seria aceita."""
    agente(pasta, "redacao", "- primeira metade\n", "- segunda metade\n",
           pausa=0.3)
    assert executa("redacao") == "- primeira metade\n- segunda metade"


def test_resposta_sem_linha_de_fim_esgota_o_prazo_como_incompleta(pasta, monkeypatch):
    monkeypatch.setattr(modelo, "TEMPO_LIMITE", 0.4)
    agente(pasta, "triagem", "- só o começo\n", fim=False)
    with pytest.raises(modelo.ErroDoModelo, match="incompleta"):
        executa()


def test_resposta_velha_e_apagada_antes_da_espera(pasta):
    """A resposta de ontem na pasta não pode passar pela de hoje."""
    pasta.mkdir(parents=True)
    (pasta / "triagem.resposta.md").write_text(
        "<!-- leitura: 00000000 -->\nvelha\n<!-- fim: 00000000 -->\n", encoding="utf-8")
    agente(pasta, "triagem", "nova")
    assert executa() == "nova"


def test_resposta_com_bom_e_aceita(pasta):
    agente(pasta, "triagem", "com BOM", bom=True)
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


# --- os prompt files que o chat roda ----------------------------------------

FERRAMENTAS = "tools: ['read/readFile', 'edit/createFile', 'edit/editFiles']"


@pytest.mark.parametrize("etapa", ["redacao", "revisao", "triagem"])
def test_cada_etapa_tem_prompt_file_que_le_e_grava_onde_o_backend_espera(etapa):
    """O prompt file é o outro lado do backend: os caminhos têm de casar."""
    from comentario_matinal.config import PROMPT_ETAPA, RAIZ

    assert etapa in PROMPT_ETAPA
    caminho = RAIZ / ".github" / "prompts" / f"{modelo.COMANDO}-{etapa}.prompt.md"
    assert caminho.is_file(), f"falta {caminho}"
    texto = caminho.read_text(encoding="utf-8")
    pasta = modelo.PASTA_COPILOT.relative_to(RAIZ).as_posix()
    assert f"{pasta}/{etapa}.mensagem.md" in texto
    assert f"{pasta}/{etapa}.resposta.md" in texto
    assert FERRAMENTAS in texto, "o agente só lê e grava arquivos: sem terminal, sem web"
    assert "agent: agent" in texto
    assert "claude" not in texto.lower()
    assert "última linha" in texto, "o prompt file tem de pedir a linha de fim"
