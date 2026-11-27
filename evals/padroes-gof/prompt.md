---
tags: [gatilho, design]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

A regra de renovação de empréstimo virou uma sequência de ifs aninhados (sem multa pendente E (estudante OU professor) E livro sem reserva), e cada tipo de item (livro impresso, e-book, revista) tem um if instanceof diferente para calcular a multa diária. Alguém sugeriu implementar o Visitor do GoF e um barramento de comandos entre controller e service. Qual padrão de projeto devo usar em cada parte?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
