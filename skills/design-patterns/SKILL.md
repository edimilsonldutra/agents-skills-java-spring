---
name: design-patterns
description: Padrões de projeto (os 23 do GoF e os corporativos) aplicados a Spring Boot e Java 25 no padrão do pacote — princípios do catálogo e causas de reprojeto, Strategy, Factory, Template Method, Adapter, Decorator e Proxy (AOP, @Transactional, auto-invocação), Observer com eventos do Spring, Builder, Singleton e beans sem estado, Chain of Responsibility (filtros), State com enum/sealed, Facade, Command, Composite, Mediator, Visitor como switch sobre sealed, Factory Method × Abstract Factory, o que o Java já resolve (Iterator, Flyweight, Prototype), Specification para filtros dinâmicos, Repository e DTO — com onde o próprio Spring já os usa, quando usar, quando não usar e como testar. Use ao escolher como estruturar uma solução recorrente, ao revisar design ou quando alguém propuser um padrão.
---

Antes de aplicar este pattern, leia também [`../solid/SKILL.md`](../solid/SKILL.md) (os princípios por trás dos padrões), [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md). Mudar código existente: [`../refactoring/SKILL.md`](../refactoring/SKILL.md). Padrões de arquitetura distribuída: [`../microservices/SKILL.md`](../microservices/SKILL.md) e as skills citadas na seção 4.

# Padrões de projeto

Um padrão é **uma solução conhecida para um problema recorrente** — e um **vocabulário**: dizer "é um Strategy" explica o desenho em duas palavras. O erro comum é o inverso: começar pelo padrão e procurar onde encaixá-lo. **Comece pelo problema.** Sem o problema, o padrão é só indireção (`refactoring`: design pattern sem problema real é over-engineering).

O Spring já implementa vários padrões para você — reconhecê-los evita reimplementá-los mal.

## Princípios do catálogo (o que vem antes do padrão)

O catálogo original (Gamma, Helm, Johnson e Vlissides, o "GoF") abre com três princípios; os 23 padrões são aplicações deles:
- **Programe para uma interface, não para uma implementação.** Quem usa depende do contrato (`LateFeePolicy`, `BookCatalog`), não da classe concreta; o Spring injeta a implementação. Não significa "interface + `Impl` para tudo" (`solid`, D): a interface nasce quando há mais de uma implementação real, um port ou uma dependência instável.
- **Prefira composição a herança.** Herança é reaproveitamento em tempo de compilação, e a subclasse enxerga os detalhes da superclasse. Composição troca comportamento em tempo de execução por **delegação** a um colaborador injetado. Herança fica para o "é um" com o mesmo contrato (Liskov — `solid`).
- **Encapsule o que varia.** Identifique o que muda (a regra de multa, o formato de exportação, o parceiro) e coloque atrás de uma fronteira; o que não muda não precisa de abstração.

**Causas de reprojeto**, e os padrões que as evitam (use como diagnóstico quando uma mudança pequena está custando caro):
| Causa | Sintoma no pacote | Padrões |
|---|---|---|
| Criar objetos nomeando a classe concreta | `new SmtpClient(...)` dentro do service | Factory Method, Abstract Factory (no Spring: injeção) |
| Depender de uma operação específica | O chamador sabe exatamente qual método de qual classe atende o pedido | Chain of Responsibility, Command |
| Depender de plataforma ou de representação | Domínio usando DTO e exceptions do parceiro, ou do SDK | Adapter, Abstract Factory, Bridge, Proxy |
| Depender de um algoritmo | Regra de cálculo embutida em quem a usa | Strategy, Template Method, Builder, Iterator, Visitor |
| Acoplamento forte | Classes que só funcionam juntas; mudar uma quebra as outras | Facade, Mediator, Observer, Command, Bridge |
| Estender por subclasse | Hierarquia que cresce a cada variação (`PremiumStudentLoanService`) | Decorator, Strategy, Composite, Observer, Chain |
| Não poder alterar a classe | Classe de biblioteca ou de outro time | Adapter, Decorator, Visitor |

**Para escolher**, leia a **intenção** de cada candidato (a primeira frase de cada seção abaixo), pergunte **o que deve poder variar sem mudar o resto** e compare as **consequências**: todo padrão compra flexibilidade com indireção.

## Mapa rápido

| Problema | Padrão | No Spring / no pacote |
|---|---|---|
| Um algoritmo que varia por tipo (formato, meio de pagamento, regra de cálculo) | **Strategy** | `FileExporter` por formato (`file-import-export`) |
| Escolher/criar a implementação certa em tempo de execução | **Factory** | `FileExporterFactory`, o próprio container de beans |
| Mesmo esqueleto, passos que variam | **Template Method** | `JdbcTemplate`, `RestClient`, `AbstractIntegrationTest` |
| Encaixar uma interface externa no seu modelo | **Adapter** | Anti-corruption layer (`service-communication`), adapters do hexagonal |
| Acrescentar comportamento sem mudar a classe | **Decorator** / **Proxy** | `@Transactional`, `@Cacheable`, `@Async`, `@PreAuthorize` (AOP) |
| Avisar interessados sem conhecê-los | **Observer** | `ApplicationEventPublisher` + `@EventListener`/`@TransactionalEventListener` |
| Construir objetos com muitos parâmetros opcionais | **Builder** | `RestClient.builder()`, `OpenAPI`, `PageRequest`; records para dados |
| Uma instância compartilhada | **Singleton** | Todo bean do Spring (escopo padrão) — **sem estado mutável** |
| Uma requisição passando por etapas que podem interromper | **Chain of Responsibility** | `SecurityFilterChain`, `HandlerInterceptor`, filtros do Gateway |
| Comportamento que depende do estado do objeto | **State** | Enum/sealed com transições explícitas |
| Simplificar um subsistema para quem chama | **Facade** | O service que orquestra repositories e componentes |
| Filtros combináveis montados em tempo de execução | **Specification** | `Specification<T>` do Spring Data JPA |
| Isolar o acesso a dados / transportar dados entre camadas | **Repository** / **DTO** | Spring Data; `*DTO` do pacote |
| Tratar uma operação como dado (enfileirar, registrar, repetir, agendar) | **Command** | Records de comando + handler, `Runnable` num executor, mensagem numa fila |
| Combinar regras ou objetos em árvore, tratando grupo e item igual | **Composite** | Regras `AllOf`/`AnyOf`, `Specification.and/or`, árvore de categorias |
| Coordenar vários componentes sem que um conheça o outro | **Mediator** | Service orquestrador, orquestrador de saga |
| Nova operação sobre uma hierarquia fechada de tipos | **Visitor** → `switch` sobre `sealed` | Pattern matching exaustivo (Java 21+) |

### Os 23 do catálogo no Java 25 + Spring

| Grupo | Padrão | Situação | Onde |
|---|---|---|---|
| Criação | Abstract Factory | Spring faz | Uma `@Configuration` (ou perfil) por família de objetos relacionados |
| Criação | Factory Method | Spring faz | Métodos `@Bean`; métodos estáticos `of(...)`/`from(...)` |
| Criação | Builder | Usado | Builders das libraries; Test Data Builder (`test-patterns`) |
| Criação | Prototype | Raro | Cópia explícita; nunca `clone()` (seção 1) |
| Criação | Singleton | Spring faz | Escopo padrão dos beans, **sem estado mutável** (`concurrency`) |
| Estrutura | Adapter | Usado | Anti-corruption layer, adapters do hexagonal |
| Estrutura | Bridge | Raro | Duas dimensões que variam juntas (seção 2) |
| Estrutura | Composite | Usado | Regras combináveis, Specification (seção 2) |
| Estrutura | Decorator | Spring faz / usado | AOP; composição explícita para os seus |
| Estrutura | Facade | Usado | O service do pacote |
| Estrutura | Flyweight | Java faz | Enum, `BigDecimal.ZERO`, valores imutáveis compartilhados |
| Estrutura | Proxy | Spring faz | `@Transactional`, `@Cacheable`, lazy loading do JPA |
| Comportamento | Chain of Responsibility | Spring faz / usado | `SecurityFilterChain`, interceptors, lista de regras |
| Comportamento | Command | Usado | Seção 3 |
| Comportamento | Interpreter | Raro | Specification, SpEL controlado; evite linguagem própria (seção 3) |
| Comportamento | Iterator | Java faz | `Iterable`, `Stream`, `Slice`/`Window` do Spring Data |
| Comportamento | Mediator | Usado | Seção 3 |
| Comportamento | Memento | Raro | Snapshot do event sourcing, rascunho versionado (seção 3) |
| Comportamento | Observer | Spring faz | Eventos do Spring |
| Comportamento | State | Usado | Enum/sealed com transições |
| Comportamento | Strategy | Usado | Beans escolhidos por `supports` |
| Comportamento | Template Method | Spring faz | `JdbcTemplate`, `TransactionTemplate` (callbacks) |
| Comportamento | Visitor | Java faz | `switch` exaustivo sobre `sealed` (seção 3) |

---

## 1. Criacionais

### Factory
Quando a escolha da implementação depende de um dado de runtime (extensão do arquivo, header `Accept`, tipo de pagamento). No pacote: `FileImporterFactory`/`FileExporterFactory` (`file-import-export`).
- **O container do Spring já é uma factory.** Não escreva factory para criar objetos que podem ser beans — injete-os. A factory existe para **escolher entre beans** em runtime.
- Forma extensível: `List<Strategy>` injetada + `supports(...)` em cada estratégia (`solid`, seção O), ou um `Map<String, Strategy>` (o Spring injeta beans por nome).
- **Factory Method × Abstract Factory.** *Factory Method* é **um método** que decide qual objeto criar (cada método `@Bean` é um; `LoanStatus.fromCode(...)` também). *Abstract Factory* cria uma **família** de objetos que precisam combinar entre si: por parceiro de pagamento, o client, o mapper de erros e o validador de assinatura. No Spring, a família é uma `@Configuration` por parceiro (ou por perfil), e o código depende só das interfaces.

### Prototype
Criar um objeto copiando outro. Em Java, **não use `clone()`/`Cloneable`**: a cópia é rasa, não passa por construtor e o contrato é frágil. Use um **construtor ou método de cópia** explícito (`Loan.renewedCopy()`), métodos "with" em records (`period.withEnd(newEnd)`), ou o `but()` do Test Data Builder. **Nunca copie uma entity JPA** levando `id` e `@Version`: o `save` da cópia sobrescreve o original.

### Builder
Para objetos com muitos parâmetros, vários opcionais, ou que precisam ser válidos ao final da construção.
- Use os builders das libraries (`RestClient.builder()`, `ResponseEntity.ok()...`, `GroupedOpenApi.builder()`).
- **DTOs do pacote não usam builder** (são POJOs com getters/setters explícitos, sem Lombok — `code-organization`). Para dados imutáveis (eventos, respostas internas), um **record** resolve sem builder (`java-modern-features`).
- **Test Data Builder** nos testes (`test-patterns`) é o lugar onde o Builder mais compensa no dia a dia.

### Singleton
**Todo bean do Spring é singleton por padrão** — uma instância servindo todas as requisições, em várias threads ao mesmo tempo. Consequência: **beans não guardam estado de requisição em campos** (um campo `currentUser` num service é um bug de concorrência que vaza dados entre usuários). Estado por requisição vai em variável local, parâmetro ou no `SecurityContext`. Nunca escreva um Singleton "clássico" (`getInstance()` estático) para algo que pode ser bean: ele não é injetável nem substituível em teste.

---

## 2. Estruturais

### Adapter
Converte a interface de um sistema externo para o modelo do seu domínio, para que a mudança no parceiro fique em **um lugar**:
```java
@Component
public class CatalogClientAdapter implements BookCatalog {

    @Autowired
    private CatalogHttpClient client;

    @Override
    public Optional<BookInfo> findByIsbn(String isbn) {
        try {
            var response = client.getBook(isbn);
            return Optional.of(new BookInfo(response.isbn13(), response.fullTitle(), response.authorNames()));
        } catch (HttpClientErrorException.NotFound e) {
            return Optional.empty();
        }
    }
}
```
O resto da aplicação usa `BookCatalog` e `BookInfo` (seus nomes), nunca os DTOs nem os erros HTTP do parceiro. É a **anti-corruption layer** de `service-communication` e o **adapter** de `ddd-hexagonal`.

### Decorator e Proxy (AOP)
O Spring envolve seus beans em **proxies** para acrescentar comportamento: `@Transactional` abre/fecha a transação, `@Cacheable` consulta o cache (`caching`), `@Async` muda de thread (`email`), `@PreAuthorize` checa a permissão (`authentication`), `@Retryable`/Resilience4j repete (`resilience`).

**A armadilha nº 1 — auto-invocação:** o proxy só age em chamadas que **vêm de fora** do bean. `this.metodo()` dentro da mesma classe chama o objeto real e **pula** o proxy:
```java
@Service
public class LoanService {

    public void renewAll(List<Long> ids) {
        ids.forEach(this::renew);
    }

    @Transactional
    public void renew(Long id) { ... }
}
```
Aqui `renew` roda **sem transação** quando chamado por `renewAll`. Correções: anote o método de entrada (`renewAll`), mova `renew` para outro bean, ou desenhe a transação no nível certo. O mesmo vale para `@Cacheable`, `@Async` e `@PreAuthorize`. Proxies também não interceptam métodos `private` nem `final`.

Para um decorator **seu** (ex.: medir o tempo de um client), prefira compor explicitamente — uma classe que implementa a mesma interface e delega — a escrever um aspecto, a não ser que o comportamento atravesse muitos beans.

### Composite
Tratar **um item e um grupo de itens da mesma forma**, para montar árvores. O uso mais comum numa API é combinar regras:
```java
public interface RenewalRule {

    Optional<String> violation(Loan loan, Member member);
}

public record AllOf(List<RenewalRule> rules) implements RenewalRule {

    @Override
    public Optional<String> violation(Loan loan, Member member) {
        return rules.stream().map(rule -> rule.violation(loan, member)).flatMap(Optional::stream).findFirst();
    }
}

public record AnyOf(List<RenewalRule> rules) implements RenewalRule {

    @Override
    public Optional<String> violation(Loan loan, Member member) {
        var violations = rules.stream().map(rule -> rule.violation(loan, member)).toList();
        if (violations.stream().anyMatch(Optional::isEmpty)) return Optional.empty();
        return violations.stream().flatMap(Optional::stream).findFirst();
    }
}
```
`new AllOf(List.of(noPendingFines, new AnyOf(List.of(isStudent, isTeacher))))`: um grupo também é uma regra, então grupos se aninham sem que quem avalia saiba a forma da árvore. A `Specification` do Spring Data (`and`/`or`/`not`, seção 4) é um Composite. Para **árvore persistida** (categorias com subcategorias), cuidado com a leitura recursiva: carregue a árvore inteira de uma vez (CTE recursiva ou caminho materializado — `data-modeling`), nunca filho por filho.

### Bridge e Flyweight
- **Bridge**: separar **duas dimensões que variam de forma independente**, para não criar uma classe por combinação. Notificação tem o *tipo* (lembrete de devolução, multa, reserva disponível) e o *canal* (e-mail, SMS, push): o tipo monta o conteúdo e delega o envio a um `NotificationChannel`. Três tipos × três canais = seis classes, não nove. Raro; só quando as duas dimensões crescem de fato.
- **Flyweight**: compartilhar instâncias imutáveis em vez de criar cópias iguais. O Java já faz (enum, `Integer.valueOf` em faixa pequena, `BigDecimal.ZERO`, `Locale`); para um value object imutável muito repetido, uma constante basta. Não confunda com cache de dados (`caching`).

### Facade
O service do pacote é uma facade: o controller chama `bookService.create(dto)` sem saber de repository, mapper, eventos e validações. Mantenha a facade **fina** — orquestração, não a regra inteira escondida num método de 200 linhas (`solid`, seção S).

---

## 3. Comportamentais

### Strategy
Um algoritmo intercambiável atrás de uma interface — o padrão mais útil do dia a dia:
```java
public interface LateFeePolicy {

    boolean appliesTo(Member member);

    BigDecimal calculate(Loan loan, LocalDate returnDate);
}
```
Uma implementação por regra (`StandardLateFeePolicy`, `StudentLateFeePolicy`), todas `@Component`, escolhidas por `appliesTo`. Nova regra = nova classe (`solid`, seção O). **Não use** para duas variações que nunca vão crescer: um `if` é mais claro.

### Template Method
Um esqueleto fixo com passos que variam. No Spring, aparece "invertido" como **callback**: `JdbcTemplate`, `TransactionTemplate` e `RestClient` controlam abrir/fechar/tratar erro e você passa só o passo variável (um lambda). Nos testes, `AbstractIntegrationTest` (`integration-testing`) é um template: a base sobe o container e configura o client; cada teste escreve só o cenário. Prefira **callbacks/composição** a hierarquias de herança profundas.

### Observer (eventos)
Avisar outras partes do sistema sem acoplá-las ao produtor:
```java
publisher.publishEvent(new BookCreatedEvent(saved.getId()));
```
```java
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void on(BookCreatedEvent event) { ... }
```
- `@EventListener` roda **na mesma thread e na mesma transação**: uma exceção no listener desfaz o produtor. `@TransactionalEventListener(AFTER_COMMIT)` roda só se o commit aconteceu — o certo para efeitos externos (e-mail, mensagens — `email`).
- Eventos em memória **se perdem** se a aplicação cair. Para outros serviços ou entrega garantida, use **outbox** (`transactional-outbox`) e um broker (`messaging`). Entre módulos de um monolito modular, o Spring Modulith persiste os eventos (`modular-monolith`).
- Eventos são records imutáveis, com ids — não a entity inteira.

### Chain of Responsibility
Cada elo decide tratar, passar adiante ou interromper: a `SecurityFilterChain` (o `JwtTokenFilter` de `authentication` é um elo), os `HandlerInterceptor` do MVC e os filtros do Spring Cloud Gateway (`api-gateway`). Para validações de negócio em sequência ("o sócio está ativo? o livro está disponível? o limite foi atingido?"), uma lista de regras (`List<RenewalRule>`) avaliada em ordem é uma chain simples e testável.

### State
Quando o que se pode fazer depende do estado (`ACTIVE`, `RENEWED`, `OVERDUE`, `RETURNED`), centralize as **transições permitidas** em vez de espalhar `if (status == ...)`:
```java
public enum LoanStatus {
    ACTIVE, RENEWED, OVERDUE, RETURNED;

    public boolean canRenew() {
        return this == ACTIVE || this == RENEWED;
    }
}
```
Com comportamento por estado mais rico, um **sealed interface** com um record por estado e `switch` exaustivo deixa o compilador apontar o caso esquecido (`java-modern-features`). Persistido como `@Enumerated(EnumType.STRING)` (`spring-data-jpa`). Transições também são boas candidatas a links condicionais (`hateoas`).

### Command
Transformar **uma operação em objeto**, para que ela possa ser enfileirada, registrada, repetida, agendada ou desfeita. No Java atual, o comando é um **record** (os dados do pedido) e quem o executa é um **handler**:
```java
public sealed interface LoanCommand permits RenewLoan, ReturnLoan {

    Long loanId();
}

public record RenewLoan(Long loanId, Long memberId) implements LoanCommand {}

public record ReturnLoan(Long loanId, LocalDate returnedOn) implements LoanCommand {}
```
```java
@Service
public class LoanCommandHandler {

    @Autowired
    private LoanService service;

    public LoanDTO handle(LoanCommand command) {
        return switch (command) {
            case RenewLoan renew -> service.renew(renew.loanId(), renew.memberId());
            case ReturnLoan returned -> service.returnBook(returned.loanId(), returned.returnedOn());
        };
    }
}
```
Vale quando a operação precisa **viajar ou ficar guardada**: entrar numa fila (o comando vira mensagem — `messaging`), ser registrada para auditoria, ser repetida com `Idempotency-Key` (`idempotency`), agendada, ou separar escrita de leitura (`cqrs-event-sourcing`). Todo `Runnable`/`Callable` submetido a um executor já é um Command (`concurrency`). **Não vale** para chamar um service do controller: um "barramento de comandos" genérico entre controller e service só acrescenta indireção e esconde quem trata o quê.

### Mediator
Um objeto que **coordena a conversa** entre componentes, para que eles não se conheçam. O service do pacote que chama `catalog`, `lending` e `billing` em ordem é um mediador; o orquestrador de saga (`saga-pattern`) é um mediador entre serviços. Diferença para o Observer: o mediador **conhece e comanda** os participantes; no Observer, o produtor não sabe quem reage. Cuidado com o mediador que absorve as regras de todos e vira God Service (`refactoring`): ele coordena, a regra fica com o dono do dado (`solid`, coesão).

### Visitor → `switch` sobre `sealed`
O Visitor do catálogo acrescenta **operações novas a uma hierarquia fechada** sem editar as classes, ao custo de `accept`/`visit` em todo tipo. No Java 21+, um `sealed interface` com `switch` exaustivo dá o mesmo benefício sem a cerimônia, e o compilador aponta cada `switch` que esqueceu um tipo novo:
```java
public sealed interface LibraryItem permits PrintedBook, EBook, Magazine {}

public BigDecimal dailyFee(LibraryItem item) {
    return switch (item) {
        case PrintedBook book -> new BigDecimal("2.00");
        case EBook ebook -> BigDecimal.ZERO;
        case Magazine magazine -> new BigDecimal("0.50");
    };
}
```
**Hierarquia estável e operações que crescem** (multa, exportação, validação por tipo): `switch` sobre `sealed`. **Tipos que crescem e operações estáveis**: método polimórfico em cada tipo (ou Strategy). Não escreva Visitor manual em Java 25. Em **entity JPA**, `sealed` atrapalha os proxies do Hibernate: use em records e tipos de domínio (`jpa-advanced-mapping`).

### Iterator, Memento e Interpreter
- **Iterator**: o Java já tem (`Iterable`, `Stream`). O que importa numa API é **não carregar tudo**: percorra volumes grandes com `Slice`/`Window` (keyset — `pagination`) ou `Stream<T>` do repository dentro de uma transação, nunca `findAll()` numa lista.
- **Memento**: guardar o estado de um objeto para restaurá-lo depois sem expor o interior. Aparece como **snapshot** no event sourcing (`cqrs-event-sourcing`), rascunho versionado ou "desfazer". Histórico de alterações é outra coisa (auditoria — `jpa-advanced-mapping`).
- **Interpreter**: uma gramática representada por objetos. Para filtros, `Specification` resolve; para regras configuráveis, um motor de regras existente. **Nunca avalie expressão vinda do usuário com SpEL** num `StandardEvaluationContext` (execução de código — `application-security`); se precisar, `SimpleEvaluationContext` e lista do que é permitido. Evite inventar uma linguagem própria.

---

## 4. Padrões corporativos que o pacote usa

| Padrão | Para quê | Skill |
|---|---|---|
| **Repository** | Acesso a dados atrás de uma interface de coleção | `spring-data-jpa` |
| **DTO** | Contrato da API separado do modelo persistido | `code-organization` |
| **Specification** | Filtros dinâmicos combináveis (`Specification<Book>` + `JpaSpecificationExecutor`), em vez de dezenas de métodos `findByXAndYAndZ` | `spring-data-jpa` |
| **Unit of Work** | A transação JPA (persistence context) agrupa as mudanças até o commit | `spring-data-jpa` |
| **Anti-corruption layer / Adapter** | Proteger o domínio de modelos externos | `service-communication`, `ddd-hexagonal` |
| **Transactional Outbox** | Publicar evento junto com a mudança no banco | `transactional-outbox` |
| **Saga** | Transação de negócio entre serviços | `saga-pattern` |
| **CQRS** | Modelos de leitura e escrita separados | `cqrs-event-sourcing` |
| **Circuit Breaker, Retry, Bulkhead** | Falhas parciais | `resilience` |
| **Idempotency Key** | Repetição sem efeito duplicado | `idempotency` |
| **API Gateway / BFF** | Borda única para os clients | `api-gateway` |
| **Strangler Fig** | Migração incremental | `refactoring`, `microservices` |

Specification, em resumo:
```java
public final class BookSpecifications {

    private BookSpecifications() {}

    public static Specification<Book> titleContains(String title) {
        return (root, query, cb) -> title == null ? null
            : cb.like(cb.lower(root.get("title")), "%" + title.toLowerCase(Locale.ROOT) + "%");
    }

    public static Specification<Book> publishedAfter(LocalDate date) {
        return (root, query, cb) -> date == null ? null : cb.greaterThan(root.get("launchDate"), date);
    }
}
```
`repository.findAll(titleContains(title).and(publishedAfter(date)), pageable)` — o critério é montado com a Criteria API (parâmetros, sem concatenação de SQL) e continua paginado (`pagination`). Filtros `null` são ignorados.

---

## 5. Anti-padrões

- **Padrão sem problema:** factory para uma implementação, strategy para dois casos fixos, interface + `Impl` para tudo (`solid`, D).
- **God Service / God Object:** uma classe que sabe tudo (`refactoring`).
- **Service Locator:** buscar beans no `ApplicationContext` espalhado pelo código esconde as dependências — restrinja ao **ponto de escolha** de uma factory.
- **Singleton com estado:** campo mutável em bean (vaza dados entre requisições).
- **Herança para reaproveitar código:** `BaseService<T>`, `BaseEntity` genéricos que acoplam tudo (o pacote não usa `BaseEntity` — `spring-data-jpa`).
- **Modelo anêmico** num domínio rico (todas as regras no service, entidade só com getters/setters) — aceitável em CRUD, um problema em domínio complexo (`ddd-hexagonal`).
- **Proxy ignorado:** `@Transactional`/`@Cacheable` em método chamado por `this`, `private` ou `final`.
- **`clone()`/`Cloneable`**, e cópia de entity levando `id`/`@Version`.
- **Cadeia de `instanceof`** ou `if (type == ...)` repetida, onde um `switch` exaustivo sobre `sealed` (ou polimorfismo) avisaria o caso esquecido; **Visitor manual** em Java 25.
- **Barramento de comandos genérico** entre controller e service, sem fila, auditoria ou repetição que o justifique.
- **Mediador que absorve as regras** de todos os participantes.

---

## 6. Testando os padrões

- **Strategy:** um teste por implementação, mais um teste da escolha (factory/registry) com todas as estratégias; teste de contrato comum quando houver muitas (`solid`, L).
- **Adapter:** WireMock simulando o parceiro, incluindo erros e respostas estranhas (`service-communication`).
- **Observer:** o produtor publica o evento (verifique com `@RecordApplicationEvents`/`ApplicationEvents` no teste do Spring); o listener testado isoladamente; o caso de rollback (nenhum efeito).
- **Proxy:** um teste de integração que prova que a transação/cache **de fato** acontece — um teste unitário com o objeto real não passa pelo proxy.
- **State:** uma tabela de transições (`@ParameterizedTest`) com as permitidas e as proibidas.
- **Composite:** cada regra folha isolada; os grupos com dublês simples (uma regra que sempre passa, uma que sempre falha) para provar `AllOf` e `AnyOf`, inclusive aninhados e vazios.
- **Command:** o handler com um caso por tipo de comando; o comando serializado e lido de volta quando viaja por fila.

---

## Regras principais

- Comece pelo problema, nunca pelo padrão; sem problema recorrente real, prefira o código direto.
- Reconheça o que o Spring já faz: container (factory/singleton), proxies (decorator), eventos (observer), filtros (chain), templates/callbacks.
- Beans são singletons compartilhados entre threads: **sem estado mutável de requisição em campos**.
- Proxies não agem em auto-invocação (`this.metodo()`), em métodos `private` ou `final` — desenhe a fronteira transacional sabendo disso.
- Strategy (interface + implementações como beans, escolhidas por `supports`) para variações que crescem; `if`/`switch` exaustivo para poucas variações fixas.
- Adapter/anti-corruption layer para todo sistema externo; o domínio usa os próprios nomes.
- Eventos: `AFTER_COMMIT` para efeitos externos; outbox quando não podem se perder; records com ids.
- State com enum/sealed e transições explícitas; Specification para filtros dinâmicos paginados.
- **Princípios antes dos padrões**: programe para a interface (sem `Impl` por reflexo), composição antes de herança, encapsule o que varia; use as **causas de reprojeto** para diagnosticar.
- **Command** quando a operação precisa viajar ou ficar guardada; **Composite** para regras combináveis; **Mediator** coordena sem absorver regra; **Visitor** vira `switch` sobre `sealed`; Iterator e Flyweight o Java já resolve; Prototype por cópia explícita, nunca `clone()`.
- Evite Service Locator, herança para reaproveitar código, `BaseService`/`BaseEntity` genéricos e interface + `Impl` sem necessidade.
- Teste cada estratégia, a escolha entre elas, os adapters contra um servidor simulado e os proxies em teste de integração.
- **Sem Lombok** — deliberado.

## Referências

- Erich Gamma, Richard Helm, Ralph Johnson e John Vlissides, *Padrões de Projeto: soluções reutilizáveis de software orientado a objetos* (Bookman; original *Design Patterns*, Addison-Wesley, 1994): princípios do cap. 1, causas de reprojeto e o catálogo dos 23 padrões. Reescritos para Java 25 e Spring, com os exemplos do pacote.
