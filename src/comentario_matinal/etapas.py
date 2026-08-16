"""As três etapas de IA do plantão, encadeadas pelos arquivos de `saida/`.

Cada etapa monta a mensagem a partir do guia de estilo, do prompt da etapa e dos
insumos do dia, chama o modelo por `modelo.executa` e grava a saída. O que liga
uma etapa à seguinte são as seções que os prompts já especificam: os alertas da
triagem, o comentário e a auditoria da redação, e o bloco de código da revisão —
que é justamente o `.md` que `matinal --comentario` consome.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from comentario_matinal.modelo import executa

SEPARADOR = "\n\n" + "=" * 70 + "\n\n"

# Quando a web está liberada, o guia exige que o uso seja sinalizado. Sem isto o
# revisor não tem como saber que uma afirmação veio de busca, e não das fontes
# do dia — que é a distinção que a etapa de revisão precisa fazer.
INSTRUCAO_WEB = """
## USO DA WEB NESTA EXECUÇÃO

A busca na web está habilitada, e limitada ao que o prompt desta etapa permite:
confirmar dado já presente nas fontes anexas, nunca introduzir tema novo.

Registrar no bloco de auditoria, em item próprio, TODA consulta feita: qual
afirmação foi confirmada, e por qual busca. Se nenhuma consulta for feita,
registrar "nenhuma consulta à web".
"""


RE_REFERENCIA = re.compile(
    r"^Refer[êe]ncia:\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", re.MULTILINE
)


def referencia_do_painel(painel: str) -> datetime | None:
    """Lê o horário de referência do cabeçalho do bloco direcional.

    O horário de redação do plantão é o do término da coleta, que é quando o
    painel foi gerado. Usar o relógio da máquina faria a etapa afirmar um horário
    que não é o do material que ela está analisando — e a primeira coisa que uma
    triagem competente faz é reclamar dessa incoerência.
    """
    from zoneinfo import ZoneInfo

    m = RE_REFERENCIA.search(painel)
    if not m:
        return None
    d, mes, ano, h, mi = (int(g) for g in m.groups())
    return datetime(ano, mes, d, h, mi, tzinfo=ZoneInfo("America/Sao_Paulo"))


# Nome dos comentários arquivados: arquivo/AAAA/MM/AAAAMMDD.md.
RE_ARQUIVADO = re.compile(r"^(\d{8})\.md$")

# Distância máxima, em dias, entre o comentário arquivado e a data do plantão.
# Sexta para segunda são três dias; feriado emendado chega a cinco. Além de uma
# semana o texto deixa de ser "o do dia anterior" — e é sob esse rótulo que as
# etapas 1 e 3 o recebem, comparando o quadro de hoje com o que ele descreve.
JANELA_ANTERIOR = 7


def comentario_anterior(raiz: Path, asof: datetime,
                        janela: int = JANELA_ANTERIOR) -> tuple[Path, date] | None:
    """Acha o comentário arquivado mais recente antes do dia do plantão.

    As etapas 1 e 3 pedem o comentário do dia anterior — a triagem para julgar
    ineditismo do tema, a revisão para apanhar contradição não sinalizada. Exigir
    que alguém passasse ``--anterior`` todo dia significava, na prática, que o
    insumo chegava como "(não fornecido)" e as duas checagens não aconteciam.

    A busca é por data no nome do arquivo, não por data de modificação: o
    arquivamento é manual e pode ocorrer dias depois, mas o nome é a data de
    envio. Nada de futuro entra, para que reprocessar um plantão antigo não
    receba um comentário escrito depois dele.
    """
    if not raiz.exists():
        return None

    hoje = f"{asof:%Y%m%d}"
    candidatos = [
        (m.group(1), caminho)
        for caminho in raiz.glob("*/*/*.md")
        if (m := RE_ARQUIVADO.match(caminho.name)) and m.group(1) < hoje
    ]
    if not candidatos:
        return None

    marca, caminho = max(candidatos)
    data = date(int(marca[:4]), int(marca[4:6]), int(marca[6:]))
    if (asof.date() - data).days > janela:
        return None
    return caminho, data


def com_data(texto: str, data: date) -> str:
    """Carimba a data de envio no corpo do comentário anterior.

    O rótulo da entrada é "COMENTÁRIO DO DIA ANTERIOR" — é assim que os prompts
    das etapas 1 e 3 o nomeiam, e mudá-lo quebraria o casamento. Mas numa
    segunda-feira o texto é o de sexta, e a etapa precisa saber contra qual dia
    está comparando antes de acusar contradição.
    """
    return f"(enviado em {data:%d/%m/%Y})\n\n{texto.strip()}"


@dataclass(frozen=True)
class Insumos:
    """O material do dia, comum às três etapas."""

    guia: str
    fontes: str
    painel: str
    calendario: str
    asof: datetime
    anterior: str | None = None

    @property
    def horario(self) -> str:
        ny = self.asof.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
        return (f"{self.asof:%d/%m/%Y}, {self.asof:%Hh%M} de Brasília "
                f"(equivalente a {ny:%Hh%M} de Nova York)")


# --------------------------------------------------------------------------
# Extração de seções da saída do modelo
# --------------------------------------------------------------------------

def titulos(texto: str):
    """Percorre os títulos de Markdown, ignorando o que está em bloco de código.

    Sem isto, um `# comentário` dentro de uma cerca ``` seria lido como título e
    encerraria a seção ali — e é justamente dentro de uma cerca que a revisão
    entrega o texto final.
    """
    dentro = False
    for i, linha in enumerate(texto.splitlines()):
        if re.match(r"^\s*```", linha):
            dentro = not dentro
            continue
        if dentro:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if m:
            yield i, len(m.group(1)), m.group(2)


def secao(texto: str, *chaves: str) -> str | None:
    """Devolve o corpo da primeira seção cujo título contenha alguma das chaves.

    O casamento é tolerante de propósito: o modelo pode escrever "### C) ALERTAS",
    "## C — Alertas" ou "### Alertas". Prender-se a uma grafia exata quebraria o
    encadeamento por um detalhe de formatação.
    """
    linhas = texto.splitlines()
    inicio = nivel = None
    for i, grau, titulo in titulos(texto):
        if inicio is None:
            if any(c.lower() in titulo.lower() for c in chaves):
                inicio, nivel = i, grau
        elif grau <= nivel:
            return "\n".join(linhas[inicio + 1:i]).strip()
    if inicio is not None:
        return "\n".join(linhas[inicio + 1:]).strip()
    return None


def secao_ou_tudo(texto: str, rotulo: str, *chaves: str) -> str:
    """Extrai a seção; não achando, devolve o documento inteiro com aviso.

    Passar o documento inteiro é redundante, mas perder o insumo em silêncio é
    pior: a etapa seguinte rodaria sem os alertas e ninguém notaria.
    """
    corpo = secao(texto, *chaves)
    if corpo:
        return corpo
    print(f"Aviso: não localizei a seção {rotulo!r} na saída da etapa anterior. "
          "Passando o documento inteiro adiante — conferir se a etapa seguinte "
          "recebeu o que precisava.", file=sys.stderr)
    return texto


def texto_do_comentario(redacao: str) -> str:
    """Extrai o comentário da saída da redação.

    O prompt da etapa 2 pede os marcadores "sem cabeçalho", e o modelo obedece:
    a saída começa direto no primeiro marcador, sem o título "1) COMENTÁRIO".
    Procurar esse título falharia sempre. O que existe de fato é o título do
    bloco de auditoria, então o comentário é o que vem antes dele.
    """
    corpo = secao(redacao, "1) comentário", "1) comentario")
    if corpo:
        return corpo

    linhas = redacao.splitlines()
    for i, _, titulo in titulos(redacao):
        if "auditoria" in titulo.lower():
            return "\n".join(linhas[:i]).strip()

    print("Aviso: não localizei onde o comentário termina na saída da redação. "
          "Mandando o documento inteiro para a revisão.", file=sys.stderr)
    return redacao.strip()


class FormatoInesperado(RuntimeError):
    """A saída do modelo não veio no formato que o prompt especifica."""


def comentario_revisado(texto: str) -> str:
    """Extrai o bloco de código da seção 3 da revisão, validando o formato.

    Aqui não há tolerância. Este é o único ponto do fluxo em que a saída do
    modelo entra direto no documento enviado à diretoria: qualquer linha estranha
    dentro do bloco vira parágrafo do comentário. Falhar com mensagem clara é
    melhor do que gravar um .md que só se descobre malformado no Word.
    """
    alvo = secao(texto, "texto revisado") or texto
    blocos = re.findall(r"```[a-zA-Z]*\n(.*?)```", alvo, re.DOTALL)
    if not blocos:
        raise FormatoInesperado(
            "A seção '3) TEXTO REVISADO' não trouxe bloco de código. O prompt de "
            "revisão pede o texto final dentro de um bloco markdown, com uma "
            "linha '- ' por marcador. Extrair à mão e salvar antes de montar o "
            "documento."
        )

    linhas = [l.rstrip() for l in blocos[-1].strip().splitlines() if l.strip()]
    if not linhas:
        raise FormatoInesperado("O bloco de código da seção 3 veio vazio.")

    fora = [l for l in linhas if not l.lstrip().startswith("- ")]
    if fora:
        raise FormatoInesperado(
            f"{len(fora)} linha(s) do bloco de código não são marcadores. O bloco "
            "deve conter exclusivamente linhas iniciadas por '- ', sem título, "
            f"fecho ou comentário. Primeira: {fora[0][:70]!r}"
        )
    if not 4 <= len(linhas) <= 5:
        print(f"Aviso: o texto revisado tem {len(linhas)} marcadores, fora da "
              "faixa de 4 a 5 que o guia fixa.", file=sys.stderr)

    return "\n\n".join(linhas) + "\n"


# --------------------------------------------------------------------------
# Montagem das mensagens
# --------------------------------------------------------------------------

def _entrada(rotulo: str, corpo: str | None) -> str:
    if not corpo or not corpo.strip():
        return f"**[{rotulo}]**\n\n(não fornecido)"
    return f"**[{rotulo}]**\n\n{corpo.strip()}"


def _mensagem(prompt_etapa: str, ins: Insumos, entradas: list[str],
              web: bool) -> str:
    partes = [
        "# GUIA DE ESTILO (leitura obrigatória)\n\n" + ins.guia,
        "# INSTRUÇÕES DESTA ETAPA\n\n" + prompt_etapa,
        "# ENTRADAS\n\n" + "\n\n".join(entradas),
    ]
    if web:
        partes.append(INSTRUCAO_WEB.strip())
    return SEPARADOR.join(partes)


def mensagem_triagem(prompt: str, ins: Insumos, web: bool) -> str:
    return _mensagem(prompt, ins, [
        _entrada("HORÁRIO DE REDAÇÃO", ins.horario),
        _entrada("FONTES NOTICIOSAS", ins.fontes),
        _entrada("PAINEL DE GRÁFICOS", ins.painel),
        _entrada("CALENDÁRIO ECONÔMICO DO DIA", ins.calendario),
        _entrada("COMENTÁRIO DO DIA ANTERIOR", ins.anterior),
    ], web)


def mensagem_redacao(prompt: str, ins: Insumos, temas: str, alertas: str,
                     web: bool) -> str:
    return _mensagem(prompt, ins, [
        _entrada("TEMAS SELECIONADOS PELO AUTOR", temas),
        _entrada("HORÁRIO DE REDAÇÃO", ins.horario),
        _entrada("FONTES NOTICIOSAS", ins.fontes),
        _entrada("PAINEL DE GRÁFICOS", ins.painel),
        _entrada("CALENDÁRIO ECONÔMICO DO DIA", ins.calendario),
        _entrada("ALERTAS DA TRIAGEM", alertas),
    ], web)


def mensagem_revisao(prompt: str, ins: Insumos, texto: str, auditoria: str,
                     web: bool) -> str:
    return _mensagem(prompt, ins, [
        _entrada("TEXTO PARA REVISÃO", texto),
        _entrada("HORÁRIO DE REDAÇÃO", ins.horario),
        _entrada("FONTES NOTICIOSAS", ins.fontes),
        _entrada("PAINEL DE GRÁFICOS", ins.painel),
        _entrada("CALENDÁRIO ECONÔMICO DO DIA", ins.calendario),
        _entrada("BLOCO DE AUDITORIA DA REDAÇÃO", auditoria),
        _entrada("COMENTÁRIO DO DIA ANTERIOR", ins.anterior),
    ], web)


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------

def roda(mensagem: str, etapa: str, destino: Path, *, web: bool,
         modelo: str | None) -> str:
    saida = executa(mensagem, etapa=etapa, web=web, modelo=modelo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida, encoding="utf-8")
    return saida
