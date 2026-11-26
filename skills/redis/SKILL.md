---
name: redis
description: Redis e Valkey em produção com Spring Boot 4 / Spring Data Redis — escolha Redis vs banco relacional vs broker, StringRedisTemplate e RedisTemplate com Jackson 3 (nunca serialização Java), estruturas (String, Hash, Set, Sorted Set), TTL por cache (RedisCacheManagerBuilderCustomizer), atomicidade com scripts Lua, locks distribuídos com liberação segura (e quando preferir lock no banco), rate limiting distribuído, revogação de JWT e sessões, Redis Streams vs Pub/Sub, maxmemory-policy e isolamento de instâncias, SCAN (nunca KEYS *), Lettuce, Sentinel vs Cluster com hash tags, Valkey e Amazon ElastiCache, métricas e testes com Testcontainers. Use quando usar Redis/Valkey/ElastiCache diretamente (estruturas de dados, Lua, lock distribuído, rate limit, Streams, Pub/Sub, sessão, tuning operacional ou topologia). Não use apenas para escolher entre Caffeine e Redis ou configurar @Cacheable simples (caching).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../caching/SKILL.md`](../caching/SKILL.md) (padrão de cache com `@Cacheable`, invalidação e stampede), [`../library-docs/SKILL.md`](../library-docs/SKILL.md) (confirmar classes e properties no Spring Boot 4 / Spring Data Redis 4) e [`../application-security/SKILL.md`](../application-security/SKILL.md).

# Redis e Valkey com Spring Boot

O **Redis** (e o **Valkey**, fork aberto Apache-2.0 mantido pela Linux Foundation, compatível com o protocolo RESP e os clientes Java) é um armazenamento **em memória** de altíssima vazão e latência sub-milissegundo. Ele resolve muito mais que `@Cacheable` — mas **não é substituto do banco relacional nem de um broker durável**.

## 1. Quando usar Redis — e quando NÃO usar

| Necessidade | Use Redis? | Alternativa melhor |
|---|---|---|
| Cache compartilhado entre réplicas (`caching`), TTL por recurso | **Sim** | Caffeine local se o dado tolera atraso de segundos entre pods |
| Rate limiting distribuído, contadores/rankings (`ZSET`), denylist de `jti` (revogação de JWT) | **Sim** | — |
| Sessões HTTP compartilhadas (BFF / OAuth2 client) | **Sim** (`spring-session-data-redis`) | JWT stateless (`authentication`, `aws-cognito`) |
| Coordenação de eficiência (evitar dois workers recalcularem o mesmo relatório caro) | **Sim** (lock com TTL + Lua) | — |
| **Consistência forte de negócio** (saldo, estoque, idempotência financeira, evitar cobrança dupla) | **Não como fonte de verdade** | Constraint única, `@Version` ou `SELECT FOR UPDATE` no banco (`spring-data-jpa`, `idempotency`) |
| **Eventos de domínio que não podem se perder** (integração entre serviços) | **Não (especialmente Pub/Sub)** | `transactional-outbox` + Kafka/RabbitMQ/SQS (`messaging`) |
| **Fonte de verdade durável** ou consultas relacionais/ad-hoc | **Não** | Banco relacional (`spring-data-jpa`, `aws-rds-secrets-manager`) |

**Redis vs Valkey:** a mudança de licença do Redis em 2024 levou a comunidade e provedores de nuvem (incluindo Amazon ElastiCache) a adotar o **Valkey** (Apache-2.0). Do ponto de vista do Spring Data Redis e do Lettuce, o protocolo e o código são os mesmos — **prefira Valkey** em projetos novos ou em ElastiCache, salvo dependência explícita de módulos proprietários do Redis.

---

## 2. Dependencies e configuração (Spring Boot 4)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```
Para testes de integração no Boot 4, confirme o starter modular (`spring-boot-starter-data-redis-test` / `spring-boot-testcontainers`) com `library-docs`. O cliente padrão do Boot é o **Lettuce** (assíncrono sobre Netty, conexão única multiplexada — dispensa pool na maioria dos casos; veja seção 8).

```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST}
      port: ${REDIS_PORT:6379}
      username: ${REDIS_USERNAME:}
      password: ${REDIS_PASSWORD}
      ssl:
        enabled: true
      timeout: 2s
      connect-timeout: 2s
      client-name: library-api
```
- **Credenciais e TLS:** nunca deixe senha/token no `application.yml` nem no Git — venha do Secrets Manager / External Secrets (`aws-rds-secrets-manager`, `kubernetes`). Em produção, **TLS sempre ligado** (`ssl.enabled: true`) e, quando o servidor suporta **Redis ACL** (Redis 6+ / Valkey), crie um usuário dedicado por aplicação com permissões restritas aos seus prefixos e comandos (sem `FLUSHALL`, `CONFIG`, `KEYS`).
- **Timeouts curtos e explícitos:** sem timeout (ou com o default longo de 60 s), um Redis travado prende threads da API em cascata. 1–2 s para comando/conexão é um ponto de partida seguro.

### TTL distinto por cache e serialização JSON (complemento de `caching`)

A propriedade `spring.cache.redis.time-to-live` define apenas um TTL global. Em produção, cada cache tem validade própria — configure com `RedisCacheManagerBuilderCustomizer` e **nunca use o default `JdkSerializationRedisSerializer`** (usa `ObjectInputStream`: risco de desserialização insegura em `application-security` e quebra a cada mudança de classe):

```java
@Configuration
@EnableCaching
public class RedisCacheConfig {

    @Bean
    RedisCacheConfiguration defaultRedisCacheConfiguration() {
        return RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10))
                .prefixCacheNameWith("library:v1:")
                .disableCachingNullValues()
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(RedisSerializer.json()));
    }

    @Bean
    RedisCacheManagerBuilderCustomizer redisCacheManagerBuilderCustomizer(RedisCacheConfiguration defaultConfig) {
        return builder -> builder
                .withCacheConfiguration("books", defaultConfig.entryTtl(Duration.ofMinutes(30)))
                .withCacheConfiguration("book-availability", defaultConfig.entryTtl(Duration.ofSeconds(30)));
    }
}
```
Confirme a assinatura exata do serializador JSON baseado em Jackson 3 (`RedisSerializer.json()` / `GenericJacksonJsonRedisSerializer`) na versão resolvida do Spring Data Redis 4 com `library-docs`. Inclua uma **versão no prefixo** (`library:v1:`) para invalidar entradas antigas de forma limpa quando o formato do DTO mudar de maneira incompatível.

---

## 3. Estruturas de dados e templates

Escolha a estrutura pelo padrão de acesso — **não serialize listas inteiras em uma única String JSON** se você precisa atualizar um campo ou ler uma fatia:

| Estrutura | Quando usar | Exemplo de comando / API |
|---|---|---|
| **String** | Valor simples, DTO JSON, contador (`INCR`), flag com TTL, `SET NX PX` | `opsForValue()` |
| **Hash** | Objeto com vários campos lidos/atualizados individualmente (ex.: contadores por livro, sessão) | `opsForHash()` |
| **Set** | Pertinência única sem ordem (tags, ids ativos) | `opsForSet()` |
| **Sorted Set (`ZSET`)** | Ranking, fila agendada por timestamp, janela deslizante de rate limit | `opsForZSet()` |
| **HyperLogLog** | Contagem aproximada de elementos únicos com memória fixa (~12 KB) | `opsForHyperLogLog()` |
| **Stream** | Log append-only com consumer groups e `XACK` (seção 6) | `opsForStream()` |

**Convenção de chaves:** `<app>:<ambiente>:<domínio>:<id>` (ex.: `library:prod:book:42`, `library:prod:ratelimit:{user-99}`). Curta, legível, sem espaços e **sem PII** (nunca e-mail/CPF na chave — use o ID interno ou hash, `privacy-lgpd`).

### `StringRedisTemplate` vs `RedisTemplate`

Prefira **`StringRedisTemplate`** para strings, contadores, locks, denylists e JSON serializado explicitamente com o `JsonMapper` (Jackson 3) — evita metadados `@class` acoplados ao nome da classe Java, facilita interoperabilidade entre serviços e elimina riscos de polymorphic deserialization:

```java
@Component
public class RevokedTokenStore {

    private static final String KEY_PREFIX = "library:auth:revoked:";

    @Autowired
    private StringRedisTemplate redisTemplate;

    public void revoke(String jti, Duration remainingTtl) {
        if (remainingTtl.isNegative() || remainingTtl.isZero()) return;
        redisTemplate.opsForValue().set(KEY_PREFIX + jti, "1", remainingTtl);
    }

    public boolean isRevoked(String jti) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(KEY_PREFIX + jti));
    }
}
```
Quando precisar guardar DTOs estruturados com `RedisTemplate<String, Object>`, configure explicitamente `StringRedisSerializer` para keys/hashKeys e o serializador JSON (Jackson 3) para values — **nunca** deixe o `RedisTemplate` sem serializador (o padrão é serialização Java).

---

## 4. Atomicidade com scripts Lua e rate limiting distribuído

Comandos separados (`INCR` seguido de `EXPIRE`) têm **condição de corrida**: se a aplicação cair entre os dois comandos, a chave fica **sem TTL para sempre** (vazamento de memória). Operações compostas em Redis devem ser **um único script Lua** — o Redis executa o script atomicamente sem intercalar outros clientes.

Exemplo — **rate limiter de janela fixa atômico** (ou use **Bucket4j + Lettuce** para Token Bucket pronto sem manter Lua à mão):

```java
@Component
public class RedisRateLimiter {

    private static final DefaultRedisScript<Long> INCREMENT_WITH_TTL = new DefaultRedisScript<>(
            """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
                redis.call('PEXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """,
            Long.class
    );

    @Autowired
    private StringRedisTemplate redisTemplate;

    public boolean isAllowed(String subjectId, int maxRequests, Duration window) {
        var key = "library:ratelimit:{" + subjectId + "}:" + (System.currentTimeMillis() / window.toMillis());
        var count = redisTemplate.execute(
                INCREMENT_WITH_TTL,
                List.of(key),
                String.valueOf(window.toMillis())
        );
        return count != null && count <= maxRequests;
    }
}
```
- **Scripts Lua devem ser curtos e determinísticos:** o Redis executa scripts na thread principal; um loop pesado em Lua bloqueia **todos** os clientes.
- **Todas as chaves acessadas** devem vir via `KEYS[1..n]` (nunca construídas dinamicamente dentro do script) e, em **Redis Cluster**, devem compartilhar a mesma **hash tag** (`{subjectId}`) para cair no mesmo slot (seção 8).
- O Spring envia o script via `EVALSHA` automaticamente após o primeiro carregamento (evita reenviar o texto em toda chamada).
- Em caso de indisponibilidade do Redis, decida explicitamente entre **fail-open** (deixa passar e loga — comum em rate limit não crítico) ou **fail-closed** (rejeita — necessário em proteção contra brute force de login).

---

## 5. Locks distribuídos (e suas armadilhas)

Um lock distribuído em Redis serve para **eficiência** (evitar que duas réplicas executem o mesmo job pesado ao mesmo tempo). **Não use lock em Redis sozinho para garantir corretude financeira ou unicidade de escrita no banco.**

### O padrão mínimo seguro (adquirir + liberar só se for dono)

```java
@Component
public class RedisDistributedLock {

    private static final DefaultRedisScript<Long> UNLOCK_IF_OWNER = new DefaultRedisScript<>(
            """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
            return 0
            """,
            Long.class
    );

    @Autowired
    private StringRedisTemplate redisTemplate;

    public Optional<String> tryAcquire(String lockKey, Duration ttl) {
        var token = UUID.randomUUID().toString();
        var acquired = redisTemplate.opsForValue().setIfAbsent(lockKey, token, ttl);
        return Boolean.TRUE.equals(acquired) ? Optional.of(token) : Optional.empty();
    }

    public void release(String lockKey, String token) {
        redisTemplate.execute(UNLOCK_IF_OWNER, List.of(lockKey), token);
    }
}
```
- **Sempre `SET key token NX PX ttl` atômico** (`setIfAbsent` com `Duration`) — nunca `SETNX` + `EXPIRE` separados.
- **Sempre libere conferindo o `token` via Lua:** se o trabalho demorar mais que o `ttl`, o lock expira e outro pod o adquire; um `DEL` cego apagaria o lock **do outro pod**!
- **Para tarefas agendadas entre réplicas**, prefira **EventBridge Scheduler** (`aws-eventbridge`) ou **ShedLock** (no banco ou Redis) em vez de reinventar lock manual.
- **Quando precisa de renovação automática (watchdog)** para trabalho de duração incerta, avalie `Spring Integration RedisLockRegistry` ou `Redisson` (confirmando compatibilidade com Boot 4 via `library-docs`).
- **Por que lock em Redis não basta para corretude crítica:** (1) uma pausa longa de GC/rede pode deixar o lock expirar enquanto o processo A ainda acha que é dono e grava no banco depois do processo B; (2) replicação primário → réplica no Redis é **assíncrona** — um failover pode perder um lock recém-concedido. Para invariantes de dados, proteja o destino final com **fencing token**, **`@Version`** (optimistic locking) ou **constraint única** no banco (`spring-data-jpa`, `idempotency`).

---

## 6. Redis Streams vs Pub/Sub (e quando preferir um broker)

| | Redis Pub/Sub | Redis Streams | Kafka / RabbitMQ / SQS (`messaging`) |
|---|---|---|---|
| **Durabilidade / replay** | **Zero** — quem está offline perde a mensagem | Persistido em memória/AOF até `MAXLEN`, com replay por ID | Persistido em disco, retenção longa, DLQ nativa |
| **Entrega para múltiplos workers** | Broadcast para todos (não divide trabalho) | **Consumer groups** (`XREADGROUP` + `XACK` + PEL) | Nativo (partições / filas / DLQ) |
| **Quando usar** | Invalidação de cache local entre pods, notificação em tempo real descartável (WebSocket) | Filas/eventos leves quando Redis já está no stack e perda sob falha catastrófica de memória é aceitável | **Padrão do pack** para eventos de domínio e integração entre serviços |

Se usar **Redis Streams**:
- **Sempre limite o tamanho do stream** (`MAXLEN ~ 10000` no `XADD` — trimming aproximado): stream sem teto consome toda a memória do Redis.
- Use **Consumer Groups** (`XREADGROUP`), confirme apenas após processar (`XACK`) e trate mensagens presas na **Pending Entries List (PEL)** com `XAUTOCLAIM` + limite de tentativas para uma stream/fila de mortas (equivalente à DLQ).
- Mantenha consumidores **idempotentes** (`idempotency`) — entrega é *at-least-once*.

---

## 7. Memória, `maxmemory-policy` e anti-padrões de produção

A decisão operacional mais importante do Redis é **o que acontece quando a memória enche** (`maxmemory-policy`):

| Política | Comportamento quando `maxmemory` é atingido | Use para |
|---|---|---|
| **`allkeys-lru`** ou **`allkeys-lfu`** | Despeja as chaves menos usadas recentemente / menos frequentes | **Cache puro** (pode recomputar do banco) |
| **`volatile-lru`** / **`volatile-ttl`** | Despeja apenas chaves que **têm TTL** | Cache misto onde algumas chaves fixas nunca devem sair (arriscado se faltar memória) |
| **`noeviction`** (padrão) | Recusa novas escritas com erro `OOM` | **Locks, sessões, rate limit, Streams, revogação de JWT** — despejar uma chave aqui quebra segurança/corretude |

**Regra crítica de isolamento:** **nunca compartilhe a mesma instância/cluster de Redis** entre **cache puro** (`allkeys-lru`) e **estado crítico** (locks distribuídos, revogação de JWT, sessões, Streams). Se o cache encher a memória, o Redis vai despejar seus locks ou tokens revogados silenciosamente! Separe em instâncias/clusters distintos por perfil de política.

### Anti-padrões que derrubam produção

1. **`KEYS *` em produção:** o Redis processa comandos em uma thread principal; `KEYS *` varre **todo** o espaço de chaves em O(N) e congela o servidor inteiro para todos os clientes. Use sempre **`SCAN` com `COUNT`** (ou `redisTemplate.scan(ScanOptions.scanOptions().match("...").count(200).build())`), e nunca faça varredura no caminho quente de uma request HTTP.
2. **Big keys e coleções sem limite:** um valor String de vários MB ou um `Hash`/`ZSET`/`List` com centenas de milhares de itens causa picos de latência em leitura, serialização e remoção (prefira `UNLINK` assíncrono em vez de `DEL` para chaves grandes).
3. **Hot keys:** uma única chave recebendo dezenas de milhares de req/s satura um único shard do cluster. Mitigue com cache local curto (Caffeine 5–30 s na frente do Redis — L1 + L2) ou sharding da chave.
4. **Serialização Java nativa (`JdkSerializationRedisSerializer`):** proibida (`application-security`, `caching`).
5. **Chaves sem TTL em cache/rate limit/denylist:** crescimento infinito até OOM ou eviction em cascata.
6. **Chamar Redis dentro de `@Transactional` de escrita longa no banco:** se a transação fizer rollback, o que foi gravado no Redis já ficou lá; e a latência de rede mantém a conexão JDBC presa. Atualize/invalide cache após o commit (`@TransactionalEventListener(phase = AFTER_COMMIT)`) ou fora da transação.

---

## 8. Topologia, Lettuce e Amazon ElastiCache (Valkey/Redis)

### Topologias

| Topologia | Quando usar | Atenção no Spring Boot |
|---|---|---|
| **Standalone** | Apenas dev local e testes | `spring.data.redis.host/port` |
| **Replication + Sentinel** | Alta disponibilidade (failover automático) quando os dados cabem em um nó | `spring.data.redis.sentinel.master` + `nodes` |
| **Cluster** | Sharding horizontal (memória/throughput > 1 nó) e alta disponibilidade | `spring.data.redis.cluster.nodes`; **operações multi-chave e scripts Lua exigem hash tags `{...}`** para garantir o mesmo hash slot (`CROSSSLOT` error caso contrário) |

### Lettuce e Virtual Threads

- O **Lettuce** compartilha **uma única conexão TCP multiplexada** para comandos não bloqueantes — **não** adicione `commons-pool2` sem medir necessidade (pooling desnecessário aumenta conexões abertas no servidor).
- Exceções que exigem conexões dedicadas (ou pool): comandos **bloqueantes** (`BLPOP`, `XREAD BLOCK`), **transações** (`MULTI`/`EXEC`) e **Pub/Sub**.
- Em **Redis Cluster**, habilite a atualização periódica de topologia (`ClusterTopologyRefreshOptions` com adaptive + periodic refresh) para que o cliente descubra failovers e novos shards sem reiniciar a aplicação.
- Com **Java 25 Virtual Threads** (`java-modern-features`), o Lettuce já usa Netty não bloqueante na camada de I/O — configure timeouts e monitore o pool de event loops do Netty se houver carga extrema.

### Amazon ElastiCache (Valkey / Redis)

- **Valkey** no ElastiCache tem menor custo que Redis OSS no mesmo porte e é compatível com o cliente Spring Data Redis/Lettuce.
- **ElastiCache Serverless** (escala automática de memória e ECPUs, Multi-AZ nativo, endpoint único com TLS obrigatório) reduz operação para workloads variáveis; **Replication Group (Node-based)** com `multi_az_enabled = true` e `automatic_failover_enabled = true` dá custo previsível em carga estável.
- **Rede e segurança:** sempre em **subnets privadas**, security group aceitando porta `6379` **somente do SG da aplicação** (`aws-eks`, `aws-ecs-fargate`), `transit_encryption_enabled = true` (TLS), `at_rest_encryption_enabled = true` (KMS) e **AUTH/RBAC** com segredo no Secrets Manager (`aws-rds-secrets-manager`).
- Declare tudo por **Terraform** (`aws_elasticache_serverless_cache` ou `aws_elasticache_replication_group` — `aws-terraform`), nunca no console.

---

## 9. Observabilidade

Além das métricas do Spring Cache (`cache.gets`, `cache.evictions` em `caching`), monitore no servidor Redis/Valkey (CloudWatch ElastiCache ou `redis_exporter` no Prometheus — `observability`, `aws-observability`):
- **`DatabaseMemoryUsagePercentage` / `used_memory` vs `maxmemory`:** alarme > 75–80% antes de começar eviction ou `OOM`.
- **`Evictions` (`evicted_keys`):** em instância de locks/sessões/rate limit, **qualquer eviction > 0 é incidente**; em cache, pico contínuo indica memória subdimensionada ou falta de TTL.
- **`EngineCPUUtilization`:** lembre que o núcleo do Redis é single-threaded — CPU perto de 80–90% em um nó significa fila de comandos e latência p99 disparando.
- **`CurrConnections` / `RejectedConnections`:** conexões vazando ou pool mal dimensionado.
- **`ReplicationLag`** (em Sentinel/Cluster/Multi-AZ) e **hit ratio** (`CacheHits / (CacheHits + CacheMisses)`).

---

## 10. Testes (Testcontainers, sem mockar `RedisTemplate`)

Nunca mocke `RedisTemplate`/`ValueOperations` encadeados (teste frágil que não prova serialização, TTL nem script Lua — `test-patterns`). Suba um container **singleton** de Valkey ou Redis real (`integration-testing`):

```java
@SpringBootTest
class RedisLockAndRateLimitIntegrationTest {

    @ServiceConnection(name = "redis")
    static final GenericContainer<?> REDIS = new GenericContainer<>(DockerImageName.parse("valkey/valkey:8.1-alpine"))
            .withExposedPorts(6379);

    static {
        REDIS.start();
    }

    @Autowired
    private RedisDistributedLock lock;

    @Autowired
    private RedisRateLimiter rateLimiter;

    @Test
    void onlyOneCallerAcquiresLockAndWrongTokenCannotReleaseIt() {
        var key = "test:lock:" + UUID.randomUUID();
        var token = lock.tryAcquire(key, Duration.ofSeconds(10)).orElseThrow();

        assertThat(lock.tryAcquire(key, Duration.ofSeconds(10))).isEmpty();

        lock.release(key, "wrong-token");
        assertThat(lock.tryAcquire(key, Duration.ofSeconds(10))).isEmpty();

        lock.release(key, token);
        assertThat(lock.tryAcquire(key, Duration.ofSeconds(10))).isPresent();
    }

    @Test
    void rateLimiterAllowsUpToLimitAndRejectsExcess() {
        var subject = "user-" + UUID.randomUUID();

        assertThat(rateLimiter.isAllowed(subject, 2, Duration.ofSeconds(5))).isTrue();
        assertThat(rateLimiter.isAllowed(subject, 2, Duration.ofSeconds(5))).isTrue();
        assertThat(rateLimiter.isAllowed(subject, 2, Duration.ofSeconds(5))).isFalse();
    }
}
```
- **Container singleton** (`static { REDIS.start(); }`, sem `@Testcontainers`/`@Container` por classe) e **tag fixa** (`valkey/valkey:8.1-alpine` ou `redis:7.4-alpine`, nunca `latest`). Confirme suporte a `@ServiceConnection(name = "redis")` ou use `@DynamicPropertySource` (`spring.data.redis.host`/`port`) com `library-docs`.
- **Chaves únicas por teste** (`UUID.randomUUID()`) para isolamento sem `FLUSHALL` entre testes paralelos.
- **Cubra o que importa:** atomicidade sob concorrência (várias threads competindo pelo mesmo lock → exatamente uma vence), recusa de liberação com token errado, expiração por TTL (use TTL curto de ~200 ms + **Awaitility**, nunca `Thread.sleep`), e degradação graciosa (`CacheErrorHandler`/fallback) quando o Redis falha.

---

## Regras principais

- **Redis não é banco primário nem broker durável:** use-o para cache distribuído, rate limiting, contadores/rankings, denylist de JWT, sessões e coordenação de eficiência; consistência crítica continua no banco (`@Version`, constraints únicas) e eventos de domínio em `transactional-outbox` + broker (`messaging`).
- **Prefira Valkey** (Apache-2.0) em projetos novos e no ElastiCache, salvo dependência explícita de módulo proprietário.
- **Nunca use serialização Java nativa (`JdkSerializationRedisSerializer`)**: use `StringRedisTemplate` ou JSON (Jackson 3 — confirme com `library-docs`); versione o prefixo da chave (`library:v1:`).
- **Nunca misture cache com eviction (`allkeys-lru`) e estado crítico (locks, sessões, rate limit, Streams) na mesma instância**: separe instâncias e use `noeviction` onde despejar chave quebra segurança ou corretude.
- **Nunca `KEYS *` em produção** (use `SCAN` fora do caminho quente); evite big keys, hot keys e chaves sem TTL; **nunca coloque PII na chave**.
- **Operações compostas (rate limit, lock release) são scripts Lua atômicos** com chaves passadas em `KEYS[...]` — nunca `SETNX` + `EXPIRE` separados nem `DEL` cego em lock.
- **Em Redis Cluster**, use **hash tags `{...}`** para operações multi-chave e Lua, e habilite refresh de topologia no Lettuce; não adicione pool Lettuce sem necessidade medida.
- **Streams sempre com `MAXLEN ~`**, consumer groups, `XACK` e tratamento da PEL; Pub/Sub apenas para mensagens efêmeras descartáveis.
- **Segurança e AWS:** TLS obrigatório, timeouts curtos (1–2 s), ACL por aplicação, segredos fora do Git (Secrets Manager), ElastiCache privado Multi-AZ/Serverless declarado em Terraform.
- **Testes com container real singleton** (`valkey`/`redis` com tag fixa, chaves únicas por teste, Awaitility para TTL), sem mockar `RedisTemplate`.
- **Sem Lombok** — deliberado.
