---
tags: [gatilho, refatoracao]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

O método importCopies(InputStream csv, boolean dryRun) do nosso service lê o CSV, valida cada linha, calcula a categoria do exemplar num for que também acumula os erros, e grava no banco, tudo num método de 120 linhas. Ele também devolve a contagem e altera um campo static com o total importado no dia. Os testes de integração existem e passam. Quais refatorações aplico e em que ordem, sem mudar o comportamento?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
