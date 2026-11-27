---
tags: [gatilho, ia]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Queremos adicionar na API de biblioteca (Spring Boot 4) um assistente que recomenda livros usando OpenAI, busca sinopses e resenhas no PostgreSQL com pgvector e permite consultar os empréstimos ativos do sócio logado por tool calling, garantindo que um sócio nunca veja empréstimos ou anotações privadas de outro e sem travar o pool do banco enquanto a IA responde. Como estruturo isso?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
