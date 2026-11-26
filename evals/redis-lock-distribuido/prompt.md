---
tags: [gatilho, dados, redis]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Preciso implementar um lock distribuído e um rate limit atômico com Redis no Spring Boot 4 para evitar que dois pods rodem o mesmo job ao mesmo tempo. Posso reaproveitar a mesma instância de Redis do cache e usar DEL ao terminar e KEYS * para limpar?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
