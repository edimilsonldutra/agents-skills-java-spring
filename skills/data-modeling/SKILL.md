---
name: data-modeling
description: Modelagem de dados e arquitetura de persistência para APIs Spring Boot — escolha de banco e consistência usando Teorema CAP, PACELC, ACID e BASE, níveis de isolamento SQL (READ COMMITTED, REPEATABLE READ, SERIALIZABLE), anomalias (lost update, write skew, phantom), MVCC e locking (@Version vs SELECT FOR UPDATE), modelagem conceitual/lógica/física (erDiagram), normalização (1FN a 3FN/BCNF) vs desnormalização controlada, chaves (BIGINT IDENTITY, UUIDv7, natural), estados e auditoria, soft delete com impacto em UNIQUE e LGPD, JSONB, índices compostos e parciais, particionamento vs sharding, read replicas e matriz de escolha relacional vs NoSQL. Use quando modelar tabelas ou entidades, decidir entre SQL e NoSQL, definir consistência/isolamento (CAP, PACELC, ACID, BASE) ou planejar índices e particionamento. Não use para escrever código JPA/repository (spring-data-jpa) nem sintaxe de migration SQL (flyway-migrations).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../design-docs/SKILL.md`](../design-docs/SKILL.md) (seção 6: dados e migrations; seção 7: decisões irreversíveis; seção 9: `erDiagram`) e [`../privacy-lgpd/SKILL.md`](../privacy-lgpd/SKILL.md) (minimização, retenção e eliminação). Depois da modelagem, implemente com a skill da tecnologia escolhida: [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md), [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md), [`../aws-rds-secrets-manager/SKILL.md`](../aws-rds-secrets-manager/SKILL.md), [`../aws-dynamodb/SKILL.md`](../aws-dynamodb/SKILL.md), [`../aws-keyspaces/SKILL.md`](../aws-keyspaces/SKILL.md), [`../redis/SKILL.md`](../redis/SKILL.md) ou [`../cqrs-event-sourcing/SKILL.md`](../cqrs-event-sourcing/SKILL.md).

# Modelagem de dados e consistência

**O modelo de dados é a decisão mais cara de reverter em um sistema.** Código se refatora em horas; um schema errado com milhões de registros, chaves mal escolhidas ou uma garantia de consistência mal entendida custa meses de migração e incidentes. Comece entendendo **os padrões de acesso, as invariantes de negócio e a garantia de consistência exigida** — só depois escolha o banco e desenhe tabelas ou partições.

---

## 1. Teorema CAP, PACELC, ACID e BASE (na prática)

Esses quatro modelos respondem a perguntas complementares para escolher o banco e o nível de consistência:

### Teorema CAP — o que acontece quando a rede falha

Em um sistema distribuído, **partições de rede (`P`) são inevitáveis** (switches falham, AZs perdem conectividade, pausas de GC isolam nós). O CAP diz que, **diante de uma partição (`P`)**, você precisa escolher entre:
- **Consistency (`C` — linearizabilidade):** toda leitura retorna a escrita mais recente ou um erro (nunca dado obsoleto). Em partição, o lado sem quórum **recusa** requisições.
- **Availability (`A`):** todo nó não falho responde sem erro — mas pode retornar dado defasado até a partição curar.

> **Mito comum:** "escolha 2 de 3 (CA, CP ou AP)". Em sistemas distribuídos **não existe CA**: você não pode "abrir mão de P", porque partições de rede acontecem quer você queira ou não. Um banco relacional em nó único (ou sem partição de rede) não está sob o trade-off distribuído do CAP; assim que você replica entre nós/AZs/regiões, o trade-off real é **CP × AP durante partição**.

### Teorema PACELC — o que importa também no dia a dia (sem partição)

O CAP fala apenas de **quando há partição**. O **PACELC** (Daniel Abadi) completa a análise para operação normal (**99,9% do tempo**):
> **Se há Partição (`P`)**, escolha entre **A**vailability e **C**onsistency; **Else (`E` — sem partição)**, escolha entre **L**atency e **C**onsistency.

| Classificação PACELC | Em partição (`P`) | Em operação normal (`E`) | Exemplos no pacote | Quando escolher |
|---|---|---|---|---|
| **PC/EC** | Prefere consistência (recusa sem quórum) | Prefere consistência (paga latência de replicação síncrona) | PostgreSQL / MySQL primário (RDS Multi-AZ síncrono), bancos NewSQL (Spanner/CockroachDB) | Financeiro, saldo, estoque, reservas, cadastros com invariantes rígidas (**padrão do pack**) |
| **PA/EL** | Prefere disponibilidade | Prefere baixa latência (leitura eventual) | DynamoDB leitura eventual / GSI (`aws-dynamodb`), Keyspaces `LOCAL_ONE` (`aws-keyspaces`), réplicas de leitura assíncronas | Catálogos, feeds, métricas, buscas, sessões tolerantes a milissegundos de defasagem |
| **PA/EC** | Prefere disponibilidade em partição | Prefere consistência no normal (quórum / leitura forte) | DynamoDB `ConsistentRead=true` (tabela base), Amazon Keyspaces `LOCAL_QUORUM` | Alta disponibilidade em escala com leitura forte por chave (sem JOINs) |
| **PC/EL** *(híbrido)* | Primário consistente | Leitura otimizada em réplica assíncrona ou cache | RDS primário + Read Replica assíncrona, ou banco + Redis (`caching`/`redis`) | Leitura pesada tolerando lag de replicação (exige cuidado com *read-your-own-writes*) |

**Atenção ao Redis/Valkey:** com replicação assíncrona (padrão), um failover pode descartar escritas recém-confirmadas pelo primário (favorece `EL` e se comporta como `PA` em partição sem `WAIT`) — por isso o Redis **não substitui** um banco `PC/EC` como fonte de verdade (`redis`).

### ACID × BASE

| | **ACID** | **BASE** |
|---|---|---|
| **Sigla** | **A**tomicity, **C**onsistency, **I**solation, **D**urability | **B**asically **A**vailable, **S**oft state, **E**ventual consistency |
| **Foco** | Invariantes rígidas garantidas a cada transação ("tudo ou nada") | Disponibilidade, baixa latência e escala horizontal; o estado converge depois |
| **Onde entra** | **Dentro de um serviço** com banco relacional (`spring-data-jpa`, `idempotency`) | **Entre microsserviços** (`microservices`, `transactional-outbox`, `saga-pattern`), projeções (`cqrs-event-sourcing`), GSIs/réplicas |
| **Custo** | Contenção de locks, limite vertical de um nó primário | Complexidade na aplicação: compensações, idempotência, UI que tolera convergência |

**Regra de ouro do pacote:** **ACID dentro do serviço** (padrão); **BASE entre serviços** (outbox + idempotência + saga só quando a fronteira entre serviços é legítima). Nunca abra mão de ACID dentro do mesmo serviço só por "escala" imaginária.

---

## 2. Níveis de isolamento ACID, anomalias e concorrência

"Usar `@Transactional`" não elimina bugs de concorrência sozinho: o **nível de isolamento** define quais anomalias podem acontecer quando duas transações rodam ao mesmo tempo.

| Nível de isolamento | Dirty Read | Non-Repeatable Read | Phantom Read | Write Skew | Custo / contenção |
|---|---|---|---|---|---|
| `READ UNCOMMITTED` | Possível | Possível | Possível | Possível | **Nunca use** em regras de negócio |
| **`READ COMMITTED`** *(default PostgreSQL, Oracle, SQL Server)* | Bloqueado | Possível | Possível | Possível | Baixo (bom default para CRUD comum) |
| **`REPEATABLE READ`** *(default MySQL InnoDB)* | Bloqueado | Bloqueado | Bloqueado no PG (Snapshot) e em locks do InnoDB | **Ainda possível** (no Snapshot Isolation) | Médio |
| **`SERIALIZABLE`** | Bloqueado | Bloqueado | Bloqueado | Bloqueado | Alto (gera `SerializationFailure` — **exige retry**!) |

### As duas anomalias que mais derrubam APIs Spring Boot

1. **Lost Update (atualização perdida):** duas requisições leem `Book` (versão 1), alteram campos e salvam; a segunda sobrescreve a primeira silenciosamente.
   - **Solução padrão:** **optimistic locking** (`@Version` na entity JPA — `spring-data-jpa`; `@DynamoDbVersionAttribute` — `aws-dynamodb`), mapeando `ObjectOptimisticLockingFailureException` para **409 Conflict** (`exception-handling`).
2. **Write Skew (invariante sobre um conjunto de linhas):** ex. *"um leitor pode ter no máximo 3 empréstimos ativos"*. Duas requisições concorrentes do mesmo leitor executam `COUNT(*) WHERE member_id = ? AND status = 'ACTIVE'`, ambas veem `2` (mesmo em `REPEATABLE READ` com MVCC!), e ambas inserem o 3º e o 4º empréstimo!
   - **Soluções práticas (da mais simples para a mais forte):**
     1. **Pessimistic lock no agregado/pai** (`@Lock(LockModeType.PESSIMISTIC_WRITE)` → `SELECT ... FOR UPDATE` na linha do `Member` ou `Book` antes de contar e inserir): serializa apenas as operações **daquele** sócio/livro, sem travar a tabela inteira.
     2. **Constraint única (ou única parcial)** no banco quando a invariante é de unicidade (ex.: um só empréstimo ativo por exemplar físico: `CREATE UNIQUE INDEX uq_active_loan_copy ON loans (copy_id) WHERE status = 'ACTIVE'`).
     3. **`@Transactional(isolation = Isolation.SERIALIZABLE)`** com **retry limitado** para `CannotAcquireLockException`/`ObjectOptimisticLockingFailureException` (só quando não há um registro-pai natural para travar).

- **MVCC (PostgreSQL × MySQL InnoDB):** leituras não bloqueiam escritas e escritas não bloqueiam leituras (cada transação vê um snapshot). Isso é ótimo para vazão, mas **não impede *write skew*** — teste concorrência de verdade com múltiplas threads no Testcontainers (`integration-testing`).
- **Workers/filas em tabela SQL** (como `transactional-outbox`): use `SELECT ... FOR UPDATE SKIP LOCKED` para múltiplos pods pegarem lotes disjuntos sem contenção.
- **Mantenha transações curtas:** nunca chame API HTTP externa, S3, SES ou broker dentro de `@Transactional` — prende locks de linha e esgota o pool Hikari (`aws-rds-secrets-manager`).

---

## 3. Escolha de persistência (qual banco usar)

**Default do pacote: banco relacional (PostgreSQL/MySQL).** Só adicione um segundo tipo de banco quando o padrão de acesso ou a escala **medida** exigirem — e registre em **ADR** (`architect`):

| Necessidade / Padrão de acesso | Melhor escolha | PACELC típico | Skill do pacote |
|---|---|---|---|
| CRUD, transações multi-tabela, relatórios/filtros flexíveis, integridade referencial | **Relacional (PostgreSQL / MySQL)** | PC/EC | `spring-data-jpa`, `flyway-migrations`, `aws-rds-secrets-manager` |
| Acesso por chave conhecida em altíssima escala, latência previsível de ms, serverless | **Chave-valor / Documento (DynamoDB)** | PA/EL ou PA/EC | `aws-dynamodb` |
| Série temporal/partições enormes com modelo Cassandra já existente | **Wide-column (Keyspaces / Cassandra)** | PA/EL ou PA/EC | `aws-keyspaces` |
| Cache compartilhado, rate limit, ranking (`ZSET`), denylist JWT, lock de eficiência | **Em memória (Valkey / Redis)** | PA/EL (sem `WAIT`) | `redis`, `caching` |
| Busca full-text complexa, facetas, relevância | **Motor de busca (OpenSearch / Elasticsearch)** *(projeção derivada, nunca fonte de verdade)* | PA/EL | `cqrs-event-sourcing` |
| Trilha de eventos imutável / projeções múltiplas com auditoria total | **Event Store + CQRS** *(só com forte justificativa)* | PC/EC (escrita) + BASE (projeção) | `cqrs-event-sourcing` |

---

## 4. Modelagem relacional: conceitual → lógico → físico

Passe sempre pelos três níveis antes de escrever a migration (`flyway-migrations`):
1. **Conceitual:** entidades do domínio, relacionamentos, cardinalidades (`1:1`, `1:N`, `N:N`) e regras de negócio — desenhe com Mermaid `erDiagram` na seção 6 do design doc (`design-docs`).
2. **Lógico:** atributos, tipos de domínio, chaves primárias/candidatas, nulabilidade, unicidade e normalização.
3. **Físico:** tipos exatos do SGBD escolhido, constraints (`NOT NULL`, `UNIQUE`, `CHECK`, `FOREIGN KEY`), índices pelos padrões de consulta reais, particionamento e retenção — traduzido diretamente em SQL no Flyway.

### Normalização (1FN–3FN/BCNF) vs Desnormalização controlada

- **Comece na 3ª Forma Normal (3FN):**
  - **1FN:** valores atômicos (sem listas separadas por vírgula em uma coluna `VARCHAR`).
  - **2FN:** todo atributo não-chave depende da chave primária inteira (relevante em chaves compostas).
  - **3FN / BCNF:** nenhum atributo não-chave depende transitivamente de outro atributo não-chave ("cada fato mora em um único lugar").
- **Quando desnormalizar de propósito (e documentar no design doc):**
  1. **Snapshot histórico imutável** (ex.: `unit_price` e `book_title` gravados em `order_items` no momento da compra): **não é erro de normalização** — o preço do catálogo muda amanhã, mas o recibo da compra não pode mudar.
  2. **Leitura quente medida** (ex.: contador pré-calculado ou projeção de leitura em `cqrs-event-sourcing`): só depois de provar que um índice não basta, deixando claro **qual tabela é a fonte de verdade** e como o valor derivado é mantido coerente (mesma transação ACID ou evento via `transactional-outbox`).

### Chaves primárias (`BIGINT` × `UUIDv7` × natural)

| Estratégia | Prós | Contras | Quando usar |
|---|---|---|---|
| **`BIGINT` (`IDENTITY`)** *(padrão do pack)* | 8 bytes, sequencial (zero fragmentação B-Tree), ótimo para índices secundários e `JOIN` | Expõe sequência/volume se exposto na URL; gerado só no banco | **Default** para entidades internas e CRUDs (`spring-data-jpa`) |
| **`UUIDv7` / ULID** (ordenado no tempo) | Não previsível na URL, pode ser gerado na aplicação (útil em sistemas distribuídos/idempotência), inserção sequencial na B-Tree | 16 bytes (dobra o tamanho das FKs e índices secundários); armazene como `UUID` nativo (PG) ou `BINARY(16)` (MySQL), nunca `CHAR(36)` | ID público exposto na API (`public_id` + `BIGINT` interno) ou PK distribuída |
| **`UUIDv4` (aleatório)** | Não previsível | **Fragmenta severamente a B-Tree** (inserções aleatórias destroem a localidade de página e o buffer pool) | **Evite como PK** em tabelas grandes; troque por `UUIDv7` |
| **Chave natural** (e-mail, CPF, ISBN) | Sem coluna extra | Muda com o tempo, acopla FKs a dados mutáveis e **espalha PII** por todas as tabelas filhas | **Evite como PK**; use surrogate PK + `UNIQUE` na coluna natural |

### Tipos, integridade, estados e *soft delete*

- **Integridade mora no banco, não só no Java:** `NOT NULL`, `UNIQUE`, `CHECK` (`price >= 0`, `due_date >= loan_date`) e `FOREIGN KEY` com `ON DELETE` explícito (`RESTRICT` por padrão — evite `ON DELETE CASCADE` em dados financeiros, pedidos ou auditoria).
- **Dinheiro e tempo:** `DECIMAL(10,2)` (`BigDecimal`, nunca `FLOAT`/`DOUBLE`); datas sem hora como `DATE` (`LocalDate`); instantes em **UTC** (`TIMESTAMP WITH TIME ZONE` no PostgreSQL / `TIMESTAMP`/`DATETIME(6)` em UTC no MySQL → `Instant`).
- **Estados explícitos vs *soft delete* (`deleted_at`):**
  - Para fluxos de negócio, modele o **ciclo de vida explícito** (`status`: `ACTIVE`, `RETURNED`, `CANCELLED` + `cancelled_at` / tabela de histórico) em vez de um booleano `deleted`.
  - **Cuidados se adotar *soft delete* (`deleted_at`):**
    1. **Quebra `UNIQUE`:** excluir um usuário e cadastrá-lo de novo falha na constraint `UNIQUE (email)`. No PostgreSQL resolva com índice único parcial (`CREATE UNIQUE INDEX uq_users_email_active ON users (email) WHERE deleted_at IS NULL`); no MySQL use coluna gerada ou mova para tabela de arquivo.
    2. **Vazamento em queries e relatórios:** toda query precisa lembrar do filtro `deleted_at IS NULL` (alto risco de bug silencioso).
    3. **LGPD (`privacy-lgpd`):** *soft delete* **NÃO é eliminação**! Quando o titular pede exclusão ou vence a retenção, os dados pessoais precisam ser **apagados ou anonimizados de verdade** (inclusive em backups/projeções conforme a política).
- **JSON / JSONB:** útil para metadados variáveis, payloads de webhook/outbox ou preferências sem regra relacional. **Não enfie o modelo principal em uma coluna JSONB**: você perde FKs, tipos fortes, constraints e legibilidade de schema.

---

## 5. Índices, particionamento, sharding e réplicas

### Índices (desenhe pelos `WHERE`, `JOIN` e `ORDER BY` reais)

- **Regra do prefixo mais à esquerda (índice composto B-Tree):** um índice em `(member_id, status, due_date)` atende consultas por `(member_id)`, `(member_id, status)` e `(member_id, status, due_date)`, mas **não** ajuda quem filtra só por `due_date`.
- **Ordem das colunas:** **igualdade (`=`) primeiro, faixa (`>`, `<`, `BETWEEN`) e ordenação (`ORDER BY`) por último**.
- **Índices obrigatórios:** toda coluna de **FK** consultada em `JOIN` ou verificada em `DELETE` (o MySQL cria automaticamente; o **PostgreSQL NÃO cria índice em FK** sozinho — crie explicitamente na migration!).
- **Índices parciais e *covering*:** em tabelas grandes onde só uma fração está ativa (ex.: `outbox_events WHERE published_at IS NULL`), um índice parcial é minúsculo e muito rápido. Em queries de leitura intensa, *covering index* (`INCLUDE (...)`) permite *Index-Only Scan*.
- **Custo:** cada índice extra torna `INSERT`/`UPDATE`/`DELETE` mais lentos e consome RAM. Nunca crie índice "por precaução": confirme com `EXPLAIN (ANALYZE, BUFFERS)` sobre volume representativo (`jvm-performance`).

### Particionamento, sharding e réplicas de leitura

- **Particionamento de tabela** (mesmo banco — ex.: tabela `audit_logs` ou `loans` particionada por mês via `PARTITION BY RANGE (created_at)`):
  - Benefício principal: **retenção/expurgo instantâneo** (`DROP TABLE`/`DETACH PARTITION` sem travar nem gerar bloat de `DELETE`) e índices menores que cabem em RAM.
  - Restrição importante: no PostgreSQL e no MySQL, **toda PK e constraint `UNIQUE` precisa incluir a coluna de particionamento**.
- **Read Replicas (escala de leitura):** réplicas são normalmente **assíncronas** (modelo `PC/EL` / eventual). Se o usuário cria um recurso (`POST`) e logo em seguida faz `GET` caindo na réplica, pode receber `404` (*replication lag*). Mitigue devolvendo o recurso criado na resposta do `POST` e roteando fluxos *read-your-own-writes* para o primário (ex.: `@Transactional(readOnly = true)` só envia à réplica em consultas explicitamente tolerantes a lag).
- **Sharding horizontal:** divide os dados em múltiplos bancos independentes por chave de shard (ex.: `tenant_id`). **Último recurso:** elimina transações ACID e `JOIN`s entre shards, complica rebalanceamento e migrations. Antes de considerar sharding, esgote: queries/índices, paginação keyset (`pagination`), pool + cache (`caching`/`redis`), read replicas, particionamento e escala vertical.

---

## 6. Validação do modelo (design doc, QA e code review)

- **No design doc (`design-docs` §6 e §7):** inclua o `erDiagram` (Mermaid), as **invariantes de consistência** (onde precisa de ACID/lock e onde aceita BASE/eventual), os **padrões de consulta** com os índices planejados, o volume estimado em 3 anos, a estratégia de retenção/LGPD e marque mudanças de schema existentes como **decisões irreversíveis** (expand → contract, `flyway-migrations`).
- **Em testes (`qa`, `integration-testing`):** prove as invariantes sob **concorrência real** (N threads simultâneas contra o banco em Testcontainers para pegar *lost update* e *write skew*), valide constraints `UNIQUE`/`CHECK`/`NOT NULL` no banco (não só Bean Validation) e confira `EXPLAIN` nas consultas críticas.
- **Na revisão (`code-reviewer`):** valide integridade no banco, controle de concorrência em invariantes críticas, ausência de `UUIDv4` como PK em tabela grande, ausência de PII como PK ou em índice desnecessário, índice em FK no PostgreSQL, impacto de *soft delete* em `UNIQUE`/LGPD e compatibilidade *expand → contract*.

---

## Regras principais

- **Justifique consistência com CAP, PACELC e ACID × BASE:** **ACID (`PC/EC`) dentro do serviço** é o padrão do pacote; **BASE / consistência eventual** entre serviços (`transactional-outbox`, `saga-pattern`) ou em leituras onde o negócio tolera defasagem (GSI, réplicas assíncronas, projeções CQRS).
- **Nível de isolamento e concorrência explícitos:** `READ COMMITTED` / `REPEATABLE READ` com MVCC **não impedem *write skew*** — use `@Version` para *lost update* e lock pessimista no registro-pai (`SELECT FOR UPDATE`), constraint única parcial ou `SERIALIZABLE` com retry para invariantes sobre conjuntos.
- **Relacional primeiro** (`spring-data-jpa`, `aws-rds-secrets-manager`); banco NoSQL ou segundo motor exige padrão de acesso/escala medido e **ADR** (`architect`).
- **3FN por padrão; desnormalização só intencional e documentada** (snapshot histórico imutável ou leitura quente medida, sempre com fonte de verdade declarada).
- **Chaves:** `BIGINT IDENTITY` como padrão interno; `UUIDv7`/ULID quando precisar de ID público ou gerado fora do banco; **evite `UUIDv4` como PK** em tabelas grandes e **nunca use PII como PK**.
- **Integridade no banco:** `NOT NULL`, `UNIQUE`, `CHECK`, FKs com `ON DELETE` explícito (`RESTRICT` por padrão), `DECIMAL` para dinheiro e UTC (`Instant`) para timestamps.
- **Estados explícitos em vez de *soft delete* genérico;** se usar `deleted_at`, resolva `UNIQUE` com índice parcial e **nunca trate *soft delete* como eliminação LGPD** (`privacy-lgpd`).
- **JSONB só para dados realmente semi-estruturados** (nunca para entidades centrais com FK/regras de negócio).
- **Índices guiados pelas consultas reais** (igualdade antes de faixa/ordenação, índice em FK no PostgreSQL, parciais onde couber, validados com `EXPLAIN`); **particionamento** antes de **sharding**; trate *read-your-own-writes* ao usar read replicas.
- **Evolução sempre por `flyway-migrations` (expand → contract)** — mudanças em schema publicado são decisões irreversíveis (`design-docs` §7).
