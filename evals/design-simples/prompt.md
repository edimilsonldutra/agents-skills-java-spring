---
tags: [gatilho, design]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

No LoanService, a renovação faz loan.setStatus(RENEWED), loan.setRenewals(loan.getRenewals() + 1) e loan.setDueDate(...), e o service recebe o objeto Message do SDK de chat para avisar o sócio. Também temos 30 ifs do tipo "se o empréstimo tem livros dos autores X e Y, ganha N dias a mais", e o negócio quer cadastrar novas combinações sem deploy. Como melhoro o design sem abandonar o layout flat-by-layer e o Dozer?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
