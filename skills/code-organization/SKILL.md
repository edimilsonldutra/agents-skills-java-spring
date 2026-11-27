---
name: code-organization
description: Fundação do pacote — faz uma única vez o questionário de preferências do projeto (comentários, database, Swagger, build tool, mapper, injection) e define o layout flat-by-layer sob br.com.edimilsonldutra (com o trade-off e quando migrar para módulos), naming, Startup, patterns de entity/DTO/controller/service/exception e o application.yml. Use antes de gerar código em qualquer projeto Spring Boot deste padrão ou quando perguntarem onde algo deve ficar.
---

# Estrutura de Aplicação Spring Boot

Organização flat-by-layer: controllers, services, repositories, model, DTOs e config vivem em packages dedicados sob `br.com.edimilsonldutra`. Não é domain-driven. Java e Spring Boot evoluem rápido — sempre resolva as últimas versões estáveis no momento da criação do projeto (veja a skill `maven-config`) e nunca copie versões de outro projeto.

Toda outra skill desta família assume que esta skill e `code-style` foram lidas primeiro.

Ainda não tem projeto? Comece com `scaffold`: ele pergunta a versão do Java, build tool, config file e quais building blocks opcionais incluir (persistence, Flyway, exception handling, web config, Swagger, Bean Validation — cada um um decorator independente, ligado por default), cria o projeto e executa as partes aplicáveis deste Step 0 junto com eles.

---

## Step 0 — Preferências do projeto (pergunte uma vez, lembre)

Execute isto antes de gerar qualquer código com qualquer skill desta família.

1. **Procure respostas salvas.** Busque no `CLAUDE.md` do projeto uma seção intitulada `## Project preferences`, e nesta conversa respostas já dadas. Se existirem, use-as silenciosamente e pule para os patterns abaixo.
2. **Caso contrário, pergunte, uma vez, tudo de uma vez** (use a tool `AskUserQuestion` quando disponível — duas chamadas de até quatro perguntas — ou uma única mensagem simples). Cada pergunta tem um default; aceite "just use the defaults" como uma resposta válida.

| Preferência | Opções (default primeiro) | O que muda |
|---|---|---|
| Comments in generated code | **No** / Yes | Nenhum comentário em Java, XML, YAML, SQL ou Dockerfiles, a menos que o desenvolvedor peça; as explicações vão na resposta do chat, não no código. |
| Database | **MySQL** / PostgreSQL / SQL Server / Oracle / MariaDB | Os cinco databases suportados. Muda o JDBC driver, o módulo de database do Flyway, o módulo do Testcontainers, a imagem Docker e o healthcheck, a JDBC URL e a sintaxe SQL das migrations (`flyway-migrations`, `maven-config` e `docker-and-docker-compose` carregam as tabelas por database). MySQL é o default e o caminho validado de ponta a ponta. Para um database fora desses cinco, mantenha a arquitetura, resolva os artifacts equivalentes a partir da documentação atual, e diga ao desenvolvedor que aquele database não é coberto. **Perguntado no `scaffold` somente quando seu decorator de Persistence é escolhido** — caso contrário, perguntado lazily, na primeira vez que uma skill que precisa dele roda (por exemplo `spring-data-jpa` aberta em um projeto existente). |
| Swagger/OpenAPI annotations | **Separate `*ControllerDocs` interface** / directly on the controller | Onde vivem todo `@Operation`, `@ApiResponse` e `@Parameter` (veja `swagger`). **Diga o trade-off ao perguntar:** com a interface, as annotations de Bean Validation em parâmetros (`@Valid`, `@Min`, `@NotBlank`…) **não** podem ser escritas no método do controller — precisam ir também no método da interface, senão o controller inteiro falha com um 500 (veja `bean-validation`); com as annotations direto no controller, a validation fica no controller e não há essa restrição. **Perguntado no `scaffold` somente quando seu decorator de Swagger é escolhido** — caso contrário, perguntado lazily pelo próprio `swagger`. |
| Build tool | **Maven** / Gradle | Ambos são suportados. O `scaffold` gera qualquer um (Gradle em Groovy ou Kotlin DSL) e o `maven-config` mapeia toda dependency, plugin e comando de Maven para Gradle; Maven é o default e o caminho mais usado nos exemplos das skills. |
| Java version | **Latest LTS** | Escolhido no `scaffold`: qualquer release LTS a partir da 17, ou outro número depois de um aviso de que uma release não-LTS não é adequada para produção. Em um projeto existente é o `java.version` / toolchain do build file. |
| Configuration file | **YAML** / properties | `application.yml` (default) ou `application.properties`, escolhido no `scaffold`. Com properties, todo bloco YAML destas skills é escrito como chaves flat com pontos. |
| User-facing text language | **English** (igual aos identifiers) / idioma do desenvolvedor | Identifiers de código (packages, classes, campos, métodos) são sempre em inglês; somente o texto que um client de fato lê — mensagens de Bean Validation (veja `bean-validation`), mensagens de exception (veja `exception-handling`), summaries/descriptions do Swagger (veja `swagger`) — segue esta resposta. Escolhido no `scaffold`. |
| Entity ↔ DTO mapping | **MapStruct** / Dozer | O package `mapper` e toda conversão de service (veja `spring-data-jpa` e `maven-config`). **MapStruct** gera código de getter/setter em tempo de compilação (zero reflexão, sem Jackson 2 transitivo, compatível com records e AOT); `Dozer` fica como opção apenas para projetos legados. **Perguntado no `scaffold` somente quando seu decorator de Persistence é escolhido.** |
| Dependency injection | **Constructor** / field `@Autowired` | Controllers, services e componentes usam campos `private final` + construtor explícito (sem `@Autowired` quando há construtor único e sem Lombok); os unit tests funcionam tanto instanciando direto pelo construtor quanto com `@InjectMocks` (`testing`), e classes de teste JUnit do Spring (`@WebMvcTest`, `@DataJpaTest`, `@SpringBootTest`) continuam usando `@Autowired` nos campos de teste. |

**Lombok nunca é usado e não é uma opção.** Entities e DTOs sempre têm constructors, getters, setters, `equals()` e `hashCode()` explícitos.

3. **Ofereça salvar.** Depois das respostas, pergunte se deve registrá-las no `CLAUDE.md` do projeto (só escreva se o desenvolvedor concordar) para que sessões futuras não perguntem de novo:

```markdown
## Project preferences
- Base package: br.com.edimilsonldutra
- Comments in generated code: no
- Database: MySQL
- Swagger annotations: *ControllerDocs interface
- Build tool: Maven
- Java version: 25 (LTS)
- Configuration file: YAML
- User-facing text language: English
- Entity/DTO mapping: MapStruct
- Dependency injection: constructor
- Model profile: auto
```

Sempre que uma skill posterior precisar de uma preferência que ainda é desconhecida (por exemplo `swagger` aberta primeiro), pergunte somente essa pergunta e adicione-a à seção salva.

---

## Package Structure

```
br.com.edimilsonldutra/
├── Startup.java                            # @SpringBootApplication entrypoint
├── config/                                 # Global configuration
│   ├── OpenApiConfig.java
│   ├── WebConfig.java                      # CORS, content negotiation
│   ├── JacksonConfig.java                  # YAML converter (see web-config)
│   └── SecurityConfig.java
├── controllers/                            # @RestController — HTTP layer
│   ├── docs/                               # Swagger interface contracts
│   │   └── BookControllerDocs.java
│   └── BookController.java
├── services/                               # @Service — business logic
│   └── BookService.java
├── repository/                             # Spring Data JPA interfaces
│   └── BookRepository.java
├── model/                                  # @Entity — JPA entities
│   ├── Book.java
│   ├── User.java
│   └── Permission.java
├── data/
│   └── dto/                                # Transfer objects
│       ├── BookDTO.java
│       ├── request/                        # Request-only payloads
│       └── security/
│           ├── AccountCredentialsDTO.java
│           └── TokenDTO.java
├── exception/                              # Domain exceptions + global handler
│   ├── ExceptionResponse.java
│   ├── ResourceNotFoundException.java
│   ├── RequiredObjectIsNullException.java
│   ├── BadRequestException.java
│   └── handler/
│       └── CustomEntityResponseHandler.java
├── security/
│   └── jwt/
│       ├── JwtTokenProvider.java
│       └── JwtTokenFilter.java
├── file/                                   # File import/export (when needed)
│   ├── exporter/{contract,factory,impl}/
│   └── importer/{contract,factory,impl}/
├── mail/                                   # E-mail sending (when needed)
├── messaging/                              # Brokers: event/, publisher/, listener/, config/ (see messaging)
└── mapper/
    └── BookMapper.java                     # MapStruct interface (@Mapper(componentModel = "spring"))
```

Crie somente os packages de que uma feature precisa; um primeiro CRUD tem `controllers`, `services`, `repository`, `model`, `data/dto`, `exception`, `config`, `mapper`.

### Por que flat-by-layer, e quando deixar de ser

Há quatro formas clássicas de empacotar: **por camada** (este layout), **por recurso** (`book/` com controller, service e repository juntos), **portas e adaptadores** (`ddd-hexagonal`) e **por componente** (um package por capacidade, com a API pública no topo e os internos escondidos — `modular-monolith`). O flat-by-layer é a escolha do pacote para **um serviço com um domínio e pouca regra**: é o layout que todo dev Spring reconhece e o mais barato de gerar. O preço é conhecido:
- **A estrutura não "grita" o domínio**: olhando os packages se vê `controllers/services/repository`, não `lending/catalog/billing`. Com um domínio, tudo bem; com vários, o `services/` vira um saco de 40 classes de 6 assuntos.
- **Tudo é `public`**, porque uma camada precisa enxergar a outra em outro package. Nada impede o controller de chamar o repository direto, pulando o service: a regra "controller → service → repository" só se mantém por revisão (`code-reviewer`) ou por um teste de **ArchUnit** (`ddd-hexagonal`, seção 4).
- **Uma feature espalha-se por 5 a 7 packages**, e um PR pequeno toca todos.

Sinais de que é hora de mudar: **mais de um domínio** no mesmo serviço, times diferentes mexendo em partes diferentes, ou o mesmo service crescendo por motivos de negócio distintos. A migração recomendada é para **módulos por capacidade** (`modular-monolith`), com o flat-by-layer reduzido **dentro** de cada módulo; hexagonal só onde o domínio for rico (`ddd-hexagonal`). Registre a mudança em ADR.

---

## Naming Conventions

| Tipo              | Convenção         | Exemplo                            |
|-------------------|-------------------|------------------------------------|
| Entrypoint        | `Startup`         | `Startup.java`                     |
| JPA Entity        | Nome do domínio   | `Book`, `Person`, `User`           |
| DTO               | `*DTO`            | `BookDTO`, `AccountCredentialsDTO` |
| Controller        | `*Controller`     | `BookController`, `AuthController` |
| Controller Docs   | `*ControllerDocs` | `BookControllerDocs`               |
| Service           | `*Service`        | `BookService`, `AuthService`       |
| Repository        | `*Repository`     | `BookRepository`, `UserRepository` |
| Exception         | `*Exception`      | `ResourceNotFoundException`        |
| Exporter/Importer | `*Exporter`/`*Importer` | `XlsxExporter`, `CsvImporter` |
| Test-only pagination wrappers | `Wrapper*DTO`, `PagedModel*` | `WrapperBookDTO` (vivem em `src/test`) |

---

## Code Patterns

### Startup.java
```java
@SpringBootApplication
public class Startup {

    public static void main(String[] args) {
        SpringApplication.run(Startup.class, args);
    }
}
```
A `Startup` e as classes de `config/` são o **componente Main** da aplicação: o lugar mais "sujo", que conhece todas as implementações concretas e as liga (beans, properties, perfis). Nenhuma regra de negócio depende dele, e é por isso que ele pode depender de tudo. Regra de negócio dentro de `@Configuration` ou de um `@Bean` é achado de revisão.

### Entity
Sem Lombok. Constructor sem argumentos explícito. `equals()`/`hashCode()` via `Objects`, usando getters, sobre todos os campos. Sempre `implements Serializable` com `serialVersionUID = 1L`. Constraints de coluna declaradas com `@Column`. Datas sem parte de horário usam `java.time.LocalDate` (nunca `java.util.Date` + `@Temporal`, que o Hibernate 7 depreca). Veja `spring-data-jpa` para relationships, fetch types e repositories.
```java
@Entity
@Table(name = "books")
public class Book implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 250)
    private String title;

    @Column(name = "launch_date", nullable = false)
    private LocalDate launchDate;

    public Book() {}

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public LocalDate getLaunchDate() {
        return launchDate;
    }

    public void setLaunchDate(LocalDate launchDate) {
        this.launchDate = launchDate;
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        Book book = (Book) o;
        return Objects.equals(getId(), book.getId()) && Objects.equals(getTitle(), book.getTitle()) && Objects.equals(getLaunchDate(), book.getLaunchDate());
    }

    @Override
    public int hashCode() {
        return Objects.hash(getId(), getTitle(), getLaunchDate());
    }
}
```

### DTO
Mesma estrutura da entity, sem annotations JPA. Entities nunca são expostas pelos controllers. Se o projeto usa HATEOAS, o DTO também estende `RepresentationModel<T>` e carrega `@Relation(collectionRelation = "books")` (skill `hateoas`). Sem `@XmlRootElement` em DTOs de produção — o Jackson 3 escreve XML a partir do nome da classe e dos nomes das properties sem annotations JAXB (veja `web-config`).
```java
public class BookDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String title;
    private LocalDate launchDate;

    public BookDTO() {}

    // getters, setters, equals, hashCode — same shape as the entity
}
```

### Controller
O CRUD abaixo é o ponto de partida para dado simples. Recurso com regra, ciclo de vida ou consumidor externo: desenhe antes com `api-design` (papel do endpoint, transição de estado como ação, `If-Match`).

Constructor injection explícita por default (`private final` + construtor sem `@Autowired`, pois há um único construtor). Implementa `*ControllerDocs` quando a preferência de Swagger é a interface. Retorna `ResponseEntity<>` quando é preciso controlar o status HTTP, o DTO diretamente caso contrário. Os endpoints declaram os media types escolhidos pelo projeto — JSON sempre, XML/YAML somente quando o projeto os pediu (veja `web-config`). Validations rápidas de input vivem em métodos privados.
```java
@RestController
@RequestMapping("/api/book/v1")
public class BookController implements BookControllerDocs {

    private final BookService service;

    public BookController(BookService service) {
        this.service = service;
    }

    @GetMapping(value = "/{id}", produces = {
        MediaType.APPLICATION_JSON_VALUE,
        MediaType.APPLICATION_XML_VALUE,
        MediaType.APPLICATION_YAML_VALUE})
    @Override
    public BookDTO findById(@PathVariable("id") Long id) {
        return service.findById(id);
    }

    @PostMapping(
        consumes = {
            MediaType.APPLICATION_JSON_VALUE,
            MediaType.APPLICATION_XML_VALUE,
            MediaType.APPLICATION_YAML_VALUE},
        produces = {
            MediaType.APPLICATION_JSON_VALUE,
            MediaType.APPLICATION_XML_VALUE,
            MediaType.APPLICATION_YAML_VALUE})
    @Override
    public BookDTO create(@RequestBody BookDTO book) {
        return service.create(book);
    }

    @DeleteMapping("/{id}")
    @Override
    public ResponseEntity<?> delete(@PathVariable("id") Long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
```
Os `produces`/`consumes` acima assumem que JSON + XML + YAML foram todos escolhidos; use somente `MediaType.APPLICATION_JSON_VALUE` quando o projeto é somente JSON.

Com a preferência de **field injection** (`field` no Step 0, comum em projetos legados), substitua o campo `final` e o construtor por `@Autowired private BookService service;`; o resto não muda.

### Controller Docs interface
Com a preferência default, todas as annotations de Swagger/OpenAPI vivem aqui e o controller fica limpo (`@Tag` vai na classe do controller). Com a preferência "directly on the controller", coloque as mesmas annotations nos métodos do controller e pule a interface. Veja `swagger`.
```java
public interface BookControllerDocs {

    @Operation(summary = "Finds a Book", tags = {"Book"},
        responses = {
            @ApiResponse(description = "Success", responseCode = "200",
                content = @Content(schema = @Schema(implementation = BookDTO.class))),
            @ApiResponse(description = "Not Found", responseCode = "404", content = @Content),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    BookDTO findById(@PathVariable("id") Long id);
}
```

### Service
Logger SLF4J, `private static final`. A conversão Entity ↔ DTO passa pela interface MapStruct do package `mapper` injetada no construtor (`BookMapper`). Lança domain exceptions diretamente no corpo do método. Escritas com `@Transactional`, leituras com `@Transactional(readOnly = true)` (veja `spring-data-jpa`). Com a preferência legada Dozer, use o wrapper estático `ObjectMapper.parseObject` no lugar.
```java
@Service
public class BookService {

    private static final Logger logger = LoggerFactory.getLogger(BookService.class);

    private final BookRepository repository;
    private final BookMapper mapper;

    public BookService(BookRepository repository, BookMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    @Transactional(readOnly = true)
    public BookDTO findById(Long id) {
        logger.info("Finding one book!");
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        return mapper.toDto(entity);
    }

    @Transactional
    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        logger.info("Creating one book!");
        var entity = mapper.toEntity(book);
        return mapper.toDto(repository.save(entity));
    }
}
```

### Mapper (preferência default MapStruct)
```java
@Mapper(componentModel = "spring")
public interface BookMapper {

    BookDTO toDto(Book entity);

    Book toEntity(BookDTO dto);

    List<BookDTO> toDtoList(List<Book> entities);
}
```
Com a preferência legada **Dozer**, usa-se um wrapper estático `mapper/ObjectMapper` (`DozerBeanMapperBuilder.buildDefault()`) com `parseObject` e `parseListObjects` (detalhes em `spring-data-jpa`).

### Exception
Toda exception declara `serialVersionUID`. Veja `exception-handling` para o conjunto completo e o handler global.
```java
@ResponseStatus(HttpStatus.NOT_FOUND)
public class ResourceNotFoundException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public ResourceNotFoundException(String message) {
        super(message);
    }
}
```

---

## Configuration — application.yml

Use YAML (`application.yml`, nunca `.yaml`) a menos que as preferências digam `properties` (escolhido no `scaffold`): então escreva as mesmas chaves como chaves flat com pontos em `application.properties`. Os blocos abaixo são mostrados em YAML. Abaixo está a base com que todo projeto começa; outras skills adicionam seus próprios blocos (JWT, e-mail, file upload) quando a feature é introduzida.

### Main (`src/main/resources/application.yml`)
```yaml
cors:
  originPatterns: http://localhost:8080,http://localhost:3000

spring:
  application:
    name: my-app
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://localhost:3306/my_db?useTimezone=true&serverTimezone=UTC
    username: root
    password: ${DB_PASSWORD:admin123}
  jpa:
    hibernate:
      ddl-auto: none
    properties:
      hibernate:
        check_nullability: true
    show-sql: false
    open-in-view: false

logging:
  level:
    root: INFO

springdoc:
  api-docs:
    enabled: true
  paths-to-match:
    - /auth/**
    - /api/**/v1/**
  swagger-ui:
    enabled: true
```
O driver, a URL e as flags `useTimezone`/`serverTimezone` são específicos do MySQL — substitua pelos equivalentes do database escolhido no Step 0.

### Test (`src/test/resources/application.yml`)
**Uma cópia completa do arquivo principal, não um overlay.** Um arquivo com o mesmo nome em `src/test/resources` faz shadowing do principal no classpath de teste, então qualquer coisa que falte nele (chaves JWT, CORS, mail, springdoc, `check_nullability`) falta nos testes. Copie o arquivo principal inteiro, depois mude somente o que difere:
- remova `datasource.url`, `username` e `password` — o initializer do Testcontainers os injeta em runtime;
- prefira `RANDOM_PORT` nos testes de integração (`integration-testing`, evita conflito de porta no CI); adicione `server.port: 8888` somente se uma suíte legada depender de porta fixa;
- aponte qualquer diretório de upload para `target/` (Gradle: `build/`), por exemplo `file.upload-dir: target/test-uploads`.

Toda mudança posterior em uma setting compartilhada precisa ser feita nos dois arquivos.

### Convenções principais
- Valores sensíveis usam variáveis de ambiente: `${ENV_VAR:defaultValue}`; nunca commite secrets reais.
- `ddl-auto: none` sempre — schema gerenciado exclusivamente pelo Flyway (veja `flyway-migrations`).
- `check_nullability: true` sempre — veja `spring-data-jpa` para saber por que é obrigatório com o Hibernate 7.
- `show-sql: false` em todos os ambientes; habilite temporariamente via logging levels se necessário.
- `open-in-view: false` sempre.
- `springdoc` (não `spring-doc`) é a chave top-level correta; uma chave errada é ignorada silenciosamente.
- Nomes de properties são escritos exatamente como o Spring/seu código os faz bind (`expire-length`, não um erro de grafia) — um typo em uma chave não quebra o build, quebra em runtime.

---

## Onde vive o resto

Cada tópico tem a sua skill (persistence, migrations, erros, web config, Swagger, validation, segurança, testes, mensageria, microsserviços, Docker/Kubernetes, AWS e produto). Para o mapa completo de "qual skill para qual necessidade", use a skill `guide` — não repita o mapa aqui. Toda skill desta família segue este layout e as preferências do Step 0.

## Referências

- Robert C. Martin, *Arquitetura Limpa: o guia do artesão para estrutura e design de software* (Alta Books, 2019), caps. 21 (arquitetura gritante), 26 (o componente Main) e 34 (pacote por camada, por recurso, portas e adaptadores e por componente). As ideias foram reescritas para o layout do pacote.
