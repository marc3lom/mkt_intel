# Configuração inicial (uma vez)

O plantão inteiro roda deste repositório. Não é preciso criar Project algum: as três
etapas de IA montam a mensagem com o guia de estilo e o prompt da etapa embutidos, a
partir dos arquivos de `prompts/`. O Project continua existindo como caminho
alternativo — ver [O Project do Claude](#o-project-do-claude), mais abaixo.

1. Instalar as dependências: `uv sync`.
2. Ter o `claude` no PATH, autenticado. É o backend padrão das etapas de IA.
3. Instalar o filtro de notebook: `uv run nbstripout --install`.

O passo 3 vale por clone, e é o que impede que um notebook executado leve para o
commit os dados de mercado e o texto do comentário — possivelmente antes de ele ter
sido enviado. O filtro tira as saídas no `git add`, sem tocar no arquivo aberto na
tela. Sem ele nada avisa na hora: quem percebe é o `tests/test_notebook.py`, que
existe como rede para o clone em que o passo foi esquecido.

O `uv sync` cria o `.venv` e instala tudo, inclusive o `blpapi`, que não vem do PyPI —
o `pyproject.toml` já aponta para o índice da Bloomberg. Rodar sempre do Windows nativo,
nunca do WSL: o `blpapi` conversa com o terminal por IPC local. A instalação não exige
terminal aberto; a execução do comando, sim.

Sempre que uma convenção mudar, editar `prompts/00_guia_de_estilo.md` e comitar. O
comando lê o arquivo do disco a cada execução, então a mudança vale no plantão
seguinte, sem mais nenhum passo. Quem usa o Project precisa substituir o arquivo lá
também. Não editar convenções nos prompts de etapa — eles apenas referenciam o guia.

## O Project do Claude

O Project é caminho alternativo, para o dia em que o comando não está à mão — máquina
sem o `claude` no PATH, terminal indisponível, etapa feita fora do posto. Os prompts
são exatamente os mesmos; o que o comando evita é o trabalho de anexar os arquivos e
o risco de anexar a versão errada.

Para montá-lo: criar um Project chamado "Comentário Matinal — DEPIN/DIRIN", colar
`prompts/project_instructions.md` nas instruções e anexar ao conhecimento os quatro
arquivos de `prompts/`. Escrever `etapa 1`, `etapa 2` ou `etapa 3`, com o horário de
redação e o material do dia anexo.

`project_instructions.md` não repete convenção alguma: extensão, disciplina numérica,
atribuição e janela temporal ficam no guia, e é de lá que o Project as lê. Manter uma
cópia dessas regras nas instruções do Project produziria duas fontes, e a segunda
envelheceria em silêncio na primeira revisão do guia.
