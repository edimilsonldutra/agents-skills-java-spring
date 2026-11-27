---
tags: [gatilho, kubernetes]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Temos no EKS a API de empréstimos e um consumidor de SQS que envia notificações, os dois como Deployment com HPA por CPU. Na campanha de fim de ano a fila chegou a 50 mil mensagens e o consumidor não escalou. Também temos um @Scheduled que calcula multas às 3h e roda duplicado nas 4 réplicas. Como organizo isso no Kubernetes?

(O projeto não está aberto nesta sessão: responda com a abordagem e os manifests de referência do padrão, sem pedir o repositório.)
