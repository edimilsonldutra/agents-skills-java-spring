---
tags: [gatilho, dados]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Preciso registrar quem criou e quem alterou cada livro e quando, e importar 200 mil empréstimos de uma planilha. A primeira tentativa de importação com repository.save em loop estourou a memória e levou 40 minutos. As entities usam GenerationType.IDENTITY. Como faço?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
