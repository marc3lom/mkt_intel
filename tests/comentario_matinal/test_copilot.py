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
            f"﻿<!-- leitura: {lido} -->\ncom BOM", encoding="utf-8")

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
