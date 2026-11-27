---
type: llm
weight: 1
---

Orienta usar o ChatClient (injetado via ChatClient.Builder no construtor, sem Lombok) fora de @Transactional do banco para não prender conexões, separar instruções de sistema da entrada do usuário contra prompt injection, filtrar a busca no VectorStore/pgvector por metadata no servidor e obter o sócio autenticado pelo SecurityContext dentro da @Tool (nunca aceitando userId escolhido pelo modelo, evitando vazamento entre sócios), além de configurar timeouts/limites na chamada ao provedor. O agente só tem ferramentas de leitura: orientar basta.
