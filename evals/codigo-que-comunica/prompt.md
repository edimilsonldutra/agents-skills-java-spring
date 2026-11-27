---
tags: [gatilho, estilo]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Revise o estilo deste método do LoanService: ele se chama process(Long id, boolean flag), devolve null quando o sócio não tem empréstimos, guarda as tags do livro numa List que às vezes fica com repetidas, e no meio do método tem um laço de cálculo de multa de 40 linhas com 8 variáveis locais misturado com a montagem do e-mail de aviso. Como deixo esse código mais legível?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
