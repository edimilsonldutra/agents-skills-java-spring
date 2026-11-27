---
name: jpa-advanced-mapping
description: Mapeamento JPA avançado com Hibernate 7 e Spring Data JPA 4 — auditoria (@CreatedDate, AuditorAware, Clock), @Embeddable (record) e AttributeConverter, herança vs composição, @ElementCollection, bidirecional sincronizado, cascade/orphanRemoval, persist vs merge, escrita em lote, lock pessimista com timeout, @SoftDelete e cache L2. Use quando o CRUD básico de spring-data-jpa não basta. Não use para CRUD/N+1/testes de repository (spring-data-jpa), escolha de banco/isolamento (data-modeling) nem SQL de schema (flyway-migrations).
---

Antes de aplicar este pattern, leia também [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md) (o padrão de entity, repository e transação que esta skill estende), [`../data-modeling/SKILL.md`](../data-modeling/SKILL.md) (consistência, locking e soft delete como decisão), [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md) (toda coluna nova nasce numa migration), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../library-docs/SKILL.md`](../library-docs/SKILL.md) (confirme anotações e properties na versão resolvida).

# Mapeamento JPA avançado

A `spring-data-jpa` cobre o CRUD do pacote: entity explícita, `IDENTITY`, sem `BaseEntity`, sem Lombok, Flyway dono do schema. Esta skill reúne o que aparece quando o domínio cresce. **Cada recurso aqui tem custo** (mais mapeamento, mais SQL implícito, mais coisa para o próximo dev entender): use quando resolver um problema concreto, e registre as escolhas estruturais (herança, `SEQUENCE`, cache de segundo nível) no `CLAUDE.md` ou em ADR. Toda coluna e tabela citada aqui nasce numa migration (`flyway-migrations`); `ddl-auto` continua `none`.

## 1. Auditoria: quem e quando

```java
@Configuration
@EnableJpaAuditing(dateTimeProviderRef = "auditingDateTimeProvider")
public class JpaAuditingConfig {

    @Bean
    public AuditorAware<String> auditorAware() {
        return () -> Optional.ofNullable(SecurityContextHolder.getContext().getAuthentication())
            .filter(auth -> auth.isAuthenticated() && !(auth instanceof AnonymousAuthenticationToken))
            .map(Authentication::getName);
    }

    @Bean
    public DateTimeProvider auditingDateTimeProvider(Clock clock) {
        return () -> Optional.of(Instant.now(clock));
    }
}
```
```java
@Entity
@Table(name = "books")
@EntityListeners(AuditingEntityListener.class)
public class Book implements Serializable {

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @CreatedBy
    @Column(name = "created_by", updatable = false, length = 100)
    private String createdBy;

    @LastModifiedBy
    @Column(name = "updated_by", length = 100)
    private String updatedBy;
```
- O `DateTimeProvider` com o `Clock` injetado deixa os testes determinísticos (`test-patterns`). Sem ele, o Spring Data usa a hora do sistema.
- O pacote não usa `BaseEntity`: repita os quatro campos nas entities auditadas. Com muitas entities, um `@Embeddable` de auditoria é a alternativa (o Spring Data aceita os metadados num objeto embutido; confirme na versão), registrada no `CLAUDE.md`.
- **Query `@Modifying` não passa pelo listener**: atualização em massa precisa setar `updated_at` na própria query (`spring-data-jpa`).
- Auditoria guarda **a última** mudança. Histórico completo é outra coisa: Hibernate Envers ou eventos (`cqrs-event-sourcing`). `created_by` identifica pessoas: entra no mapa de dados pessoais (`privacy-lgpd`).

**Callbacks** (`@PrePersist`, `@PreUpdate`, `@PostLoad`) servem para **derivar ou normalizar o próprio estado** (ISBN sem hífen, e-mail em minúsculas). Dentro deles: nada de repository, chamada remota, outra entity alterada ou regra de negócio; isso vai para o service ou para o domínio.

## 2. Value objects: `@Embeddable` e `AttributeConverter`

Quando o domínio tem um valor com regra (`Money`, `Isbn`, `Address`), o Jakarta Persistence 3.2 aceita **record** como `@Embeddable`:
```java
@Embeddable
public record Money(
    @Column(name = "price_amount", nullable = false, precision = 10, scale = 2) BigDecimal amount,
    @Column(name = "price_currency", nullable = false, length = 3) String currency) {

    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        if (amount.signum() < 0) throw new IllegalArgumentException("Negative amount");
    }
}
```
```java
@Embedded
private Money price;

@Embedded
@AttributeOverride(name = "amount", column = @Column(name = "fine_amount"))
@AttributeOverride(name = "currency", column = @Column(name = "fine_currency"))
private Money fine;
```
- Colunas na própria tabela, sem join; `@AttributeOverride` quando a entity tem dois do mesmo tipo.
- Usar no **flat-by-layer** só quando há regra no valor; o padrão do pacote para preço segue `BigDecimal` simples (`spring-data-jpa`). Em domínio rico, é o caminho natural (`ddd-hexagonal`).
- O **MapStruct** (default do pacote) mapeia records e value objects nativamente; em projetos legados com **Dozer** (que exige construtor vazio e setters), mapeie value objects à mão.

**`AttributeConverter`** mapeia um tipo para **uma** coluna. O caso típico é enum com **código estável**, quando o nome da constante pode mudar ou o banco legado usa códigos:
```java
@Converter(autoApply = true)
public class LoanStatusConverter implements AttributeConverter<LoanStatus, String> {

    @Override
    public String convertToDatabaseColumn(LoanStatus status) {
        return status == null ? null : status.getCode();
    }

    @Override
    public LoanStatus convertToEntityAttribute(String code) {
        return code == null ? null : LoanStatus.fromCode(code);
    }
}
```
O padrão continua `@Enumerated(EnumType.STRING)` (`spring-data-jpa`); o converter é para quando o nome não pode ser o contrato. Converter não se aplica a `@Id` nem a `@Version`, e código desconhecido no banco deve lançar exception clara em `fromCode`, não devolver `null`.

## 3. Herança: quase sempre composição

| Estratégia | Tabelas | Prós | Contras |
|---|---|---|---|
| `@MappedSuperclass` | Só as das subclasses | Compartilha mapeamento sem polimorfismo | Não é entity: sem consulta polimórfica. No pacote, só para mapeamento realmente comum e registrado (não é `BaseEntity` genérica) |
| `SINGLE_TABLE` (default) | Uma, com discriminador | Rápida, sem join, consulta polimórfica simples | Colunas das subclasses anuláveis; a obrigatoriedade vira `CHECK` na migration |
| `JOINED` | Uma por classe | Normalizada, `NOT NULL` por subclasse | Join em toda leitura, dois `INSERT`s por registro |
| `TABLE_PER_CLASS` | Uma por classe concreta | Tabelas independentes | Consulta polimórfica com `UNION`; não funciona com `IDENTITY`. Evite |

```java
@Entity
@Table(name = "library_items")
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "item_type", length = 20)
public abstract class LibraryItem implements Serializable { }

@Entity
@DiscriminatorValue("PRINTED")
public class PrintedBook extends LibraryItem { }

@Entity
@DiscriminatorValue("EBOOK")
public class EBook extends LibraryItem { }
```
**Antes de herdar, pergunte se um campo de tipo resolve**: `LibraryItem` com `itemType` (enum) e o comportamento variável numa estratégia (`design-patterns`) é mais simples de mapear, migrar e consultar. Herança de entity faz sentido quando os subtipos têm **dados** diferentes e são consultados juntos. Se for herdar, `SINGLE_TABLE` é o ponto de partida; `JOINED` quando as subclasses têm muitas colunas próprias e obrigatórias.

## 4. Coleções de valores e ordenação

**`@ElementCollection`** guarda valores **sem identidade** numa tabela filha:
```java
@ElementCollection
@CollectionTable(name = "book_tags", joinColumns = @JoinColumn(name = "book_id"))
@Column(name = "tag", nullable = false, length = 50)
private Set<String> tags = new HashSet<>();
```
- Lazy por padrão; sem id próprio, não é consultável como entity e não tem auditoria.
- Use **`Set`**: com `List` sem coluna de ordem, o Hibernate apaga e reinsere a coleção inteira a cada mudança.
- Coleção grande, com dados próprios ou consultada sozinha: vira **entity** com `@OneToMany`.

**Ordem estável:** `@OrderBy("createdAt DESC")` ordena na leitura (vira `ORDER BY`, nada é gravado); `@OrderColumn(name = "position")` **persiste** a posição para listas ordenadas pelo usuário (capítulos, playlist), ao custo de atualizar posições a cada inserção no meio. Sem nenhum dos dois, a ordem de uma coleção é **indefinida**.

## 5. Relacionamento bidirecional: os dois lados

O **dono** da relação é o lado com a FK (`@ManyToOne`, o lado sem `mappedBy`). Mudar só o lado inverso (`book.getReviews().add(review)`) **não grava a FK**. Sincronize os dois lados num método da entity dona da coleção:
```java
public void addReview(BookReview review) {
    reviews.add(review);
    review.setBook(this);
}

public void removeReview(BookReview review) {
    reviews.remove(review);
    review.setBook(null);
}
```
- Sem setter da coleção inteira (`setReviews`): trocar a instância quebra o `orphanRemoval`. Mapeamento de DTO para entity passa pelos métodos `add`/`remove`.
- **`cascade = ALL` + `orphanRemoval = true` só em composição** (o `Book` é dono das `BookReview`, que não existem sem ele). **Nunca cascade em `@ManyToOne`** ou para entity compartilhada: apagar um empréstimo com cascade para o livro apaga o livro.
- `@ManyToMany` com dado na associação (quantidade, data) vira **entity própria** (`LoanItem`), com dois `@ManyToOne`.
- O pacote usa `List` em `@OneToMany`. Se usar `Set` de entities, `equals`/`hashCode` não podem depender do id gerado (ele muda depois do `persist` e o elemento se perde no `HashSet`).

## 6. `persist` × `merge`, referências e escrita em lote

- O `save()` do Spring Data faz `persist` quando a entity é nova (id ou `@Version` nulos) e `merge` caso contrário. O `merge` **devolve a instância gerenciada**: use o retorno, não o objeto passado.
- **Nunca faça `merge` de uma entity montada a partir do DTO** (`mapper.toEntity(dto)` com id): o que não veio no DTO vira `null` no banco e o `@Version` do cliente é ignorado. Carregue, altere e salve, como no `update` do pacote.
- **`getReferenceById(id)`** devolve um proxy **sem `SELECT`**, para apontar uma FK: `loan.setBook(bookRepository.getReferenceById(bookId))`. Se o id não existir, o erro só aparece no flush (violação de FK) ou ao acessar o proxy. Com id vindo do cliente, valide existência **e dono** antes (`application-security`: IDOR).

**Escrita em lote** (importação de milhares de linhas — `file-import-export`):
- Com `IDENTITY` (padrão do pacote), o Hibernate **não agrupa inserts** em batch JDBC: cada `persist` precisa do id gerado pelo banco. Para volume grande, use `JdbcTemplate.batchUpdate` na importação, ou mude a entity para `SEQUENCE`:
  ```java
  @Id
  @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "loan_seq")
  @SequenceGenerator(name = "loan_seq", sequenceName = "loan_seq", allocationSize = 50)
  private Long id;
  ```
  O `INCREMENT BY` da sequence na migration **tem de ser igual** ao `allocationSize`. PostgreSQL, Oracle, SQL Server e MariaDB têm sequences; o MySQL não. Trocar a estratégia é decisão registrada em ADR.
- Com `SEQUENCE`: `hibernate.jdbc.batch_size: 50`, `hibernate.order_inserts: true` e `hibernate.order_updates: true` em `spring.jpa.properties`.
- Dentro de uma transação longa, **esvazie o contexto de persistência** a cada lote, senão ele cresce até o `OutOfMemoryError`:
  ```java
  for (int i = 0; i < rows.size(); i++) {
      entityManager.persist(toEntity(rows.get(i)));
      if ((i + 1) % 50 == 0) {
          entityManager.flush();
          entityManager.clear();
      }
  }
  ```
  Depois do `clear()`, toda entity carregada antes fica desanexada.
- `@Modifying` em massa ignora contexto de persistência, listeners, cascade e `@Version`: use `clearAutomatically = true` e trate auditoria e versão na própria query (`spring-data-jpa`).

## 7. Lock pessimista no repository

O padrão para edição concorrente é o **otimista** (`@Version` — `data-modeling`; pela API, `If-Match` — `api-design`). O pessimista serve quando a invariante envolve **contar ou somar outras linhas** antes de inserir (limite de empréstimos por sócio) ou quando o conflito é frequente:
```java
public interface MemberRepository extends JpaRepository<Member, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @QueryHints(@QueryHint(name = "jakarta.persistence.lock.timeout", value = "3000"))
    @Query("SELECT m FROM Member m WHERE m.id = :id")
    Optional<Member> findByIdForUpdate(@Param("id") Long id);
}
```
- Exige transação ativa (`@Transactional` no service); sem ela, `TransactionRequiredException`.
- O lock dura **até o commit**: nada de chamada remota ou processamento longo na transação.
- O suporte ao timeout **varia por banco e dialeto** (alguns só aceitam `0`, que é `NOWAIT`, ou ignoram o valor): confirme no dialeto e prove num teste contra o banco real (`integration-testing`).
- Falha ao obter o lock (`PessimisticLockingFailureException`, `CannotAcquireLockException`) vira **409** ou **503** no handler (`exception-handling`), nunca 500.
- Fila de trabalho com várias réplicas: `SKIP LOCKED` (`data-modeling`).

## 8. `@SoftDelete` do Hibernate

Se a decisão de soft delete já foi tomada (`data-modeling` prefere estados explícitos), o Hibernate 7 implementa sem filtro manual:
```java
@Entity
@Table(name = "members")
@SoftDelete(strategy = SoftDeleteType.TIMESTAMP, columnName = "deleted_at")
public class Member implements Serializable { }
```
O `delete` vira `UPDATE`, e as consultas da entity passam a filtrar as linhas apagadas. Cuidados: **query nativa não filtra**; `UNIQUE` precisa de índice parcial (`data-modeling`); a coluna nasce na migration; e **soft delete não é eliminação LGPD** (`privacy-lgpd`).

## 9. Cache de segundo nível

O cache de segundo nível do Hibernate guarda **entities por id** entre transações. Compare antes com o cache de DTO no service (`caching`), que é o padrão do pacote e costuma ser mais simples.
| Combina | Não combina |
|---|---|
| Dado de **referência** e dado **mestre** pouco alterado, lido por id | Dado **operacional** (empréstimos, reservas) |
| `READ_ONLY` para o que nunca muda | Tabela alterada por outra aplicação ou por `@Modifying` em massa (o cache não fica sabendo) |
| Uma réplica, ou provider distribuído | Várias réplicas com cache **local** em dado que muda (cada pod vê uma versão) |

Configuração: dependência `org.hibernate.orm:hibernate-jcache` com um provider JCache; `hibernate.cache.use_second_level_cache: true` e `hibernate.cache.region.factory_class: jcache`; na entity, `@Cacheable` (Jakarta) e `@Cache(usage = CacheConcurrencyStrategy.READ_ONLY)` (Hibernate). **Cache de query** (`hibernate.cache.use_query_cache`) raramente compensa. Meça hit ratio antes e depois (`observability`).

---

## Regras principais

- **Auditoria com Spring Data** (`@EnableJpaAuditing`, `AuditorAware` sem usuário anônimo, `DateTimeProvider` com `Clock`); campos explícitos ou `@Embeddable`, nunca `BaseEntity` genérica; `@Modifying` seta auditoria na query; callbacks só normalizam o próprio estado.
- **Value objects** como `@Embeddable` record com validação no construtor e `@AttributeOverride` para repetições; `AttributeConverter` para enum com código estável; MapStruct mapeia records (Dozer legado não).
- **Composição antes de herança**; se herdar, `SINGLE_TABLE` com `CHECK` na migration, `JOINED` para subtipos grandes, nunca `TABLE_PER_CLASS`.
- **`@ElementCollection` com `Set`** e só para valores pequenos; ordem estável com `@OrderBy` ou `@OrderColumn`.
- **Bidirecional sincronizado** por `add`/`remove` na entity dona da coleção; cascade e `orphanRemoval` só em composição; nunca cascade em `@ManyToOne`.
- **Carregar, alterar e salvar**; nunca `merge` de entity montada do DTO; `getReferenceById` com validação de existência e dono.
- **Lote**: `IDENTITY` não agrupa inserts (`JdbcTemplate.batchUpdate` ou `SEQUENCE` com `allocationSize` igual ao `INCREMENT BY`, via ADR); `flush`/`clear` por lote.
- **Lock pessimista** só para invariante sobre outras linhas, com timeout confirmado no banco real e transação curta; otimista como padrão.
- **`@SoftDelete`** só depois da decisão em `data-modeling`; **cache de segundo nível** só para referência e mestre medidos.
- **Sem Lombok** — deliberado.

## Referências

- *Hibernate ORM 7 User Guide* e especificação *Jakarta Persistence 3.2*; *Spring Data JPA* (auditoria, locking, `@QueryHints`). Anotações e properties conferidas nos jars `hibernate-core` 7.4.17 e `spring-data-jpa` 4.2.0.
- Vlad Mihalcea, *High-Performance Java Persistence* (2016): base conceitual de batching, identificadores, locking e cache de segundo nível.
