---
tags: [gatilho, api]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Vamos abrir a API de empréstimos para uma rede de bibliotecas parceiras. Hoje o cliente renova um empréstimo mandando PUT /api/loan/v1/{id} com o campo status, e dois atendentes que editam o mesmo livro ao mesmo tempo sobrescrevem a alteração um do outro. Como redesenho esses endpoints?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
