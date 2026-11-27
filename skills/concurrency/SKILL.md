---
name: concurrency
description: Concorrência na aplicação Spring Boot 4 / Java 25 — beans singleton sem estado mutável, ConcurrentHashMap atômico, locks locais vs múltiplas réplicas, @Async e TaskExecutor (fila limitada, shutdown, propagação de contexto), CompletableFuture com executor e timeout, Semaphore com virtual threads e testes de corrida. Use ao escrever ou revisar código multi-thread ou estado em bean. Não use para ligar virtual threads (java-modern-features), thread dump (jvm-performance), locks no banco (data-modeling) nem circuit breaker (resilience).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../java-modern-features/SKILL.md`](../java-modern-features/SKILL.md) (virtual threads, Scoped Values, concorrência estruturada), [`../jvm-performance/SKILL.md`](../jvm-performance/SKILL.md) (pools, timeouts e diagnóstico) e [`../resilience/SKILL.md`](../resilience/SKILL.md) (bulkhead, timeouts e fallback). Nomes de classes e properties do Spring mudam entre versões: confirme na versão resolvida com [`../library-docs/SKILL.md`](../library-docs/SKILL.md).

# Concorrência na aplicação

Todo bean do Spring é **singleton** por padrão, e cada request roda na sua própria thread (de plataforma ou virtual). Portanto **todo campo mutável de um bean é estado compartilhado entre requests**, mesmo que ninguém tenha escrito "thread" no código. A pergunta de revisão é sempre a mesma: **quem mais lê ou escreve isto ao mesmo tempo?**

A ordem de preferência das soluções:
1. **Não compartilhar**: estado em variável local ou parâmetro.
2. **Compartilhar só o imutável**: `record`, `List.of`, `java.time`, `BigDecimal`, `DateTimeFormatter`.
3. **Estruturas concorrentes prontas**: `ConcurrentHashMap`, atômicos, um cache de verdade (`caching`).
4. **Lock**, por último, com seção crítica curta.
5. **Várias réplicas**: nada disso basta; a coordenação vai para o banco, o Redis ou o broker (seção 3).

## 1. Bean singleton: o estado compartilhado que ninguém vê

```java
// ❌ três bugs de concorrência num service "normal"
@Service
public class FineService {

    private BigDecimal total = BigDecimal.ZERO;
    private final SimpleDateFormat format = new SimpleDateFormat("dd/MM/yyyy");
    private final Map<Long, BigDecimal> finesByMember = new HashMap<>();
```
- `total` acumula valores de requests diferentes (e se perde em atualizações simultâneas).
- `SimpleDateFormat` **não é thread-safe**: sob carga, produz datas erradas sem lançar nada.
- `HashMap` escrito por várias threads pode corromper a estrutura interna (perda de entradas, laço infinito em versões antigas).

A correção: estado do request em **variável local**; `DateTimeFormatter` (imutável) no lugar de `SimpleDateFormat`; o mapa vira cache de verdade com limite e expiração (`caching`) ou `ConcurrentHashMap` se for realmente um registro em memória.

| Seguro para compartilhar entre threads | **Não** compartilhe (crie por uso ou confine) |
|---|---|
| `DateTimeFormatter`, tipos `java.time`, `BigDecimal`, `String`, `record` com campos imutáveis | `SimpleDateFormat`, `DecimalFormat`, `Calendar` |
| `ObjectMapper`/`JsonMapper` do Jackson 3, depois de construído | `StringBuilder`, `ArrayList`/`HashMap` mutáveis |
| `RestClient`, `JdbcTemplate`, clients do AWS SDK v2 | `MessageDigest`, `Cipher`, `Mac` |
| `ThreadLocalRandom.current()` (por thread) | `Random` compartilhado sob alta contenção (correto, mas lento) |

Mudar o escopo do bean para `prototype` ou `request` **não** é a correção: esconde o problema e cria objetos a cada injeção. Campo `static` mutável tem o mesmo problema, com a vida da JVM inteira.

## 2. Coleções concorrentes e atômicos

**`ConcurrentHashMap` é atômico por operação, não entre operações.** Verificar e depois escrever é uma corrida:
```java
// ❌ duas threads passam pelo containsKey e criam dois contadores
if (!counters.containsKey(memberId)) {
    counters.put(memberId, new LongAdder());
}
counters.get(memberId).increment();
```
```java
counters.computeIfAbsent(memberId, id -> new LongAdder()).increment();
```
- Use `computeIfAbsent`, `compute`, `merge` (`totals.merge(memberId, fine, BigDecimal::add)`) para ler e escrever numa operação só; para um `Set` concorrente, use `ConcurrentHashMap.newKeySet()`.
- **`ConcurrentHashMap` rejeita `null`**: chave ou valor `null` lança `NullPointerException` (diferente do `HashMap`). Já dentro da função de remapeamento de `compute`, `computeIfPresent` e `merge`, **retornar `null` remove a entrada** do mapa (`computeIfAbsent` que retorna `null` apenas não insere).
- A função passada a `computeIfAbsent`/`compute` roda **com a entrada bloqueada**: nada de I/O, chamada remota ou escrita no **mesmo** mapa dentro dela (pode bloquear outras threads ou lançar `IllegalStateException` por atualização recursiva).
- **Contadores:** `AtomicLong` quando o valor exato é lido com frequência; `LongAdder` quando há muita escrita concorrente e leitura rara. Para métrica, use um `Counter` do Micrometer (`observability`), não um campo do bean.
- **`CopyOnWriteArrayList`**: muita leitura e escrita rara (lista de listeners). Cada escrita copia o array inteiro.
- **`ConcurrentLinkedQueue`**: fila não-bloqueante para passagem leve entre threads, mas **`size()` é `O(N)`** (percorre os nós) — use sempre `isEmpty()`, nunca `size() == 0` em laço ou health check.
- **`Collections.synchronizedList`**: iterar exige `synchronized` manual na lista e operações compostas continuam em corrida; prefira as opções acima.
- **Configuração carregada no startup**: `List.copyOf`/`Map.copyOf` ou `record`, publicada uma vez e nunca alterada.
- **Mapa em memória que só cresce** é vazamento de memória com atraso: sem limite e expiração, use Caffeine (`caching`).

## 3. Locks, e o limite de uma JVM

| Mecanismo | Quando |
|---|---|
| `synchronized` | Seção crítica curta e simples. Desde o Java 24 não prende mais a virtual thread à thread de plataforma (`java-modern-features`) |
| `ReentrantLock` | Precisa de `tryLock(timeout)`, de interrupção ou de mais de uma condição |
| `ReentrantReadWriteLock` | Muitas leituras e escritas raras sobre a mesma estrutura, e a leitura não é trivial |
| `StampedLock` | Raro; leitura otimista em código de baixo nível medido. Não é reentrante |

```java
private final ReentrantLock lock = new ReentrantLock();

public void rebuildIndex() {
    try {
        if (!lock.tryLock(2, TimeUnit.SECONDS)) throw new IndexBusyException();
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new IndexBusyException();
    }
    try {
        index = buildIndex();
    } finally {
        lock.unlock();
    }
}
```
- **Seção crítica curta**: nunca I/O, chamada remota ou query dentro do lock.
- **Deadlock**: duas threads pegando dois locks em ordem inversa. Previna com **ordem fixa de aquisição** (sempre pelo id menor) e `tryLock` com timeout; diagnostique com thread dump (`jvm-performance`).
- **`InterruptedException` nunca é engolida**: restaure a flag (`Thread.currentThread().interrupt()`) e saia; ou propague.
- Campo lido por várias threads e escrito por uma, sem lock: `volatile` (ou `AtomicReference`) para garantir visibilidade. Sem isso, outra thread pode nunca ver o valor novo.

**Com várias réplicas, lock em memória não protege nada.** `synchronized` e `ReentrantLock` coordenam threads **de uma JVM**; com 3 pods, duas requests em pods diferentes entram na seção "protegida" ao mesmo tempo. A coordenação entre réplicas vai para:
- o **banco**: constraint única, `@Version`, `SELECT ... FOR UPDATE` (`data-modeling`, `jpa-advanced-mapping`);
- um **lock distribuído** (`redis`), com TTL e liberação segura;
- uma **chave de idempotência** (`idempotency`).

Lock em memória para proteger regra de negócio num serviço escalado horizontalmente é achado de revisão.

## 4. `@Async` e executors

O Spring Boot configura um executor para `@Async`. Com **platform threads**, é um `ThreadPoolTaskExecutor` com **8 threads e fila ilimitada** (com fila ilimitada, `max-size` é ignorado). Com **virtual threads** ligadas, é um `SimpleAsyncTaskExecutor` sem limite. Nos dois casos, o default não protege nada:
```yaml
spring:
  task:
    execution:
      thread-name-prefix: app-async-
      propagate-context: true
      pool:
        core-size: 8
        max-size: 16
        queue-capacity: 500
      simple:
        concurrency-limit: 200
        reject-tasks-when-limit-reached: true
      shutdown:
        await-termination: true
        await-termination-period: 30s
```
- **Fila limitada** (`queue-capacity`) e, com virtual threads, **limite de concorrência** (`simple.concurrency-limit`). Fila cheia lança `TaskRejectedException`: trate (responder 503, adiar, ou descartar o que é descartável), não deixe virar 500 genérico. A política de rejeição se troca com um bean `ThreadPoolTaskExecutorCustomizer`.
- **Shutdown gracioso** (`await-termination`), coerente com o `terminationGracePeriodSeconds` do pod (`kubernetes`).
- **Um executor por tipo de trabalho** (`@Async("reportExecutor")`): relatório lento não pode ocupar as threads do e-mail de confirmação. É o bulkhead no nível da thread (`resilience`).
- **Propagação de contexto**: `SecurityContext`, MDC e trace vivem em `ThreadLocal` e **não** chegam sozinhos à thread do `@Async`. `propagate-context: true` usa o `ContextPropagatingTaskDecorator`, que exige a biblioteca `io.micrometer:context-propagation` no classpath e propaga o que tiver um *accessor* registrado (o tracing do Micrometer registra o seu). Para o `SecurityContext`, use o suporte do Spring Security (`DelegatingSecurityContextAsyncTaskExecutor`). Confirme na versão resolvida (`library-docs`).

Armadilhas do `@Async`:
- Chamado de **outro método da mesma classe**, roda **síncrono** (o proxy não intercepta `this.metodo()`, como no `@Transactional` — `design-patterns`).
- **`@Async void` engole a exception**: ela vai para o `AsyncUncaughtExceptionHandler`, que só registra no log. Devolva `CompletableFuture<T>` quando o chamador precisa saber, ou configure o handler (`AsyncConfigurer`) com log e métrica.
- **A transação não atravessa threads**: passe **ids**, não entities (lazy loading quebra fora da sessão), e dispare trabalho que depende do commit com `@TransactionalEventListener(phase = AFTER_COMMIT)` (`email`).
- **Nunca `new Thread()` nem `Executors.newFixedThreadPool()` dentro de bean** sem ciclo de vida: as threads vazam, o shutdown não espera e não há métricas. Executor é `@Bean` (o Spring chama o shutdown); `ExecutorService` criado no código fecha com try-with-resources (é `AutoCloseable`).
- Com o Actuator, executors registrados como bean publicam métricas `executor.*` (ativas, na fila, rejeitadas): alarme na fila crescendo (`observability`).

## 5. `CompletableFuture` e scatter-gather

Montar a página de um livro chamando três serviços **em paralelo**, com prazo:
```java
@Service
public class BookPageService {

    private final CatalogClient catalogClient;
    private final ReviewClient reviewClient;
    private final LendingClient lendingClient;
    private final Executor executor;

    public BookPageService(
            CatalogClient catalogClient,
            ReviewClient reviewClient,
            LendingClient lendingClient,
            @Qualifier("integrationExecutor") Executor executor) {
        this.catalogClient = catalogClient;
        this.reviewClient = reviewClient;
        this.lendingClient = lendingClient;
        this.executor = executor;
    }

    public BookPageDTO findPage(Long bookId) {
        var book = CompletableFuture.supplyAsync(() -> catalogClient.findBook(bookId), executor)
            .orTimeout(2, TimeUnit.SECONDS);
        var availability = CompletableFuture.supplyAsync(() -> lendingClient.availability(bookId), executor)
            .orTimeout(2, TimeUnit.SECONDS);
        var reviews = CompletableFuture.supplyAsync(() -> reviewClient.findReviews(bookId), executor)
            .completeOnTimeout(List.of(), 800, TimeUnit.MILLISECONDS)
            .exceptionally(error -> List.of());

        return CompletableFuture.allOf(book, availability, reviews)
            .thenApply(ignored -> new BookPageDTO(book.join(), availability.join(), reviews.join()))
            .join();
    }
}
```
- **Sempre com executor explícito.** Sem ele, `supplyAsync` usa o `ForkJoinPool.commonPool()`, compartilhado pela JVM inteira e dimensionado para CPU: algumas chamadas HTTP lentas travam todo o resto que usa o pool comum (inclusive parallel streams).
- **Obrigatório × opcional**: o livro e a disponibilidade são obrigatórios (`orTimeout` falha a página); as avaliações são opcionais (`completeOnTimeout` + `exceptionally` degradam para lista vazia — `resilience`: fallback).
- **`orTimeout` não cancela a chamada em andamento**: a thread continua presa até o timeout do próprio client. Configure connect e read timeout no `RestClient` (`service-communication`); o `orTimeout` é o orçamento total da página.
- **`join()` lança `CompletionException`** com a causa dentro: trate a causa (timeout de dependência obrigatória → 503 ou 504 conforme o contrato de erro — `exception-handling`), não a casca.
- O contexto (trace, segurança) não chega às threads do executor sem propagação (seção 4).
- A **concorrência estruturada** (`StructuredTaskScope`) resolve o mesmo problema com cancelamento automático das irmãs, mas segue em preview no JDK 25 (`java-modern-features`). Até ficar final, este é o padrão.

## 6. Virtual threads: limite pelo recurso, não pelo pool

Com virtual threads, **não existe mais o pool que limitava a concorrência** por acidente. Dez mil requests chegam juntas ao parceiro que aguenta vinte. O limite passa a ser explícito, por recurso:
```java
private final Semaphore partnerPermits = new Semaphore(20);

public PartnerResponse send(PartnerRequest request) {
    try {
        if (!partnerPermits.tryAcquire(500, TimeUnit.MILLISECONDS)) throw new PartnerBusyException();
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new PartnerBusyException();
    }
    try {
        return partnerClient.send(request);
    } finally {
        partnerPermits.release();
    }
}
```
- Se o projeto já usa Resilience4j, o **bulkhead** dele faz isso com métricas e configuração (`resilience`); prefira-o.
- O limite é **por JVM**: o total no parceiro é `réplicas × permissões`. Ajuste junto com o HPA (`kubernetes`).
- Virtual thread não acelera **trabalho de CPU**; só ajuda quando a thread passa o tempo esperando I/O.
- Não faça pool de virtual threads nem cache de objeto caro em `ThreadLocal` (cada virtual thread é nova e o cache nunca é reaproveitado) — `java-modern-features`.

## 7. Parallel streams e Fork/Join: quase nunca numa API

`parallelStream()` roda no **mesmo `commonPool`** da seção 5. Numa API:
- Cada request que usa `parallelStream` disputa o pool com todas as outras; com I/O dentro (query, HTTP), o pool trava e derruba o desempenho de quem nem usa parallel stream.
- O ganho só aparece com **trabalho de CPU**, **muitos elementos** (milhares, com processamento não trivial por elemento), fonte que se divide bem (`ArrayList`, array; não `LinkedList` nem `Stream.iterate`), **sem estado compartilhado** mutável e sem exigência de ordem (`forEachOrdered` e `findFirst` custam caro).
- **Meça antes** com JMH ou com o teste de carga (`jvm-performance`). Em job de lote CPU-bound pode compensar; em endpoint, quase nunca.
- Não use o truque de submeter o stream a um `ForkJoinPool` próprio: depende de detalhe de implementação. Se precisa de paralelismo controlado, use um executor explícito.

## 8. Produtor-consumidor em memória × broker

Uma `BlockingQueue` com threads consumidoras é simples, mas:
- **perde tudo** no restart, no deploy e no OOM;
- **não é compartilhada** entre réplicas;
- não tem retry, DLQ nem visibilidade.

Serve para trabalho **descartável e local** (agrupar métricas, buffer de log), sempre **limitada** (`ArrayBlockingQueue`), com `offer(timeout)` para aplicar contrapressão e esvaziamento no shutdown. O que **não pode ser perdido** (e-mail de confirmação, evento de negócio) vai para um broker com outbox (`messaging`, `transactional-outbox`).

`@Scheduled` também é concorrência: com várias réplicas, roda em todas (use lock distribuído ou um agendador externo — `redis`, `aws-eventbridge`); e o pool de agendamento tem **1 thread** por padrão (`spring.task.scheduling.pool.size`), então uma tarefa lenta atrasa todas as outras.

## 9. Testes

- **Corrida**: N threads largando juntas (`CountDownLatch` como portão de largada, `ExecutorService`), depois afirme a invariante (o total, a quantidade de registros); repita com `@RepeatedTest` (`test-patterns`, seção 10). Falha intermitente é **bug**, não teste instável.
- **Assíncrono**: Awaitility (`await().atMost(...).untilAsserted(...)`), nunca `Thread.sleep`.
- **`@Async` em unit test**: chame o método direto (sem proxy, roda síncrono) e teste o executor/configuração em teste de integração. Em teste de integração, um `SyncTaskExecutor` torna o fluxo determinístico quando a assincronia não é o que se testa.
- **Timeouts e fallback**: torne os prazos configuráveis e use valores pequenos no teste; o stub da dependência opcional demora mais que o prazo e o teste afirma a resposta degradada.
- **Pinning e contenção** sob carga: evento JFR `jdk.VirtualThreadPinned` e thread dump (`jvm-performance`).
- Código lock-free de baixo nível (raro numa API) pede ferramenta própria, como o jcstress do OpenJDK.

## 10. Checklist de revisão

- Bean com **campo mutável** escrito durante o request? `SimpleDateFormat`, `HashMap`, `ArrayList` ou `StringBuilder` compartilhados?
- `containsKey` + `put` (ou `get` + `put`) em mapa concorrente, em vez de `computeIfAbsent`/`merge`? Valor possivelmente `null` passado ao `ConcurrentHashMap` ou `ConcurrentLinkedQueue.size()` chamado em caminho quente?
- **Lock em memória** protegendo regra de negócio num serviço com mais de uma réplica?
- I/O dentro de `synchronized`/lock ou dentro de `computeIfAbsent`?
- `InterruptedException` engolida (catch vazio ou só log)?
- `@Async` sem executor próprio, com fila ilimitada, `void` sem tratamento de erro, chamado de dentro da mesma classe, recebendo entity?
- `supplyAsync` sem executor (pool comum); `CompletableFuture` sem timeout; `join()` sem tratar `CompletionException`?
- `parallelStream()` em endpoint ou com I/O dentro?
- `new Thread()`/`Executors.new...` sem ciclo de vida; fila em memória para trabalho que não pode ser perdido?
- Virtual threads ligadas sem limite explícito para a dependência frágil?

---

## Regras principais

- **Bean singleton é estado compartilhado**: estado do request em variável local; só objetos imutáveis ou thread-safe em campo; `DateTimeFormatter`, nunca `SimpleDateFormat`.
- **Mapa concorrente com operação composta atômica** (`computeIfAbsent`, `merge`); sem I/O dentro da função; cache com limite (`caching`), não mapa que só cresce.
- **Lock por último**, seção crítica curta, ordem fixa e `tryLock` com timeout; `InterruptedException` restaura a flag. **Várias réplicas → banco, Redis ou idempotência**, nunca lock em memória.
- **`@Async` com executor configurado**: fila ou concorrência limitada, rejeição tratada, shutdown gracioso, contexto propagado, um executor por tipo de trabalho, `CompletableFuture` em vez de `void` quando o erro importa, ids em vez de entities.
- **Scatter-gather com executor explícito**, `orTimeout` nas obrigatórias, fallback nas opcionais, timeout também no client, `CompletionException` desembrulhada.
- **Virtual threads com limite por recurso** (`Semaphore` ou bulkhead), lembrando que o limite é por JVM.
- **Parallel streams quase nunca numa API**; só CPU-bound, volume grande e medido.
- **Fila em memória só para o descartável**; o resto vai para broker com outbox.
- **Testes de corrida com portão de largada e repetição**; Awaitility para o assíncrono; nunca `sleep`.
- **Sem Lombok** — deliberado.

## Referências

- Documentação do Java SE 25 (`java.util.concurrent`) e do Spring Framework 7 e Spring Boot 4 (*Task Execution and Scheduling*); properties `spring.task.*` conferidas no `spring-configuration-metadata.json` do Spring Boot 4.2.0.
- Brian Goetz et al., *Java Concurrency in Practice* (Addison-Wesley, 2006): base conceitual de thread-safety, publicação segura e confinamento.
- Maurice Naftalin e Philip Wadler, com Stuart Marks, *Java Generics and Collections*, 2ª ed. (O'Reilly, 2025), caps. 9, 13, 15 e 17: semântica de `null` e remapeamento em `ConcurrentHashMap`, `ConcurrentLinkedQueue.size()` `O(N)` e substituição de `Collections.synchronized*`.
- Anghel Leonard, *Java Coding Problems*, 2ª ed. (Packt, 2024), caps. 10 e 11, como apoio para virtual threads, `Semaphore` e produtor-consumidor. A API de concorrência estruturada do livro (`ShutdownOnFailure`) foi substituída no JDK 25.
