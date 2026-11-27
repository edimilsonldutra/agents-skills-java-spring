---
type: llm
weight: 1
---

Explica que o bean é singleton e o campo mutável é compartilhado entre requests (estado vai para variável local ou para o banco), troca SimpleDateFormat por DateTimeFormatter, e mostra que synchronized só protege uma JVM: com 3 réplicas a renovação precisa de coordenação no banco (@Version, constraint ou SELECT FOR UPDATE), lock distribuído ou chave de idempotência. Sugere um teste de corrida com portão de largada. O agente só tem ferramentas de leitura: orientar basta.
