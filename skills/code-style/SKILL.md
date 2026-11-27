---
name: code-style
description: Estilo de código Java do pacote — código que comunica (valores e princípios, nomes que revelam intenção, método composto), coleções (interface pela semântica, vazia em vez de null, imutáveis, cópia de segurança), comentários (default nenhum), var, guard clauses, quebras de linha, annotations, equals/hashCode, logger SLF4J, idioms modernos, Jackson 3 e chains do REST Assured, sem Lombok. Use ao gerar ou revisar código Java deste padrão ou quando pedirem para ajustar o estilo de uma classe.
---

# Java Code Style

Baixa cerimônia, explícito, legível. Sem Lombok. Sem mágica. A indentação é de 4 espaços, nunca tabs.

Leia `code-organization` primeiro: o **Step 0** dela coleta as preferências do projeto (comentários, database, posição do Swagger, build tool, mapper, injection). Se esta skill for a primeira aberta na conversa e não existir uma seção `## Project preferences` no `CLAUDE.md` do projeto, execute esse Step 0 agora — no mínimo a pergunta de comentários abaixo.

---

## Código que comunica

Código é lido muito mais vezes do que escrito; o leitor é o próximo dev (ou você daqui a seis meses). Quando duas formas de escrever funcionam igual, os **valores** desempatam, nesta ordem: **comunicação** (o leitor entende a intenção), **simplicidade** (nada que não precise estar ali) e **flexibilidade** (só a que o código vai realmente usar). Os princípios que derivam deles:
- **Consequências locais**: uma mudança deve afetar pouco código, perto de onde ela acontece.
- **Minimizar repetição**: a mesma ideia em dois lugares diverge na primeira mudança (`solid`: DRY de conhecimento).
- **Lógica e dados juntos**: a regra fica com quem tem os dados (`solid`: coesão).
- **Simetria**: partes equivalentes escritas do mesmo jeito (se `create` valida e depois mapeia, `update` também).
- **Expressão declarativa**: dizer o que se quer, não como (`stream().filter(...)` com nome claro, `Specification`, annotations), quando isso fica mais claro.
- **Taxa de mudança**: o que muda no mesmo ritmo e pelo mesmo motivo fica junto; o que muda em ritmos diferentes, separado.

### Nomes que revelam intenção

- O nome diz **para que serve**, não o tipo nem a implementação: `overdueLoans`, não `list2` nem `loanArrayList`; `calculateLateFee`, não `process`.
- **Booleanos como pergunta**: `isOverdue`, `hasPendingFines`, `canRenew`. Nada de `flag`, `status2` ou negações (`isNotActive` vira `isActive` com `!`).
- **Métodos com verbo de negócio** (`renew`, `returnBook`, `chargeLateFee`), não verbos genéricos (`handle`, `doIt`, `manage`). Consulta não muda estado e se nomeia como consulta (`findActiveLoans`, `isEligible`).
- O **tamanho do nome acompanha o escopo**: `i` num laço de 3 linhas; `pendingRenewalRequests` num campo.
- **Mesmo conceito, mesmo nome** em todo o código (não `member`, `user` e `client` para a mesma coisa — o glossário de `requirements-engineering`). Nomes em inglês no código; mensagens ao usuário no idioma da preferência.
- Se o nome precisa de um comentário para ser entendido, troque o nome.

### Método composto

Cada método trabalha num **só nível de abstração**: ou orquestra passos com nome, ou faz um passo em detalhe, nunca os dois.
```java
@Transactional
public LoanDTO renew(Long id) {
    var loan = findLoan(id);
    ensureRenewable(loan);
    loan.renew(clock);
    notifyMember(loan);
    return mapper.toDto(repository.save(loan));
}
```
Ler o método conta a história; o detalhe de cada passo está num método privado com nome de negócio. Um método que mistura a orquestração com um laço de cálculo e a montagem de um e-mail no meio pede extração (`refactoring`, `cognitive-complexity`). Não extraia por extrair: um passo de uma linha clara não precisa de método próprio.

---

## Comentários no código gerado

**Default: sem comentários** — em Java, XML, YAML, SQL, Dockerfiles e arquivos de ignore. Nomes, métodos pequenos e o texto da skill ao redor carregam a explicação; o que precisar ser explicado vai na resposta do chat ou no `CLAUDE.md` do projeto, não no código.

O desenvolvedor pode optar por ter comentários no Step 0 ("Comments in generated code: yes"). Quando optar, escreva comentários curtos que expliquem o *porquê* (uma constraint, um workaround, uma decisão não óbvia), nunca comentários que repetem o que a linha faz, e nunca código comentado, marcadores `//@formatter:off` ou sobras de TODO.

Os snippets destas skills são escritos sem comentários para poderem ser copiados como estão. Aplique a preferência salva a todo arquivo que você gerar, em toda skill da família, pelo resto da conversa.

---

## Declaração de variáveis

Sempre `var` para variáveis locais quando o tipo é óbvio pelo lado direito. Nunca `var` quando o tipo seria ambíguo sem contexto.

Use `var`:
```java
var user = repository.findByUsername(username);
var token = tokenProvider.createAccessToken(username, user.getRoles());
var sortDirection = "desc".equalsIgnoreCase(direction) ? Sort.Direction.DESC : Sort.Direction.ASC;
var content = given(specification).when().post().then().extract().body().asString();
```

Tipo explícito quando o lado direito não deixa o tipo óbvio, ou quando ajuda no ponto da chamada:
```java
TokenDTO token;
Pageable pageable = PageRequest.of(page, size, sort);
```

Quando uma variável é declarada antes de um branch condicional e atribuída dentro dele, use o tipo explícito:
```java
TokenDTO token;
if (user != null) {
    token = tokenProvider.refreshToken(refreshToken);
} else {
    throw new UsernameNotFoundException("Username " + username + " not found!");
}
return ResponseEntity.ok(token);
```

---

## Instruções if

**Guard clauses de uma linha** — `if` + `throw` ou `if` + `return` sem chaves, na mesma linha:
```java
if (user == null) throw new RequiredObjectIsNullException();
if (book == null) throw new RequiredObjectIsNullException();
```

**Guard de uma linha em controllers** — `if` + `return` na mesma linha, sem chaves:
```java
if (credentialsIsInvalid(credentials)) return ResponseEntity.status(HttpStatus.FORBIDDEN).body("Invalid client request!");
if (parametersAreInvalid(username, refreshToken)) return ResponseEntity.status(HttpStatus.FORBIDDEN).body("Invalid client request!");
```

**if/else multi-linha** — sempre com chaves, corpo na linha seguinte:
```java
if (user != null) {
    token = tokenProvider.refreshToken(refreshToken);
} else {
    throw new UsernameNotFoundException("Username " + username + " not found!");
}
```

**Condições booleanas que ocupam várias linhas** — `||` e `&&` no final de cada linha, alinhados sob a primeira condição:
```java
private static boolean credentialsIsInvalid(AccountCredentialsDTO credentials) {
    return credentials == null ||
            StringUtils.isBlank(credentials.getPassword()) ||
            StringUtils.isBlank(credentials.getUsername());
}
```

**Pattern matching para `instanceof`** — faça o bind da variável na condição em vez de fazer cast na linha seguinte:
```java
if (body instanceof ProblemDetail problem && problem.getType() == null) {
    problem.setType(URI.create("about:blank"));
}
```

---

## Chamadas de método com vários argumentos

Quando os argumentos não cabem em uma linha, cada argumento na sua própria linha, indentado um nível:
```java
authenticationManager.authenticate(
    new UsernamePasswordAuthenticationToken(
        credentials.getUsername(),
        credentials.getPassword()
    )
);

var token = tokenProvider.createAccessToken(
        credentials.getUsername(),
        user.getRoles()
);
```

---

## Formatação de annotations

**Annotation única, curta** — na mesma linha da declaração:
```java
@Service
public class AuthService { ... }
```

**Annotation com vários argumentos** — cada um na sua própria linha, indentado:
```java
@Operation(
        summary = "Authenticates a user and returns a token",
        description = "Validates user credentials and generates an access token.",
        tags = {"Authentication"},
        responses = {
                @ApiResponse(description = "Success", responseCode = "200", content = @Content),
                @ApiResponse(description = "Bad Request", responseCode = "400", content = @Content)
        }
)
```

**Mapping annotations com vários media types** — vale somente em projetos que escolheram mais que JSON (veja a pergunta da skill `web-config`); cada media type então vai na sua própria linha:
```java
@PostMapping(
        consumes = {
                MediaType.APPLICATION_JSON_VALUE,
                MediaType.APPLICATION_XML_VALUE,
                MediaType.APPLICATION_YAML_VALUE},
        produces = {
                MediaType.APPLICATION_JSON_VALUE,
                MediaType.APPLICATION_XML_VALUE,
                MediaType.APPLICATION_YAML_VALUE}
)
```

Quando há somente `produces` (sem `consumes`), pode ficar em uma linha se couber:
```java
@GetMapping(produces = {
        MediaType.APPLICATION_JSON_VALUE,
        MediaType.APPLICATION_XML_VALUE,
        MediaType.APPLICATION_YAML_VALUE})
```

---

## equals() e hashCode()

Sobre todos os campos, usando getters, em uma única linha quando todos os campos cabem — nunca quebrado em várias linhas:
```java
@Override
public boolean equals(Object o) {
    if (o == null || getClass() != o.getClass()) return false;
    Book book = (Book) o;
    return Objects.equals(getId(), book.getId()) && Objects.equals(getAuthor(), book.getAuthor()) && Objects.equals(getLaunchDate(), book.getLaunchDate()) && Objects.equals(getPrice(), book.getPrice()) && Objects.equals(getTitle(), book.getTitle());
}

@Override
public int hashCode() {
    return Objects.hash(getId(), getAuthor(), getLaunchDate(), getPrice(), getTitle());
}
```

A guard clause `if (o == null || getClass() != o.getClass()) return false;` sempre em uma linha.

---

## Getters e setters

Cada getter e setter nas suas próprias linhas — nunca em uma linha só:
```java
public Long getId() {
    return id;
}

public void setId(Long id) {
    this.id = id;
}
```

---

## Coleções

- **Declare pela interface que expressa a semântica**: `List` quando a **ordem** importa ou há repetição, `Set` quando o que importa é **não repetir** (tags, ids, permissões), `Map` para **busca por chave**, `SequencedCollection` quando importa o primeiro e o último (`java-modern-features`). `List` onde a regra é unicidade esconde um bug de duplicata.
- **Nunca devolva `null` para coleção**: devolva vazia (`List.of()`). Quem chama itera sem `if`, e o `null` não vaza para o JSON.
- **Coleção que não deve mudar**: `List.of`, `Set.of`, `Map.of` para literais; `List.copyOf`/`Set.copyOf` para publicar uma cópia imutável (configuração carregada no startup, resultado de regra); `Stream.toList()` já devolve lista não modificável.
- **Cópia de segurança** ao guardar ou devolver uma coleção que o outro lado pode alterar, em classes com invariantes (domínio rico, value objects, componentes com estado). Nas entities e DTOs do flat-by-layer, o Hibernate e mappers baseados em setters usam coleção mutável: lá, a regra é o service não alterar coleção com regra por fora da entity (`solid`, "Estado com regra").
- **Parâmetro coletor**: quando vários métodos contribuem para um resultado, passe a coleção que acumula (`collectViolations(loan, violations)`) em vez de criar e juntar listas em cada um.
- Volume grande não cabe em coleção: pagine ou percorra em stream (`pagination`, `design-patterns`: Iterator).

---

## Declaração do logger

SLF4J em todo lugar — services, factories, components — declarado `private static final`, construído a partir da classe:
```java
private static final Logger logger = LoggerFactory.getLogger(BookService.class);
```

Os imports são `org.slf4j.Logger` e `org.slf4j.LoggerFactory` (o Spring Boot traz o SLF4J pelo seu logging starter; nenhuma dependency extra). Faça log com placeholders `{}`, nunca com concatenação de strings nem patterns de `String.format` — o SLF4J não interpreta `%s`/`%n`:
```java
logger.info("Email sent to {}", recipient);
```

---

## Idioms modernos de Java

Features do Java 17+ que o codebase usa onde encaixam. Nenhuma é obrigatória para uma feature funcionar.

- **Records** para payloads imutáveis, somente de serialização, sem framework que precise de setters, como o error body: `public record ExceptionResponse(Instant timestamp, String message, String details) {}`. Entities JPA e DTOs de entidade que estendem `RepresentationModel` (HATEOAS) continuam classes com constructor sem argumentos.
- **`instanceof` pattern matching** (veja acima) em vez de um cast na linha seguinte.
- **`Stream.toList()`** em vez de `collect(Collectors.toList())` quando o resultado só é lido.
- **Text blocks** para fixtures multi-linha em testes (conteúdo CSV, bodies JSON).
- **Records privados dentro de uma classe de teste** para fixtures pequenas de teste.

---

## Jackson 3 em testes e helpers

O Spring Boot 4 usa Jackson 3: os packages são `tools.jackson.core`, `tools.jackson.databind` e `tools.jackson.dataformat.*`. O package das annotations **não** mudou — `@JsonProperty`, `@JsonIgnore` e `@JsonInclude` ainda são importadas de `com.fasterxml.jackson.annotation`.

- Mappers são imutáveis: construa-os, não os mute.
```java
var objectMapper = JsonMapper.builder()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();
```
- `JacksonException` é unchecked, então métodos de teste e helpers não declaram mais `throws JsonProcessingException`.
- O Jackson 3 ignora properties desconhecidas por default; habilite `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` explicitamente onde rejeitá-las for o comportamento pretendido.

---

## Formatação de chain do REST Assured

Cada método na sua própria linha, indentado para mostrar o agrupamento lógico: setup → body → when → then → extract:

```java
tokenDto = given()
        .basePath("/auth/signin")
        .port(TestConfigs.SERVER_PORT)
        .contentType(MediaType.APPLICATION_JSON_VALUE)
        .body(credentials)
        .when()
        .post()
        .then()
        .statusCode(200)
        .extract()
        .body()
        .as(TokenDTO.class);
```

---

## Atribuição de variável após o REST Assured

Sempre atribua a uma variável tipada primeiro, depois ao campo static compartilhado:
```java
BookDTO createdBook = objectMapper.readValue(content, BookDTO.class);
book = createdBook;
```

Não:
```java
book = objectMapper.readValue(content, BookDTO.class);
```
(perde a referência intermediária).

---

## Quebra de linha em chamada de constructor

Quando uma chamada de constructor com dois ou mais argumentos é atribuída a uma variável, quebre depois do `=`:
```java
AccountCredentialsDTO credentials =
    new AccountCredentialsDTO("leandro", "admin123");
```

---

## Linhas vazias

- Uma linha em branco entre os campos e o primeiro constructor.
- Uma linha em branco entre métodos.
- Nenhuma linha em branco entre `@Override` e a assinatura do método.
- Nenhuma linha em branco entre a(s) annotation(s) da classe e `public class`.
- Uma linha em branco após a chave de abertura de um método que tenha mais de duas instruções.

---

## Regras principais

- **Código que comunica**: comunicação, simplicidade e flexibilidade desempatam; nomes que revelam intenção (booleanos como pergunta, verbos de negócio, mesmo conceito com o mesmo nome); método composto, com um só nível de abstração.
- **Coleções**: interface pela semântica (`List`/`Set`/`Map`), vazia em vez de `null`, imutável quando não deve mudar, cópia de segurança em classes com invariantes.
- **Sem comentários no código gerado**, a menos que o desenvolvedor tenha optado por eles no Step 0.
- `var` para locais quando o tipo é óbvio — tipo explícito quando declarada antes de um branch.
- Guard clauses de uma linha (`if (x == null) throw ...`) — sem chaves, sem nova linha.
- `if/else` multi-linha sempre usa chaves.
- Returns booleanos com várias condições: `||` / `&&` no final da linha, próxima condição indentada.
- O return de `equals()` em uma única linha, independentemente do comprimento.
- Logger: SLF4J, `private static final`, placeholders `{}`.
- Chains do REST Assured: um método por linha, chain completa.
- Variável intermediária antes de atribuir ao campo static em testes.
- Indentação de 4 espaços.
- **Sem Lombok** — nunca. Esta é uma escolha deliberada.

## Referências

- Kent Beck, *Padrões de Implementação* (Bookman, 2013; original *Implementation Patterns*, Addison-Wesley, 2007): valores e princípios (comunicação, simplicidade, flexibilidade; consequências locais, simetria, taxa de mudança), nome revelador de intenção, método composto, parâmetro coletor, coleções e cópia de segurança. Classes anônimas, exceções verificadas e a medição de desempenho do apêndice ficaram de fora por estarem superadas no Java 25 e no padrão do pacote.
