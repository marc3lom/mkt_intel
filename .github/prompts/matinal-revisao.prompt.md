---
name: matinal-revisao
description: Comentário matinal, etapa de revisão — lê a mensagem que o notebook preparou e grava a resposta
agent: agent
tools: ['read/readFile', 'edit/createFile', 'edit/editFiles']
---

Esta é uma etapa automatizada. Não converse: execute os passos abaixo, na ordem.

1. Leia o arquivo `output/comentario_matinal/copilot/revisao.mensagem.md` INTEIRO, da primeira à última
   linha. Ele é longo: leia em trechos sucessivos, sem pular nenhum, até chegar à
   seção "FIM DA MENSAGEM".
2. Siga as instruções desse arquivo como se fossem o seu pedido. Todo o material de
   trabalho está nele: não abra nenhum outro arquivo e não busque nada fora dele.
3. Grave a sua resposta, e somente ela, em `output/comentario_matinal/copilot/revisao.resposta.md`. A
   primeira linha é a linha de leitura pedida no fim da mensagem.
4. Não altere nenhum outro arquivo. No chat, responda apenas "Resposta gravada."
