# mkt_intel

Disseminação de informação e inteligência de mercado da Mesa de Investimentos
(DEPIN/DIRIN): o **comentário matinal** e os **informes de eventos** (FOMC e payroll).
Tudo roda em notebooks, no VS Code, com o GitHub Copilot nas etapas de texto.

## Do que precisa

- VS Code, com as extensões Python, Jupyter e GitHub Copilot (logado).
- Python 3.14, uv e git.
- Acesso a este repositório.
- Para as coletas: o terminal Bloomberg aberto e logado, na mesma máquina.

## Instalação (uma vez)

```
git clone <endereço deste repositório>
cd mkt_intel
uv sync
uv run nbstripout --install
```

O `nbstripout` tira as saídas dos notebooks antes de qualquer commit: elas carregam
dados de mercado e texto que ainda não foi enviado.

Para o payroll (fallback do FRED): copiar `etc/env.exemplo` para `etc/.env` e pôr a
sua chave do FRED, gratuita em https://fred.stlouisfed.org/docs/api/api_key.html. O
`etc/.env` é seu e nunca vai ao repositório.

No VS Code: abrir a pasta `mkt_intel` (a raiz do repositório, não uma subpasta),
abrir um notebook e escolher o kernel `.venv`.

## Comentário matinal

Notebook: `notebooks/comentario_matinal/plantao_copilot.ipynb`. As fontes do dia, em
PDF, vão em `input/comentario_matinal/`. O comentário do dia anterior é opcional: se
você o tiver, salve-o em PDF ali mesmo, com nome começando por `anterior`.

Nas três etapas de texto a célula grava a mensagem e espera. Abra o chat do Copilot
(Ctrl+Alt+I), escolha o modo **Agente** e digite o comando que a célula pedir:
`/matinal-triagem`, `/matinal-redacao` ou `/matinal-revisao`. Quando o Copilot gravar
a resposta, a célula continua sozinha.

Depois de enviado o e-mail, no terminal: `uv run matinal enviado`. Ele arquiva o
comentário em `arquivo/` (só nesta máquina) e esvazia o `input/` e o `output/` do dia.

## Informes de eventos

- FOMC: `notebooks/informes_eventos/fomc/fomc_analysis.ipynb`. Pasta do dia:
  `input/informes_eventos/fomc/<AAAAMMDD>/`. Etapas de texto: `/fomc-resumo`,
  `/fomc-bancos` e `/fomc-revisao`, do mesmo jeito.
- Payroll: `notebooks/informes_eventos/payroll/`.

## Sigilo

Nunca comitar `input/`, `output/`, `arquivo/` nem `etc/.env` — o `.gitignore` já os
exclui. Nunca colar fonte, número de painel ou minuta em commit, issue ou qualquer
coisa que saia da máquina.

## Quando algo dá errado

- **A célula acusa "não foi lida até o fim" ou "código de outra execução":** rodar a
  célula de novo e repetir o comando no chat.
- **O comando `/matinal-…` não aparece no chat:** conferir que a pasta aberta no VS
  Code é a raiz do repositório e que o chat está no modo Agente.
- **"FRED API key not found" com o `etc/.env` criado:** o Bloco de Notas costuma
  salvar como `etc/.env.txt`, e o Explorer esconde o `.txt`. O erro diz o nome real;
  renomear para `.env`.
- **Bloomberg sem dados (`no cached response`):** o terminal pode abrir sem o
  `bbcomm`; iniciar o `bbcomm.exe` de `C:\blp\` à mão e rodar a célula de novo.
- **O git não alcança o GitHub pela rede do BC:** configurar o proxy no repositório
  (`git config http.proxy …`, `git config http.proxyAuthMethod negotiate` e
  `git config http.sslBackend schannel`).
