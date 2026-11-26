---
type: llm
weight: 1
---

Justifica a escolha relacional (ACID / PC/EC no PACELC) para invariantes rígidas comparando com DynamoDB (PA/EL ou PA/EC, BASE), identifica o risco de write skew mesmo em REPEATABLE READ propondo lock pessimista no registro do leitor (SELECT FOR UPDATE) ou SERIALIZABLE com retry, e recomenda chave surrogate (BIGINT/UUIDv7, evitando UUIDv4/PII como PK) com índice composto colocando igualdade antes de faixa/ordenação. O agente só tem ferramentas de leitura: orientar basta.
