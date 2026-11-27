---
name: kafka
description: Apache Kafka com Spring Boot 4 — KafkaTemplate idempotente, @KafkaListener, JSON seguro (trusted packages, ErrorHandlingDeserializer), keys e partições, consumer groups, DefaultErrorHandler com DLT e @RetryableTopic, exactly-once, tópicos, Schema Registry, Strimzi/MSK, lag e testes com Testcontainers. Use quando publicar ou consumir eventos em Kafka. Não use para escolher o broker (messaging).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../messaging/SKILL.md`](../messaging/SKILL.md) (escolha de broker, desenho de eventos, garantias) — e **`../transactional-outbox/SKILL.md`** se o evento nasce de uma mudança no database.

# Apache Kafka

Kafka é um **log distribuído e particionado**: mensagens ficam retidas por tempo/tamanho, vários **consumer groups** leem o mesmo tópico de forma independente, e é possível **reprocessar** (replay) voltando o offset. Ótimo para streaming de eventos em escala; é mais pesado de operar que uma fila. Se o caso é "fila de tarefas" simples, avalie `rabbitmq`/`aws-sns-sqs` (veja `messaging`).

> As APIs do **Spring Kafka 4 / Boot 4** mudaram com a modularização e o Jackson 3 (por exemplo, o starter próprio e as classes de serializer JSON). Confirme os nomes exatos na versão resolvida (`library-docs`) em vez de copiar de um projeto Boot 3; os pontos incertos estão marcados abaixo.

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-kafka</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-kafka-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-kafka</artifactId>
    <scope>test</scope>
</dependency>
```
Versões vêm do BOM do Boot. (No Boot 3 os artifacts eram `spring-kafka` e `spring-kafka-test`; confirme na versão resolvida com `library-docs`.)

---

## Conceitos que mudam o seu código

- **Tópico → partições.** A partição é a unidade de **ordem** e de **paralelismo**. A **key** da mensagem decide a partição (hash): mesma key → mesma partição → **ordem preservada**. Use como key o **id do agregado** (`book.id`) — todos os eventos daquele livro chegam em ordem.
- **Consumer group.** Cada partição é lida por **um** consumer do grupo. Mais consumers que partições = ociosos. Réplicas da sua aplicação com o mesmo `group-id` **dividem** as partições (escala horizontal); `group-id` diferentes recebem **cópias** (fan-out).
- **Offset commit.** O consumer avança o offset depois de processar. Commit **depois** do processamento = *at-least-once* (pode reprocessar após crash) — por isso o consumer é **idempotente** (`messaging`).
- **Retenção** (`retention.ms`) — o broker guarda a mensagem mesmo depois de lida; é isso que permite replay.

---

## application.yml

```yaml
spring:
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    producer:
      acks: all
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JacksonJsonSerializer
      properties:
        enable.idempotence: true
        delivery.timeout.ms: 120000
        linger.ms: 5
        spring.json.add.type.headers: false
    consumer:
      group-id: library-api
      auto-offset-reset: earliest
      enable-auto-commit: false
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.ErrorHandlingDeserializer
      properties:
        spring.deserializer.value.delegate.class: org.springframework.kafka.support.serializer.JacksonJsonDeserializer
        spring.json.trusted.packages: br.com.edimilsonldutra.messaging.event
        spring.json.value.default.type: br.com.edimilsonldutra.messaging.event.BookCreatedEvent
        spring.json.use.type.headers: false
    listener:
      ack-mode: record
      concurrency: 3

app:
  kafka:
    topics:
      book-created: library.book.created.v1
```
- `JsonSerializer`/`JsonDeserializer` acima são os nomes clássicos; **no Spring Kafka 4 (Jackson 3) existem variantes `Jackson…`** — confirme a classe da versão do projeto. Os **parâmetros** (`trusted.packages`, `ErrorHandlingDeserializer`) valem igual.
- **`acks: all` + `enable.idempotence: true`**: o produtor só considera enviado quando todas as réplicas in-sync confirmaram, e retentativas internas **não duplicam** nem reordenam. Esse é o padrão seguro; `acks=1` e `0` podem perder mensagens.
- **`ErrorHandlingDeserializer` é obrigatório** com JSON: sem ele, uma mensagem com payload inválido lança exception *na desserialização, antes* do listener, e o consumer fica **preso na mesma mensagem para sempre** (poison pill). Com ele, a falha vira um erro tratável pelo error handler e vai para a DLT.
- **`spring.json.trusted.packages` restrito** ao package dos eventos. **Nunca `*`**: permite desserializar qualquer classe do classpath a partir de um header controlado por quem publica (vetor de ataque). `use.type.headers: false` + `default.type` fixa o tipo no consumer em vez de confiar no header da mensagem.
- `auto-offset-reset: earliest` define onde começar **quando o grupo ainda não tem offset** (um grupo novo). `earliest` lê tudo desde o início; `latest` ignora o que já existe. Escolha conscientemente (consumer novo que precisa do histórico? → `earliest`).
- `enable-auto-commit: false` com `ack-mode: record` deixa o **Spring** commitar após cada registro processado com sucesso (nunca antes).
- `concurrency: 3` cria 3 threads de consumer **por instância**; o total entre as réplicas não deve passar o nº de partições.
- Dados sensíveis do cluster (SASL, truststore) vão por variáveis de ambiente/Secret (`kubernetes`).

---

## Evento (record)

```java
public record BookCreatedEvent(String eventId, long id, String title, Instant occurredAt) {}
```
Contrato público, no package `messaging/event`. Mudança só **compatível** (campo opcional novo); quebra = tópico `.v2` (`messaging`).

## Tópicos

```java
@Configuration
public class KafkaConfig {

    @Bean
    NewTopic bookCreatedTopic(@Value("${app.kafka.topics.book-created}") String name) {
        return TopicBuilder.name(name)
                .partitions(6)
                .replicas(3)
                .config(TopicConfig.MIN_IN_SYNC_REPLICAS_CONFIG, "2")
                .build();
    }
}
```
- O `KafkaAdmin` do Spring cria o tópico no startup se não existir. **Em produção, tópicos geralmente são gerenciados por infraestrutura como código** (Terraform/Strimzi `KafkaTopic`/MSK) e a aplicação não tem permissão de criar — mantenha o bean para dev/teste, ou controle por profile.
- **Partições:** escolha pelo paralelismo e throughput desejados (número de consumers que quer ter no pico) — **só dá para aumentar, não diminuir**, e aumentar muda o mapeamento key→partição. Comece com um valor razoável (6–12), não 1 nem 1000.
- **`replicas: 3` + `min.insync.replicas: 2` + `acks=all`**: tolera a queda de 1 broker sem perder dados. Exige ≥ 3 brokers (em dev local com 1 broker, use `replicas(1)`).

**Tópico compactado** para eventos de entidade (estado completo por chave — `messaging`): o broker guarda **o último valor de cada chave** em vez de apagar por tempo, e o tópico vira a fonte para reconstruir o estado:
```java
@Bean
NewTopic bookStateTopic(@Value("${app.kafka.topics.book-state}") String name) {
    return TopicBuilder.name(name)
            .partitions(6)
            .replicas(3)
            .compact()
            .config(TopicConfig.MIN_IN_SYNC_REPLICAS_CONFIG, "2")
            .build();
}
```
- A **chave é obrigatória** (sem chave, a compactação não tem o que manter) e é o id da entidade.
- **Apagar** a entidade = publicar um **tombstone** (mesma chave, valor `null`); depois de `delete.retention.ms`, a chave some do tópico. É também o caminho da eliminação LGPD num tópico compactado (`privacy-lgpd`).
- A compactação roda em segundo plano: por um tempo, várias versões da mesma chave convivem. O consumidor **sempre** trata a versão mais nova como a válida.

---

## Producer

```java
@Component
public class BookEventPublisher {

    private static final Logger logger = LoggerFactory.getLogger(BookEventPublisher.class);

    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final String topic;

    public BookEventPublisher(
            KafkaTemplate<String, Object> kafkaTemplate,
            @Value("${app.kafka.topics.book-created}") String topic) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
    }

    public void bookCreated(BookCreatedEvent event) {
        kafkaTemplate.send(topic, String.valueOf(event.id()), event)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        logger.error("Failed to publish {} to {}", event.eventId(), topic, ex);
                    } else {
                        logger.debug("Published {} to partition {} offset {}", event.eventId(),
                                result.getRecordMetadata().partition(), result.getRecordMetadata().offset());
                    }
                });
    }
}
```
- `send` é **assíncrono**: retorna um `CompletableFuture`. Sem tratar o resultado, uma falha **passa em silêncio**. Para garantia real use o **outbox** (`transactional-outbox`): o publisher do outbox espera a confirmação (`.get(timeout)`) antes de marcar como publicado.
- **Sempre passe a key** (id do agregado) para garantir ordem por entidade; sem key a distribuição é round-robin e a ordem se perde.
- Não faça `send` direto de dentro de um método `@Transactional` achando que é atômico com o commit — é o **dual write** (`messaging`).

## Consumer

```java
@Component
public class BookEventListener {

    private static final Logger logger = LoggerFactory.getLogger(BookEventListener.class);

    private final BookIndexService service;

    public BookEventListener(BookIndexService service) {
        this.service = service;
    }

    @KafkaListener(topics = "${app.kafka.topics.book-created}", groupId = "${spring.kafka.consumer.group-id}")
    public void onBookCreated(BookCreatedEvent event) {
        logger.info("Processing {} for book {}", event.eventId(), event.id());
        service.index(event);
    }
}
```
O listener é **fino**: delega ao service, que é `@Transactional` e **idempotente** (tabela de processados com `eventId` único — `transactional-outbox`). Se o método lança exception, o error handler decide: retry → DLT.

---

## Estado materializado a partir de eventos de entidade

Em vez de chamar o `catalog` por HTTP a cada empréstimo, o `lending` mantém uma **cópia local** só com os campos de livro de que precisa, alimentada pelo tópico compactado:
```java
@KafkaListener(topics = "${app.kafka.topics.book-state}", groupId = "${app.kafka.groups.book-replica}")
public void onBookState(@Header(KafkaHeaders.RECEIVED_KEY) String bookId,
                        @Payload(required = false) BookStateEvent state) {
    if (state == null) {
        replica.delete(Long.valueOf(bookId));
        return;
    }
    replica.upsert(state);
}
```
- `@Payload(required = false)` recebe o **tombstone** como `null` (sem isso, o Spring rejeita o valor nulo).
- O `upsert` grava **só se a versão recebida for mais nova** que a guardada (`WHERE version < :version`): reentrega e desordem não fazem o estado andar para trás.
- Um grupo de consumidores **novo** começa do início (`auto-offset-reset: earliest`) e reconstrói a cópia inteira; enquanto isso, a cópia está incompleta. Exponha isso no health ou numa flag de prontidão, e não sirva leituras dela antes de alcançar o fim.
- A cópia é **somente leitura** e **eventualmente consistente**: decisões que exigem o valor exato do momento (estoque disputado) continuam no dono, por comando ou API.
- A tabela da cópia pertence ao consumidor (migration própria — `flyway-migrations`) e guarda só os campos usados; dado pessoal copiado entra no mapa de dados (`privacy-lgpd`).

---

## Falhas: retry e Dead Letter Topic

Defina um `DefaultErrorHandler` (o Spring Boot o aplica ao container padrão de listeners):
```java
@Bean
DefaultErrorHandler errorHandler(KafkaTemplate<Object, Object> template) {
    var recoverer = new DeadLetterPublishingRecoverer(template);
    var backOff = new ExponentialBackOffWithMaxRetries(4);
    backOff.setInitialInterval(1000);
    backOff.setMultiplier(2.0);
    backOff.setMaxInterval(10000);
    var handler = new DefaultErrorHandler(recoverer, backOff);
    handler.addNotRetryableExceptions(IllegalArgumentException.class, DeserializationException.class);
    return handler;
}
```
- Após as tentativas, o `DeadLetterPublishingRecoverer` publica a mensagem em `<tópico>.DLT` (com headers do erro original) e o consumer **segue para a próxima**. Crie e **monitore** o DLT; **alarme se tiver mensagens**.
- **`addNotRetryableExceptions`:** erros permanentes (payload inválido, regra de negócio) vão **direto** para a DLT, sem 4 retries inúteis.
- **Retry bloqueante** (acima): enquanto retenta, a **partição inteira espera** (a ordem é preservada, mas uma mensagem ruim atrasa todas as seguintes daquela partição). Mantenha o backoff **curto**.
- **Retry não bloqueante** — `@RetryableTopic`: a mensagem falha vai para tópicos de retry com atraso crescente e o consumer principal **não para**; ao esgotar, vai para a DLT. Perde a ordem estrita (aceite apenas se o consumer tolera desordem):
```java
@RetryableTopic(attempts = "4", backOff = @BackOff(delay = 2000, multiplier = 2.0), dltStrategy = DltStrategy.FAIL_ON_ERROR)
@KafkaListener(topics = "${app.kafka.topics.book-created}")
public void onBookCreated(BookCreatedEvent event) { ... }

@DltHandler
public void onDlt(BookCreatedEvent event) {
    logger.error("Sent to DLT: {}", event.eventId());
}
```
- Nunca engula a exception no listener (`catch` vazio): o Kafka entenderia como sucesso e **commitaria o offset** — a mensagem estaria perdida.

## Idempotência e exactly-once

- O consumer é **at-least-once**; garanta **idempotência** de negócio (`messaging`, `transactional-outbox`). É a defesa que funciona fim a fim.
- O Kafka oferece **transações** (`transactional.id`) para *read-process-write* **entre tópicos Kafka** de forma atômica: `spring.kafka.producer.transaction-id-prefix: tx-library-` e `isolation.level=read_committed` no consumer. Ajuda em pipelines Kafka→Kafka (Kafka Streams). **Não** torna atômico um efeito em database ou API externa — para isso, idempotência/outbox.

## Ordenação e paralelismo (resumo prático)

| Quero | Faça |
|---|---|
| Ordem por entidade | key = id da entidade |
| Mais throughput | mais partições + mais consumers (≤ partições) |
| Ordem estrita **global** | 1 partição (sem paralelismo — raramente vale) |
| Um consumer lento não parar os outros | retry não bloqueante / mais partições |

**Rebalance:** quando um consumer entra/sai (deploy, HPA, crash), as partições são redistribuídas e o processamento pausa. Mantenha `max.poll.interval.ms` maior que o pior tempo de processamento de um *batch* (`max.poll.records` baixo para processamento lento), ou o consumer é considerado morto e provoca rebalances em cascata. O `CooperativeStickyAssignor` reduz a interrupção. Rolling updates frequentes + muitas partições = observe `rebalance` nas métricas.

---

## Grupos de consumidores, reprocessamento e deploy

- **Nome do grupo estável e com significado**: `<serviço>.<propósito>` (`lending.book-replica`). **Trocar o `group-id` é recomeçar**: o grupo novo lê conforme `auto-offset-reset` (todo o histórico com `earliest`, nada do passado com `latest`). Nunca derive o grupo do hostname ou da versão.
- **Reprocessar ou reconstruir estado** (bug corrigido na projeção, cópia nova): suba a versão nova com um **grupo novo**, deixe-a alcançar o fim do tópico ao lado da versão antiga, compare os resultados e só então troque o tráfego e desligue o grupo antigo. É o blue-green dos consumidores; exige que o efeito seja idempotente ou que a versão nova escreva num destino novo.
- **Reset de offset** de um grupo existente (`kafka-consumer-groups.sh --reset-offsets --to-datetime ... --dry-run`, depois `--execute`) só com **todos os consumidores do grupo parados**, com aprovação, e sabendo que o reprocessamento repete efeitos (e-mails, pagamentos) se o consumidor não for idempotente.
- **Quebra de schema** não se resolve com rolling update: o produtor passa a publicar também no tópico novo (`.v2`), os consumidores migram um a um, e o tópico antigo é desligado com data (`messaging`, `release-management`). Quando produtor e consumidores precisam trocar juntos (estado interno incompatível), planeje uma **parada total** curta e explícita, não um deploy normal.
- Rolling update provoca rebalance a cada pod (seção anterior): em deploy de consumidor com muitas réplicas, observe o lag durante e depois.

---

## Governança de tópicos

Com muitos tópicos e times, cada tópico precisa de:
- **Dono** (o único produtor — `messaging`), registrado junto ao tópico no IaC.
- **Metadados**: schema e compatibilidade, retenção ou compactação, se carrega **dado pessoal**, consumidores conhecidos e canal de contato do dono.
- **ACL de menor privilégio**: `Write` só para o principal do dono; `Read` por grupo de consumidores; ninguém com `Create`/`Delete` fora do pipeline de infraestrutura.
- **Cotas** por `client.id` para um consumidor em reprocessamento não derrubar os outros.
- Criação e alteração **só por IaC** com revisão (`aws-terraform`, `argocd`); a aplicação não cria tópico em produção.

---

## Schema Registry (evolução de contrato em escala)

JSON "solto" funciona para um time pequeno. Com vários times/consumers, use **Schema Registry** (Confluent, Apicurio, AWS Glue) com **Avro/Protobuf/JSON Schema** e regra de compatibilidade (`BACKWARD`/`FULL`): o produtor **não consegue** publicar uma mudança incompatível. Adiciona serializers do registry no lugar de `JsonSerializer` e um serviço a operar; só adote quando o custo de quebra de contrato justificar.

---

## Kafka em Docker (desenvolvimento) e produção

**docker-compose (dev local, modo KRaft — sem ZooKeeper):**
```yaml
services:
  kafka:
    image: apache/kafka:3.9.0
    ports:
      - "9092:9092"
```
(Fixe uma **tag de versão** — nunca `latest` fora de um experimento. A imagem oficial `apache/kafka` já sobe um broker único em KRaft com `localhost:9092`.)

**Produção — não opere Kafka à mão sem necessidade:**
- **Amazon MSK** (Kafka gerenciado): subnets privadas, **TLS** e autenticação **IAM** (SASL/IAM) ou SCRAM, security group aceitando só o do cluster EKS (`aws-eks`), `replicas 3` em 3 AZs. Credenciais por IRSA, nunca chaves.
- **Kubernetes:** o operador **Strimzi** declara `Kafka`, `KafkaTopic` e `KafkaUser` como YAML (`kubernetes`).
- **Confluent Cloud / Redpanda** como alternativas gerenciadas.
Em qualquer um: a aplicação lê `KAFKA_BOOTSTRAP_SERVERS` do ambiente; ACLs por tópico com **menor privilégio** (produtor só `Write`, consumer só `Read` + o group).

## Observabilidade

- Métricas Micrometer do client Kafka (`kafka.consumer.*`, `kafka.producer.*`) e do listener (`spring.kafka.listener.*`) aparecem com Actuator (`observability`). Habilite a **observation** nos templates/containers para **propagar o trace id** nos headers.
- **Consumer lag** (diferença entre o último offset e o do grupo) é **o** alerta: lag crescendo = o consumer não acompanha. Monitore também mensagens na DLT, taxa de rebalance e erros de produção.
- `liveness` **não** depende do Kafka; `readiness` pode, se o pod for inútil sem ele.

## Testes

Use o **broker real em container** (nada de mock do `KafkaTemplate` para provar integração):
```java
@SpringBootTest
class BookEventIntegrationTest {

    @ServiceConnection
    static final KafkaContainer kafka = new KafkaContainer("apache/kafka:3.9.0");

    static {
        kafka.start();
    }

    @Autowired
    private BookEventPublisher publisher;

    @Autowired
    private BookIndexRepository index;

    @Test
    void consumerProcessesThePublishedEventOnce() {
        var event = new BookCreatedEvent(UUID.randomUUID().toString(), 42L, "Clean Code", Instant.now());

        publisher.bookCreated(event);
        publisher.bookCreated(event);

        await().atMost(Duration.ofSeconds(15))
                .untilAsserted(() -> assertThat(index.countByBookId(42L)).isEqualTo(1));
    }
}
```
- `org.testcontainers.kafka.KafkaContainer` (Testcontainers 2; artifact `testcontainers-kafka`) com `@ServiceConnection` liga o app ao container. Fixe a versão da imagem. Alternativa mais leve: `@EmbeddedKafka` (`spring-kafka-test`).
- **Awaitility** (`await()`), nunca `Thread.sleep`.
- Cubra: **duplicata não duplica o efeito** (o teste acima publica 2×), **mensagem inválida vai para a DLT**, e a ordem por key quando importa.
- `auto-offset-reset: earliest` nos testes para o consumer não perder a mensagem publicada antes de ele subir.

---

## Regras principais

- **Key = id do agregado** (ordem por entidade); partições decididas pelo paralelismo e **só crescem**.
- Producer: `acks=all` + `enable.idempotence=true`; trate o resultado do `send` (ou, melhor, publique via **outbox**).
- Consumer: `ErrorHandlingDeserializer` **sempre**; `trusted.packages` restrito (**nunca `*`**); commit só após processar; **idempotente**.
- `DefaultErrorHandler` + DLT com backoff limitado; erros permanentes não retentam; DLT monitorada com alarme; nunca engula exception.
- `@RetryableTopic` quando o atraso de uma mensagem não pode parar a partição (aceitando perder a ordem estrita).
- `replicas 3` + `min.insync.replicas 2` em produção; tópicos por IaC; ACL de menor privilégio; TLS.
- Exactly-once real só Kafka→Kafka; fim a fim = at-least-once + idempotência.
- Monitore **lag**, DLT e rebalances; `max.poll.interval.ms` > tempo de processamento.
- **Eventos de entidade em tópico compactado**, chave obrigatória, tombstone para apagar; cópia local com upsert por versão, grupo novo para reconstruir.
- **Grupo de consumidores estável** (`<serviço>.<propósito>`); reprocessamento com grupo novo lado a lado; reset de offset só com o grupo parado e aprovação; quebra de schema por tópico novo.
- Cada tópico com **dono único, metadados, ACL e cotas**, criado por IaC.
- Teste com Kafka real (Testcontainers) e Awaitility, incluindo duplicata e DLT; versões de imagem fixas.
- Confirme classes/artifacts do Spring Kafka 4 / Boot 4 na versão resolvida.
- **Sem Lombok** — deliberado.

## Referências

- Adam Bellemare, *Building Event-Driven Microservices: Leveraging Organizational Data at Scale* (O'Reilly, 2020): tópicos compactados e estado materializado, grupos de consumidores, reprocessamento, deploy de consumidores e ferramentas de apoio (dono, metadados, cotas e ACL de tópicos).
