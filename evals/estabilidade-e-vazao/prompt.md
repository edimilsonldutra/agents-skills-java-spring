---
tags: [gatilho, entrega]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

A diretoria quer saber se o time está entregando bem. Fazemos deploy uma vez por mês, numa janela de fim de semana, a partir de uma branch de release que vive três semanas, o pipeline leva 45 minutos e metade dos deploys precisa de hotfix. Que métricas devemos acompanhar, como medimos a partir do GitHub Actions e do Argo CD, e o que mudar no pipeline e no processo?

(O projeto não está aberto nesta sessão: responda com a abordagem e os artefatos de referência do padrão, sem pedir o repositório.)
