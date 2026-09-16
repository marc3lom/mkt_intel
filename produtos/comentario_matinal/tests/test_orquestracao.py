"""O caminho de coleta produz os mesmos quatro arquivos, com o mesmo conteúdo.

Os demais testes cobrem módulos. A orquestração — que ordem, que argumento, que
arquivo — não é exercitada por nenhum, e é justamente ela que a extração do
`plantao.py` move. Este teste é a rede: verde contra o `cli.main()` de hoje e
verde contra o núcleo extraído depois.
"""

from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

from comentario_matinal.config import carrega_config
from comentario_matinal.janela import fuso_local

# Onde os coletores estão ligados. ``from … import`` liga o nome no módulo que
# importa, então é lá que o monkeypatch precisa agir — não no módulo de origem.
# A Tarefa 2 muda esta linha, e só ela.
MODULO = "comentario_matinal.plantao"

MARCA = "20260817"


def _referencia(cfg) -> pd.DataFrame:
    tickers = [a.ticker for a in cfg.ativos]
    return pd.DataFrame(
        {
            "px_last": [100.0 + i for i in range(len(tickers))],
            "chg_net_1d": [0.5] * len(tickers),
            "chg_pct_1d": [0.5] * len(tickers),
        },
        index=tickers,
    )


def _intraday(cfg) -> dict[str, pd.Series]:
    """Dois ativos com barras, o resto sem — exercita o selo de mercado fechado."""
    tickers = [a.ticker for a in cfg.ativos]
    return {t: pd.Series([100.0, 100.5, 101.0]) for t in tickers[:2]}


def _eco() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "United States", "DATA": "2026-08-17", "HORÁRIO": "09:30",
         "EVENTO": "Empire Manufacturing", "PERÍODO": "Aug",
         "ESTIMATIVA": "10.0", "ATUAL": "-", "ANTERIOR": "15.6", "REVISADO": "-"},
        {"PAÍS": "China", "DATA": "2026-08-17", "HORÁRIO": "04:00",
         "EVENTO": "Retail Sales YoY", "PERÍODO": "Jul",
         "ESTIMATIVA": "1.5", "ATUAL": "0.6", "ANTERIOR": "1.0", "REVISADO": "-"},
    ])


def _bancos() -> pd.DataFrame:
    return pd.DataFrame([
        {"PAÍS": "Eurozone Aggregate", "DATA": "2026-08-17", "HORÁRIO": "06:30",
         "EVENTO": "ECB's Lane Speaks in Dublin"},
    ])


@pytest.fixture
def chamadas():
    """Registro mutável de quem foi chamado, com o quê.

    A aridade posicional das lambdas originais provava que o número de
    argumentos batia, nunca o valor: um ``asof`` errado ou a lista de ativos
    errada passariam sem que nenhum teste notasse. Este registro é o que
    fecha esse buraco — ``bloomberg_falsa`` grava aqui, e quem quiser
    inspecionar o que cada coletor recebeu pede este fixture junto.
    """
    return []


@pytest.fixture
def bloomberg_falsa(monkeypatch, chamadas):
    cfg = carrega_config()

    def _coleta_referencia(ativos):
        ref = _referencia(cfg)
        chamadas.append(("coleta_referencia", list(ativos), ref))
        return ref, []

    def _coleta_intraday(ativos, asof, ref):
        chamadas.append(("coleta_intraday", list(ativos), asof, ref))
        return _intraday(cfg)

    def _coleta_calendario():
        chamadas.append(("coleta_calendario",))
        return _eco(), _bancos()

    monkeypatch.setattr(f"{MODULO}.coleta_referencia", _coleta_referencia)
    monkeypatch.setattr(f"{MODULO}.coleta_intraday", _coleta_intraday)
    monkeypatch.setattr(f"{MODULO}.coleta_calendario", _coleta_calendario)
    return cfg


def test_coleta_produz_os_quatro_arquivos(bloomberg_falsa, monkeypatch, tmp_path):
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert (tmp_path / f"painel_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"calendario_{MARCA}.png").stat().st_size > 10_000

    md = (tmp_path / f"calendario_{MARCA}.md").read_text(encoding="utf-8")
    assert "CALENDÁRIO ECONÔMICO" in md
    assert "Empire Manufacturing" in md
    assert "ECB's Lane Speaks in Dublin" in md


def test_imagens_para_nas_duas_imagens(bloomberg_falsa, monkeypatch, tmp_path):
    """O caminho de quem escreve o texto por fora — o que o `daily` fazia.

    O bloco direcional existe para as etapas de IA: é dele que a revisão tira a
    direção de cada ativo para cobrar acordo com o texto. Quem não vai rodar
    etapa alguma não o quer, e gerá-lo assim mesmo deixaria em `saida/` um
    arquivo que ninguém escreveu e ninguém lê.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "imagens", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert (tmp_path / f"painel_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"calendario_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"calendario_{MARCA}.md").exists()
    assert not (tmp_path / f"painel_{MARCA}.txt").exists()


def test_imagens_nao_avisa_sobre_a_janela(bloomberg_falsa, monkeypatch, capsys,
                                          tmp_path):
    """Quem quer só as imagens não está de plantão, e a janela não é assunto dele.

    O aviso continua nascendo no núcleo — é o mesmo contexto —, mas esta fachada
    não o mostra, e o `notebooks/imagens.ipynb` também não. As duas dizendo
    coisas diferentes sobre o mesmo passo seria exatamente a divergência entre
    fachadas que o resto da suíte existe para impedir.

    A janela é forçada aqui: sem isso o teste passaria por acaso entre 7h e 9h,
    que é justamente quando ele não pode passar por acaso.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr("comentario_matinal.plantao.na_janela", lambda _: False)
    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "imagens", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert "DRY RUN" not in capsys.readouterr().err


def test_a_coleta_continua_avisando_sobre_a_janela(bloomberg_falsa, monkeypatch,
                                                   capsys, tmp_path):
    """A rede do teste acima: o silêncio é do `imagens`, não do comando inteiro.

    Sem esta contraparte, tirar o banner de todos os caminhos passaria verde — e
    o plantão perderia o aviso que existe para impedir que um ensaio das 15h
    seja enviado à diretoria.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr("comentario_matinal.plantao.na_janela", lambda _: False)
    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    assert "DRY RUN" in capsys.readouterr().err


def test_bloco_direcional_lista_todo_ativo_do_painel(bloomberg_falsa, monkeypatch,
                                                     tmp_path):
    """O bloco é o que as três etapas de IA leem como estado do mercado.

    Um ativo que suma dele some da triagem, da redação e da revisão de uma vez —
    e sem erro, porque nada afirma que ele deveria estar lá.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    texto = (tmp_path / f"painel_{MARCA}.txt").read_text(encoding="utf-8")
    assert "PAINEL DIRECIONAL" in texto
    assert "17/08/2026 07:40" in texto
    for ativo in bloomberg_falsa.ativos:
        assert ativo.rotulo in texto, f"{ativo.rotulo} sumiu do bloco direcional"


def test_coletores_recebem_o_material_certo_na_ordem_certa(bloomberg_falsa, chamadas,
                                                            monkeypatch, tmp_path):
    """A fiação entre os três coletores, não só a contagem de argumentos.

    ``coleta_intraday`` ancora a série intradiária no fechamento anterior — é o
    que faz a variação ler como a do dia, e não a da sessão (ver
    ``test_ancora_faz_a_variacao_ser_a_do_dia_e_nao_a_da_sessao`` em
    ``test_matinal.py``). Isso depende de três coisas que a Tarefa 2 pode
    embaralhar ao mover de onde ``asof`` flui: o ``asof`` que chega precisa ser
    o mesmo da linha de comando, a referência precisa ser exatamente o objeto
    que ``coleta_referencia`` devolveu, e a ordem de chamada precisa manter
    referência antes de intraday — inverter a ordem quebraria a âncora.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 0

    nomes = [c[0] for c in chamadas]
    assert nomes.index("coleta_referencia") < nomes.index("coleta_intraday"), (
        "coleta_intraday precisa da referência já coletada para ancorar a "
        "série no fechamento anterior; fora de ordem, essa âncora quebra."
    )

    _, ativos_ref, ref_devolvida = next(
        c for c in chamadas if c[0] == "coleta_referencia"
    )
    assert [a.ticker for a in ativos_ref] == [a.ticker for a in bloomberg_falsa.ativos]

    _, ativos_intraday, asof_recebido, ref_recebida = next(
        c for c in chamadas if c[0] == "coleta_intraday"
    )
    assert [a.ticker for a in ativos_intraday] == [a.ticker for a in bloomberg_falsa.ativos]
    assert asof_recebido == datetime(2026, 8, 17, 7, 40, tzinfo=fuso_local())
    assert ref_recebida is ref_devolvida, (
        "coleta_intraday recebeu uma referência diferente da que "
        "coleta_referencia devolveu — a âncora do fechamento anterior estaria "
        "olhando para o DataFrame errado."
    )


def test_referencia_vazia_aborta_sem_gravar_nada(monkeypatch, tmp_path):
    """Sem dado de referência algum, `main()` recusa prosseguir.

    A Tarefa 2 troca este ``return 1`` por uma exceção dedicada
    (``SemDadoDeMercado``); fixar o efeito aqui — código de saída 1, nenhum
    arquivo gravado — é o que prova que a tradução preservou o comportamento.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(f"{MODULO}.coleta_referencia",
                        lambda ativos: (pd.DataFrame(), []))
    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path)],
    )
    assert main() == 1
    assert list(tmp_path.iterdir()) == [], (
        "saída abortada não pode deixar arquivo parcial para trás"
    )


def test_sem_calendario_pula_a_consulta_e_nao_gera_a_tabela(bloomberg_falsa, chamadas,
                                                             monkeypatch, tmp_path):
    """``--sem-calendario`` existe para terminal sem licença BQL: não pode tocar o BQL.

    A Tarefa 2 troca a passagem do flag por uma chamada condicional a
    ``prepara_calendario`` na fachada; este teste fixa a forma de hoje — pular
    a consulta e as duas saídas de calendário, sem afetar painel nem bloco
    direcional — para que a extração tenha contra o que se aferir.
    """
    from comentario_matinal.cli import main

    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path),
         "--sem-calendario"],
    )
    assert main() == 0

    assert (tmp_path / f"painel_{MARCA}.png").stat().st_size > 10_000
    assert (tmp_path / f"painel_{MARCA}.txt").exists()
    assert not (tmp_path / f"calendario_{MARCA}.png").exists()
    assert not (tmp_path / f"calendario_{MARCA}.md").exists()
    assert not any(c[0] == "coleta_calendario" for c in chamadas), (
        "--sem-calendario existe para terminal sem licença BQL; tocar a "
        "consulta mesmo assim é o próprio bug que o flag existe para evitar."
    )


def test_sem_a_tabela_do_calendario_a_montagem_e_recusada(bloomberg_falsa,
                                                          monkeypatch, tmp_path,
                                                          capsys):
    """A recusa é do núcleo, e a linha do terminal continua a mesma.

    O template tem dois lugares de imagem, e sem a tabela do calendário um deles
    sairia vazio no documento que vai à diretoria. A checagem morava no `cli.py`,
    onde não alcançava o notebook — e nem este caminho, em que
    `--sem-calendario` deixa o `.png` sem gerar e a montagem estourava lá dentro
    com `FileNotFoundError`, que não é `ErroDePlantao`.
    """
    from comentario_matinal.cli import main

    comentario = tmp_path / "comentario.md"
    comentario.write_text("- Um marcador.\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["matinal", "--asof", "2026-08-17T07:40", "--saida", str(tmp_path),
         "--sem-calendario", "--comentario", str(comentario)],
    )
    assert main() == 1

    esperado = "Erro: sem a tabela do calendário não há como montar o documento."
    assert esperado in capsys.readouterr().err.splitlines(), (
        f"a linha de recusa do terminal mudou; esperada: {esperado!r}"
    )
    assert not (tmp_path / f"comentario_{MARCA}.docx").exists()
