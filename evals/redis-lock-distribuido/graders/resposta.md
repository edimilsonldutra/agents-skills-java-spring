---
type: llm
weight: 1
---

Desaconselha reaproveitar a mesma instância de Redis com eviction de cache para locks/rate limit (exigindo instância separada com noeviction), proíbe KEYS * em produção (orientando SCAN) e mostra liberação do lock por script Lua conferindo o token dono com SET NX PX atômico. O agente só tem ferramentas de leitura: orientar basta.
