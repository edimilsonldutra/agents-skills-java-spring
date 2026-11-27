---
type: llm
weight: 1
---

Troca o HPA por CPU do consumidor por um ScaledObject do KEDA com o trigger aws-sqs-queue (queueLength por réplica, identidade do workload, sem HPA próprio junto), trata o consumidor como worker sem Service com grace period maior que o processamento e idempotência, e move o cálculo de multas para um CronJob com concurrencyPolicy Forbid, timeZone e tarefa idempotente que termina com código de erro em falha. O agente só tem ferramentas de leitura: orientar basta.
