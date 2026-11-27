# Kubernetes — Escala por Fila (KEDA), Nodes Spot, Workers, Jobs e CronJobs

Referência complementar de [`../SKILL.md`](../SKILL.md) para cargas em segundo plano, autoescalonamento por métricas externas e Jobs de migração.

---

## 1. Escalar consumidores pela fila (KEDA)

Um worker de fila fica ocioso de CPU enquanto as mensagens se acumulam: a métrica certa é a **profundidade da fila** ou o **lag** do grupo de consumidores. O KEDA cria e gerencia o HPA a partir dessas métricas:

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-workload-identity
  namespace: library
spec:
  podIdentity:
    provider: aws
    identityOwner: workload
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: notification-worker
  namespace: library
spec:
  scaleTargetRef:
    name: notification-worker
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: aws-workload-identity
      metadata:
        queueURLFromEnv: NOTIFICATION_QUEUE_URL
        queueLength: "20"
        awsRegion: us-east-1
```

- `queueLength` é quantas mensagens **uma** réplica dá conta (100 na fila e 20 por réplica → 5 réplicas); `identityOwner: workload` usa o IRSA/Pod Identity do próprio worker (`aws-eks`), que precisa também de `sqs:GetQueueAttributes`. Para Kafka, o trigger `kafka` com `bootstrapServers`, `consumerGroup`, `topic` e `lagThreshold`; réplicas acima do número de partições ficam ociosas (`kafka`).
- **Não crie um HPA próprio** para o mesmo Deployment (o KEDA já cria o dele) e remova `replicas`; `maxReplicaCount × pool` ≤ conexões do banco (`jvm-performance`).
- **`minReplicaCount: 0`** economiza, mas a primeira mensagem espera um pod subir (e, em Kafka, um rebalance): só para filas sem prazo curto. Confira a versão do KEDA instalada e a documentação do trigger (`library-docs`).

---

## 2. Separar cargas por node (Taints, Tolerations e Spot)

Workers e jobs tolerantes a interrupção podem rodar em nodes **Spot** (mais baratos, retomáveis pela AWS com aviso de dois minutos — `aws-eks`), e a API em nodes sob demanda. O node recebe um *taint* e só pods com a *toleration* correspondente vão para ele:

```yaml
      nodeSelector:
        workload-type: batch
      tolerations:
        - key: workload-type
          operator: Equal
          value: batch
          effect: NoSchedule
```

O consumidor em Spot precisa ser idempotente e ter shutdown curto; use *node affinity* preferida em vez de `nodeSelector` quando o posicionamento for preferência, não obrigação.

---

## 3. Workers, Jobs e CronJobs

| Trabalho | Recurso | Pontos de atenção |
|---|---|---|
| Consumidor contínuo de fila ou tópico | **Deployment** sem Service | Escala pela fila (KEDA, acima); `terminationGracePeriodSeconds` maior que o tempo de processar uma mensagem ou um lote; sem `preStop: sleep` (não há load balancer) |
| Tarefa única (reindexar, corrigir dados, migration pesada) | **Job** | Idempotente (o `backoffLimit` repete); `activeDeadlineSeconds`; `ttlSecondsAfterFinished` para limpar |
| Tarefa agendada | **CronJob** | `concurrencyPolicy: Forbid`; `timeZone`; idempotente |

**Worker**: no `SIGTERM`, o Spring para os listeners (`kafka`, `aws-s3-sqs`, `rabbitmq`) e termina a mensagem em andamento antes de sair; mensagem não confirmada volta para a fila e é reprocessada, por isso o consumidor é idempotente (`idempotency`). Mantenha startup e liveness pelo Actuator na porta de gestão; a readiness só controla o avanço do rollout, já que não há tráfego.

**CronJob** no lugar de `@Scheduled` quando a aplicação tem várias réplicas (o `@Scheduled` rodaria em todas — `concurrency`):

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: overdue-fines
  namespace: library
spec:
  schedule: "0 3 * * *"
  timeZone: "America/Sao_Paulo"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 600
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 3600
      template:
        spec:
          restartPolicy: Never
          priorityClassName: batch-low
          containers:
            - name: job
              image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.0.0
              args: ["--spring.main.web-application-type=none", "--app.job=overdue-fines"]
```

- A aplicação roda a tarefa (um `ApplicationRunner` ativado pela property) e **termina** com código de saída diferente de zero em caso de falha (`System.exit(SpringApplication.exit(context))`), senão o Job nunca falha.
- O Kubernetes garante "aproximadamente uma vez" por horário: em casos raros, um CronJob roda duas vezes ou nenhuma. Idempotência e alarme de "não rodou" (`observability`) cobrem os dois. Use o mesmo `securityContext`, recursos e segredos do Deployment (o exemplo os omite).

**Estado.** A regra do pacote é **banco e armazenamento gerenciados** (`aws-rds-secrets-manager`, `aws-s3-sqs`): a aplicação fica sem estado e escala livremente. StatefulSet com PersistentVolumeClaim só quando o próprio sistema é o armazenamento (um broker ou cache operado pelo time), com backup e restauração testados. Espaço temporário grande para processar arquivos usa **volume efêmero genérico** (um PVC criado e apagado com o pod), não o disco do node.

---

## 4. Migrations pesadas do Flyway em Job

Com várias réplicas subindo juntas, o Flyway serializa por lock (seguro), mas uma migration longa deixa o pod *not ready* e pode estourar o `startupProbe`. Para migrations pesadas, rode-as em um **Job** antes do deploy (e `spring.flyway.enabled=false` no Deployment):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: library-api-migrate-1-0-0
  namespace: library
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: migrate
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.0.0
          args:
            - "--spring.main.web-application-type=none"
            - "--spring.flyway.enabled=true"
          envFrom:
            - configMapRef:
                name: library-api-config
            - secretRef:
                name: library-api-secret
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

Com `web-application-type=none` a aplicação roda só o Flyway e encerra sem subir o servidor HTTP (ou use um entrypoint dedicado / Flyway CLI); o `securityContext` mantém compatibilidade com namespaces `restricted`. Para migrations rápidas o Flyway no startup é suficiente.
