---
tags: [gatilho, mensageria]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

O serviço de empréstimos chama o catálogo por HTTP a cada empréstimo para saber o título e o status do livro, e o catálogo está virando gargalo. Já temos Kafka. Hoje o catálogo e o serviço de reservas publicam no mesmo tópico library.book.events, com um campo "action" que pode ser CREATE, UPDATE ou DELETE. Como redesenho esses eventos para o empréstimo não depender do catálogo em tempo real?

(O projeto não está aberto nesta sessão: responda com a abordagem e o código de referência do padrão, sem pedir o repositório.)
