---
name: kubernetes
description: Deploy de Spring Boot no Kubernetes — Deployment com rolling update sem downtime (e Recreate, blue/green), probes do Actuator, requests/limits e classes de QoS, PriorityClass, graceful shutdown, securityContext, Service, Ingress, ConfigMap/Secret, HPA, escala de consumidores pela fila com KEDA, taints e tolerations, PDB, workers, Jobs e CronJobs, segurança do namespace (Pod Security Admission, NetworkPolicy, ServiceAccount), Kustomize por ambiente, Flyway em Job e troubleshooting com kubectl. Use quando criar manifests ou investigar CrashLoopBackOff, OOMKilled ou pods not ready
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto e as convenções. Pré-requisitos: uma imagem no registry (`docker-and-docker-compose`) e as probes do Actuator (`observability`).

# Kubernetes

Manifests YAML **declarativos**, versionados no repositório, em `k8s/` (ou um chart — veja `helm-charts`). Nada de `kubectl run`/`edit` em produção: o estado do cluster vem do Git. Comentários seguem a preferência salva (default: sem).

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/kustomization.yaml
    └── prod/kustomization.yaml
```

---

## Configuração da aplicação para Kubernetes

```yaml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
  main:
    banner-mode: off

management:
  endpoint:
    health:
      probes:
        enabled: true
  server:
    port: 9090
```
- `server.shutdown: graceful`: ao receber `SIGTERM` o Spring **para de aceitar** requests novas e **termina** as em andamento (até o timeout) antes de encerrar. Sem isso, cada rolling update derruba requests no meio.
- O container deve receber o `SIGTERM` direto: use `ENTRYPOINT ["java", ...]` na forma **exec** (JSON), como em `docker-and-docker-compose`; a forma shell (`ENTRYPOINT java ...`) coloca um `sh` como PID 1 que engole o sinal.

---

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: library-api
  namespace: library
  labels:
    app.kubernetes.io/name: library-api
spec:
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: library-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: library-api
    spec:
      terminationGracePeriodSeconds: 45
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.0.0
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9090
          envFrom:
            - configMapRef:
                name: library-api-config
            - secretRef:
                name: library-api-secret
          env:
            - name: JAVA_TOOL_OPTIONS
              value: "-XX:MaxRAMPercentage=75"
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 512Mi
          startupProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            periodSeconds: 5
            failureThreshold: 30
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: management
            periodSeconds: 5
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["sleep", "10"]
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

Por que cada escolha:
- **`maxUnavailable: 0` + `maxSurge: 1`:** o novo pod precisa ficar *ready* antes de um antigo ser removido — zero downtime. Combine com `flyway-migrations` (expand → contract), porque as duas versões convivem.
- **Imagem com tag imutável** (`1.0.0` ou o SHA do commit) — **nunca `latest`**: com `latest` você não sabe o que está rodando e o rollback não é determinístico.
- **Probes** (veja `observability`): a **startup** dá até 30×5 s para a JVM + Flyway subirem *antes* de a liveness começar a contar — sem ela, uma aplicação lenta para iniciar é morta em loop (`CrashLoopBackOff`). **Liveness** só verifica o processo; **readiness** decide o tráfego. Liveness nunca depende de database.
- **`preStop: sleep 10` + `terminationGracePeriodSeconds: 45`:** o Kubernetes tira o pod do Service e manda o `SIGTERM` em paralelo; o `sleep` dá tempo de o load balancer parar de enviar tráfego antes do shutdown começar. A soma `preStop (10) + timeout-per-shutdown-phase (30)` deve caber no `terminationGracePeriodSeconds` (45).
- **Memória: `requests == limits`** e o `MaxRAMPercentage=75`: a JVM calcula o heap a partir do limite do container; estourar o limite é `OOMKilled` (exit 137). Dimensione olhando as metrics reais (`jvm.memory.*`), não adivinhando — veja `jvm-performance`.
- **CPU: defina `requests`, evite `limits` de CPU** na maioria dos casos: o limite causa *throttling* (a JVM e o GC ficam lentos, a latência p99 explode, principalmente no startup). Se a plataforma exigir limit, seja generoso.
- **`readOnlyRootFilesystem` + `emptyDir` em `/tmp`:** a JVM e o Tomcat escrevem em `/tmp`; o resto do filesystem fica imutável — uma invasão não consegue gravar binários.
- **`runAsNonRoot`**, `drop: ALL` e `seccompProfile: RuntimeDefault`: o baseline de segurança *Pod Security Standards "restricted"*.

### Estratégia de rollout

- **RollingUpdate** (acima) é o padrão: exige que a versão antiga e a nova **convivam** (banco com expand → contract, contrato compatível, consumidores que toleram as duas versões de evento).
- **Recreate** derruba todas as réplicas antes de subir as novas: há indisponibilidade, mas nenhuma convivência. Só quando as versões não podem rodar juntas (mudança incompatível fora do expand → contract, consumidor que não pode ter duas versões no mesmo grupo). **Blue/green**: dois Deployments (`-blue` e `-green`) e o Service aponta para um deles pelo seletor (`version: green`); a troca e o rollback são instantâneos, ao custo de capacidade dobrada durante a troca. Canary com porcentagem de tráfego pede ferramenta (Argo Rollouts, service mesh) ou feature flag na aplicação (`release-management`).

### Classes de QoS e prioridade

O Kubernetes despeja pods de um node sem memória na ordem: **BestEffort** (sem requests) → **Burstable** (requests menores que limits, ou só parte definida) → **Guaranteed** (requests == limits de CPU **e** memória em todos os contêineres). O Deployment acima, com memória igual e CPU sem limit, é **Burstable**: protegido pela memória certa, sem o throttling de CPU. Para a API não ser a primeira vítima quando um job pesado divide o node, crie uma `PriorityClass` (`scheduling.k8s.io/v1`, `value: 100000`, `globalDefault: false`) e use `priorityClassName: api-critical` no pod da API; jobs e workers descartáveis ficam com uma classe mais baixa. Prioridade alta também permite **preempção** (o scheduler remove pods de menor prioridade para encaixar o de maior): use poucas classes, com critério.

---

## Service e Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: library-api
  namespace: library
spec:
  selector:
    app.kubernetes.io/name: library-api
  ports:
    - name: http
      port: 80
      targetPort: http
```
Tipo `ClusterIP` (default): só acessível dentro do cluster. Para fora, use um **Ingress**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: library-api
  namespace: library
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
      secretName: library-api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: library-api
                port:
                  name: http
```
Na AWS o `ingressClassName` é `alb` e as annotations são outras — veja `aws-eks`. **Nota:** o controlador comunitário `kubernetes/ingress-nginx` entrou em aposentadoria em março de 2026; para clusters novos fora da AWS, prefira **Kubernetes Gateway API** (`HTTPRoute` com Envoy Gateway/Cilium/etc.) ou o controlador gerenciado do provedor. A porta de management (9090) **não** entra no Service/Ingress: só o kubelet e o Prometheus chegam nela.

---

## ConfigMap e Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: library-api-config
  namespace: library
data:
  SPRING_PROFILES_ACTIVE: prod
  SPRING_DATASOURCE_URL: jdbc:mysql://mysql.library.svc:3306/library_api
  CORS_ORIGINPATTERNS: https://app.example.com
```
- O Spring faz *relaxed binding* de variável de ambiente: `SPRING_DATASOURCE_URL` → `spring.datasource.url`; `CORS_ORIGINPATTERNS` → `cors.originPatterns`. O `application.yml` é o mesmo em todo ambiente.
- Dados **não sensíveis** no ConfigMap; **sensíveis** no Secret (`SPRING_DATASOURCE_PASSWORD`, `JWT_SECRET`).

**Secret nunca vai para o Git em texto/base64** — base64 não é criptografia. Opções, da melhor para a mais simples: **External Secrets Operator** sincronizando do AWS Secrets Manager (veja `aws-rds-secrets-manager`), **Sealed Secrets** (versiona o secret cifrado), ou `kubectl create secret` aplicado fora do Git por quem tem permissão:
```bash
kubectl -n library create secret generic library-api-secret \
  --from-literal=SPRING_DATASOURCE_PASSWORD='...' \
  --from-literal=JWT_SECRET="$(openssl rand -base64 48)"
```
Habilite a criptografia de secrets em repouso no cluster (KMS) e aplique RBAC mínimo para quem lê `secrets`.

---

## Escala e disponibilidade

**HPA** (`autoscaling/v2`) escala pelo uso de CPU em relação ao `request`:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: library-api
  namespace: library
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: library-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```
Requer o `metrics-server` e `resources.requests.cpu` definido. Com HPA, **remova `replicas`** do Deployment (ou o `kubectl apply` brigará com o HPA). Cuidado: cada réplica abre seu próprio pool de conexões — `maxReplicas × maximumPoolSize` não pode passar o limite de conexões do database (veja `jvm-performance`).

**PodDisruptionBudget** garante que manutenção do cluster (drain de node) nunca derrube todas as réplicas:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: library-api
  namespace: library
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: library-api
```
Para alta disponibilidade, espalhe as réplicas entre zonas: `topologySpreadConstraints` com `topologyKey: topology.kubernetes.io/zone` e `whenUnsatisfiable: ScheduleAnyway`.

## Workers, escala por fila (KEDA), Jobs, CronJobs e migrations pesadas

Nem todo pod atende HTTP. Para cargas em segundo plano, manifests completos de KEDA (`ScaledObject` + `TriggerAuthentication`), taints/tolerations em nodes Spot, `CronJob` e `Job` de migration do Flyway, leia [`references/workloads-and-autoscaling.md`](references/workloads-and-autoscaling.md). Resumo das decisões obrigatórias:

- **Consumidores contínuos de fila/tópico:** `Deployment` **sem Service**, escalado pela profundidade da fila ou lag do grupo com **KEDA** (`aws-sqs-queue`, `kafka`) — **nunca** por CPU e **nunca** criando um HPA próprio junto com o `ScaledObject` (remova `replicas:` e respeite `maxReplicaCount × pool ≤ max_connections`). `terminationGracePeriodSeconds` maior que o processamento de uma mensagem/lote, sem `preStop: sleep`.
- **Nodes Spot:** separe workers/jobs tolerantes a interrupção com `nodeSelector`/affinity + `tolerations` (`NoSchedule`); a API permanece em nodes sob demanda.
- **Jobs (tarefa única) e CronJobs (agendada):** use `CronJob` com `concurrencyPolicy: Forbid` e `timeZone` no lugar de `@Scheduled` quando há múltiplas réplicas; a aplicação roda com `--spring.main.web-application-type=none` e encerra com código de saída != 0 em falha (`System.exit(SpringApplication.exit(context))`). Sempre idempotentes (`backoffLimit`, `activeDeadlineSeconds`, `ttlSecondsAfterFinished`).
- **Migrations pesadas do Flyway:** rode em `Job` antes do deploy (`spring.flyway.enabled=false` no `Deployment`, `--spring.flyway.enabled=true` no `Job`, mantendo o perfil `restricted`); migrations rápidas rodam no startup.
- **Estado:** banco e objetos ficam em serviços gerenciados (`aws-rds-secrets-manager`, `aws-s3-sqs`); `StatefulSet` só para armazenamento operado pelo próprio time, e espaço temporário grande usa volume efêmero genérico.

---

## Segurança do namespace

O pod já segue o baseline *restricted*; o namespace garante que nenhum outro pod fuja dele e limita a rede:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: library
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: library
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
```
- **Pod Security Admission** com `restricted` recusa pods com root, privilégio ou capabilities extras (`warn` avisa no `kubectl apply`).
- **NetworkPolicy** começa negando tudo; depois, políticas que liberam o necessário: ingress do controlador de Ingress para a porta da aplicação, egress para o DNS do cluster, o banco e os serviços chamados. Só tem efeito se o CNI aplicar NetworkPolicy (no EKS, o VPC CNI com o suporte habilitado — `aws-eks`).
- **ServiceAccount** própria por aplicação, com `automountServiceAccountToken: false`: a API não conversa com o Kubernetes e não precisa de token nem de Role. Permissões na AWS vêm do IRSA/Pod Identity (`aws-eks`), não do RBAC do cluster.
- **Manter atualizado**: imagem base com patch (Dependabot/Renovate) e cluster na versão suportada; a atualização dos nodes drena pods respeitando o PDB.

## Kustomize (um conjunto de manifests, vários ambientes)

`base/kustomization.yaml` lista os recursos; cada overlay muda só o que difere:
```yaml
resources:
  - ../../base
namespace: library-prod
images:
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api
    newTag: 1.0.0
patches:
  - path: resources-patch.yaml
```
(Como o `hpa.yaml` já está em `base/`, ajuste `minReplicas`/`maxReplicas` do HPA por patch em vez de fixar `replicas:` no Deployment.) `kubectl apply -k k8s/overlays/prod`. O CI atualiza só o `newTag` (`kustomize edit set image`) a cada release. Para parametrização mais rica, ou distribuir o app como pacote, veja `helm-charts`. Para entregar **por GitOps** (o cluster **puxa** do Git em vez de o CI rodar `kubectl apply`), veja `argocd`.

---

## Operação e troubleshooting

```bash
kubectl apply -k k8s/overlays/prod
kubectl -n library-prod rollout status deployment/library-api --timeout=300s
kubectl -n library-prod rollout undo deployment/library-api
kubectl -n library-prod get pods -l app.kubernetes.io/name=library-api
kubectl -n library-prod logs deploy/library-api --tail=200 -f
kubectl -n library-prod describe pod <pod>
kubectl -n library-prod top pod
kubectl -n library-prod port-forward deploy/library-api 8080:8080
kubectl -n library-prod get events --sort-by=.lastTimestamp
```
Diagnóstico pelo status do pod:

| Status | Causa provável | Onde olhar |
|---|---|---|
| `ImagePullBackOff` | tag errada, registry privado sem credencial/permissão | `describe pod` → Events |
| `CrashLoopBackOff` | a aplicação cai ao subir (config/secret ausente, Flyway falhou) ou a liveness mata uma app lenta | `logs --previous` e o `startupProbe` |
| `OOMKilled` (exit 137) | limite de memória baixo para o heap | `describe pod` → Last State; `jvm-performance` |
| `Running` mas `0/1 Ready` | readiness falhando (database fora, porta/path errados) | `describe pod` → Readiness probe failed |
| `Pending` | sem capacidade/node, `requests` altos demais, PVC não ligado | `describe pod` → Events |
| `Evicted` | node sem memória/disco | `kubectl describe node` |
| `Pending` com "untolerated taint" ou "didn't match node affinity" | regra de posicionamento que nenhum node satisfaz | `describe pod` → Events; labels e taints dos nodes (`kubectl get nodes --show-labels`) |
| Job `BackoffLimitExceeded` | a tarefa falhou em todas as tentativas | `kubectl logs job/<nome>` e os pods do job |
| CronJob que não roda | `suspend: true`, horário perdido além do `startingDeadlineSeconds`, execução anterior ainda ativa com `Forbid` | `kubectl get cronjob`, `get jobs` |
| Pod recusado na criação ("violates PodSecurity") | o pod não cumpre o perfil `restricted` do namespace | os campos citados na mensagem (`runAsNonRoot`, `capabilities`, `seccompProfile`) |

---

## Regras principais

- Tudo declarativo e no Git; tag de imagem **imutável**, nunca `latest`.
- `startupProbe` + `liveness` (só processo) + `readiness` (tráfego); Actuator em porta separada; liveness nunca depende de database.
- `server.shutdown: graceful`, `preStop sleep`, e `terminationGracePeriodSeconds` > soma dos dois; `ENTRYPOINT` em forma exec.
- Rolling update com `maxUnavailable: 0`; migrations compatíveis com as duas versões (expand → contract).
- Memória `requests == limits` com `MaxRAMPercentage`; CPU com `requests`, evitando `limits`.
- Pod seguro: não-root, `readOnlyRootFilesystem`, `drop ALL`, `RuntimeDefault`; `emptyDir` em `/tmp`.
- Config por variável de ambiente (relaxed binding); secrets **fora do Git** (External Secrets/Sealed Secrets).
- HPA + PDB + `topologySpreadConstraints` para escala e disponibilidade; some `maxReplicas × pool` ≤ conexões do database.
- Rolling update quando as versões convivem; Recreate só quando não podem; blue/green pelo seletor do Service. `PriorityClass` para a API não ser despejada antes dos jobs.
- **Consumidores escalam pela fila** (KEDA), não pela CPU; workers e jobs tolerantes a interrupção em nodes separados (taint e toleration, Spot).
- **Workers** como Deployment sem Service e com grace period maior que o processamento; **Jobs** idempotentes com prazo e limpeza; **CronJob** com `concurrencyPolicy: Forbid` e `timeZone` no lugar de `@Scheduled` com várias réplicas.
- **Sem estado na aplicação**: banco e arquivos gerenciados; StatefulSet só para armazenamento operado pelo time.
- **Namespace seguro**: Pod Security Admission `restricted`, NetworkPolicy negando tudo e liberando o necessário, ServiceAccount própria sem token montado.
- Um overlay por ambiente (Kustomize) ou um chart (`helm-charts`).

## Referências

- William Denniss, *Kubernetes for Developers* (Manning, 2024): estratégias de rollout, QoS e prioridade, escala por métricas externas, seleção de nodes, workers, Jobs e CronJobs, aplicações com estado e segurança do namespace. Manifests do KEDA conferidos na documentação oficial (versão 2.22).
