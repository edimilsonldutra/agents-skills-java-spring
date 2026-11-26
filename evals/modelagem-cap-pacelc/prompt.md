---
tags: [gatilho, dados, arquitetura]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Estamos modelando o sistema de empréstimos da biblioteca: um leitor pode ter no máximo 3 empréstimos ativos ao mesmo tempo, e queremos decidir entre PostgreSQL e DynamoDB usando CAP, PACELC e ACID × BASE, além de evitar que duas requisições concorrentes criem o 4º empréstimo mesmo em REPEATABLE READ. Como modelar as chaves, o controle de concorrência e o índice principal?

(O projeto não está aberto nesta sessão: responda com a análise e a modelagem de referência do padrão, sem pedir o repositório.)
