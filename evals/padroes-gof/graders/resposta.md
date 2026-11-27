---
type: llm
weight: 1
---

Usa Composite para as regras combináveis (AllOf/AnyOf aninhados, cada regra testável isolada), troca a cadeia de instanceof por sealed interface com switch exaustivo (o equivalente moderno do Visitor, sem accept/visit manual) e desaconselha o barramento de comandos genérico entre controller e service quando não há fila, auditoria ou repetição que o justifique. O agente só tem ferramentas de leitura: orientar basta.
