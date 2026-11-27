---
tags: [gatilho, java]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Nosso FineService guarda o total de multas do dia num campo BigDecimal e formata datas com um SimpleDateFormat em campo. Também protegemos a renovação com synchronized, mas a aplicação roda com 3 réplicas no Kubernetes. Sob carga aparecem totais e datas errados e renovações duplicadas. O que está errado e como corrijo?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
