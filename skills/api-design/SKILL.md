---
name: api-design
description: Desenho de APIs REST por padrões no Spring Boot 4 — visibilidade e tipo de integração como decisão (pública, de parceiros, interna; frontend × backend), papéis de endpoint (processamento, dado operacional, mestre e de referência, link lookup, transferência de dados), responsabilidades de operação (criação, consulta, transição de estado, função de cálculo), estrutura de mensagens e papéis dos elementos (dado, metadado, id, link, contexto), entidade embutida × link, campos escolhidos pelo cliente, request bundle, requisição condicional (ETag, If-None-Match → 304, If-Match → 412/428), garantias de ciclo de vida e checklist de revisão. Use antes de criar endpoints além do CRUD, ao modelar uma API pública ou entre serviços, ou ao revisar um contrato. Não use para a mecânica de versão (api-versioning), paginação (pagination), links HAL (hateoas) nem OpenAPI (swagger, swagger-advanced).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (controller, DTO e service do pacote), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../exception-handling/SKILL.md`](../exception-handling/SKILL.md) (status de erro), [`../api-versioning/SKILL.md`](../api-versioning/SKILL.md), [`../pagination/SKILL.md`](../pagination/SKILL.md), [`../idempotency/SKILL.md`](../idempotency/SKILL.md) e [`../application-security/SKILL.md`](../application-security/SKILL.md). Domínio rico por trás da API: [`../ddd-hexagonal/SKILL.md`](../ddd-hexagonal/SKILL.md).

# Desenho de API

O CRUD por entity do pacote (`GET/POST/PUT/DELETE /api/book/v1`) é o ponto de partida certo para **dado simples**. Quando o recurso tem **regra, ciclo de vida ou consumidor externo**, uma API desenhada a partir da tabela vaza o modelo de dados, empurra a regra para o cliente e quebra a cada mudança interna. Esta skill dá o vocabulário para desenhar a API **a partir do uso**: cada padrão é uma **opção**, e as forças (acoplamento, desempenho, evolução, segurança) são os **critérios** para escolher. Registre as escolhas no design doc (`design-docs`).

## 1. Antes de desenhar: quem consome e como

A **visibilidade** define o rigor de todo o resto:

| Visibilidade | Consumidores | Contrato e versão | Documentação | Segurança e limites |
|---|---|---|---|---|
| **Pública** | Desconhecidos, na internet | Rígido; quebra só com versão nova e prazo longo (`api-versioning`) | Completa, com exemplos e sandbox (`swagger-advanced`) | Autenticação forte, rate limit por cliente, ids não sequenciais (`application-security`) |
| **De parceiros** (*community*) | Organizações conhecidas, com acordo | Estável; mudança negociada e anunciada | Completa; changelog | Por cliente (API key + OAuth2), cotas por contrato |
| **Interna da solução** | Outros serviços ou o frontend do mesmo produto | Pode evoluir rápido, com **contract tests** (`contract-testing`) | OpenAPI gerado basta | Serviço a serviço (`service-communication`) |

E o **tipo de integração**:
- **Frontend** (tela, app, BFF): respostas moldadas para a tela, poucas chamadas por página, dados agregados. Um BFF (`api-gateway`) evita contaminar a API de domínio com formato de tela.
- **Backend** (serviço ↔ serviço): granularidade por **capacidade de negócio**, contrato estável, eventos quando ninguém precisa da resposta (`messaging`).

Uma API interna que vira pública "porque um parceiro pediu" herda decisões que não foram feitas para isso (ids sequenciais, erros com detalhe interno, sem limite). Trate a mudança de visibilidade como **decisão nova**, com ADR.

## 2. Papéis de endpoint

Cada endpoint tem **um** papel; o papel decide cache, concorrência, ciclo de vida e granularidade.

| Papel | O que é | Exemplo | Como desenhar |
|---|---|---|---|
| **Recurso de processamento** | Executa uma atividade ou comando | `POST /api/loan/v1/{id}/renewal`, `POST /api/fine/v1/simulations` | Orientado à ação; resposta com o resultado; idempotência quando o cliente pode repetir (`idempotency`) |
| **Dado operacional** | Muda muito, vida curta, ligado a um processo | `Loan`, `Reservation` | Escrita frequente: concorrência explícita (`@Version`, `If-Match` — seção 6), transições por ação (seção 3), listagem paginada |
| **Dado mestre** | Vida longa, muitos dependem dele | `Book`, `Member` | Mudanças raras e auditadas; outros serviços guardam **só o id**; cache com validação (ETag) |
| **Dado de referência** | Quase estático, consultado o tempo todo | Categorias, políticas de empréstimo, países | Só leitura na API; `Cache-Control` longo + ETag; muitas vezes basta um enum ou configuração, sem endpoint |
| **Link lookup** | Resolve um identificador em localização | `GET /api/catalog/v1/lookup?isbn=...` → link do recurso | Desacopla o cliente de onde o recurso vive; use pouco |
| **Transferência de dados** | Área para troca de volume grande ou assíncrona | Upload/download com URL pré-assinada, job de exportação | `file-upload-download`, `file-import-export`, `aws-s3-sqs`; a API devolve onde buscar, não os bytes |

**Não misture papéis** no mesmo recurso: um `Book` (dado mestre) com o contador de exemplares disponíveis (dado operacional, muda a cada empréstimo) força cache curto e concorrência no recurso inteiro. Separe (`/books/{id}` e `/books/{id}/availability`).

## 3. Responsabilidades de operação

| Responsabilidade | Lê estado? | Muda estado? | HTTP típico | Exemplo |
|---|---|---|---|---|
| **Criação de estado** | Só para validar | Cria | `POST` → **201** + `Location` | `POST /api/loan/v1` |
| **Consulta** | Sim | Não | `GET`, paginado e filtrado (`pagination`) | `GET /api/loan/v1?memberId=7` |
| **Transição de estado** | Sim | Sim | `POST` no sub-recurso da ação (ou `PATCH` para atualização parcial de dados) | `POST /api/loan/v1/{id}/renewal`, `.../return` |
| **Função de cálculo** | Não | Não | `GET` com parâmetros; `POST` só se a entrada for grande, e mesmo assim sem efeito | `POST /api/fine/v1/simulations` |

`PUT` é **substituição completa** e serve ao dado mestre quando o cliente é dono da representação inteira. Não use `PUT` para mudar estado de processo.

### Transição de estado: ação explícita, não `PUT` com `status`

```java
// ❌ o cliente decide a transição e burla as regras
// PUT /api/loan/v1/10  {"status": "RENEWED", "dueDate": "2026-12-20"}
```
O cliente precisa conhecer a regra (quantas renovações, quantos dias), pode pular estados (`RETURNED` → `ACTIVE`) e escrever campos que não deveria (**mass assignment** — `application-security`). A transição vira uma **ação** com nome de negócio:
```java
@PostMapping(value = "/{id}/renewal", produces = MediaType.APPLICATION_JSON_VALUE)
@Override
public LoanDTO renew(@PathVariable("id") Long id) {
    return service.renew(id);
}
```
```java
@Transactional
public LoanDTO renew(Long id) {
    var loan = repository.findById(id)
        .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
    loan.renew(clock);
    return parseObject(repository.save(loan), LoanDTO.class);
}
```
A regra mora no domínio (`loan.renew(clock)` — `ddd-hexagonal`, ou no service no flat-by-layer); transição inválida lança uma exception de domínio mapeada para **409 Conflict** (`exception-handling`). Cada ação vira um teste e uma linha no OpenAPI, e o `hateoas` pode anunciar só as ações possíveis no estado atual. Ação que o cliente pode repetir por timeout precisa de `Idempotency-Key` (`idempotency`).

## 4. Estrutura das mensagens

| Estrutura | Quando | Exemplo |
|---|---|---|
| **Parâmetro simples** | Um valor identifica ou filtra | `GET /books/{id}`, `?isbn=978...` |
| **Lista de parâmetros** | Vários filtros independentes | `?author=Martin&from=2020-01-01&to=2020-12-31` |
| **Árvore** | O dado é aninhado de verdade | `LoanDTO` com `items: [{bookId, quantity}]` |
| **Várias árvores no topo** | Raro; prefira uma raiz | `{"loan": {...}, "member": {...}}` só quando são de fato independentes |

Prefira **plano** quando der e **aninhado quando o domínio é aninhado**; profundidade acima de 3 costuma ser modelo de banco vazando. Nada de `Map<String, Object>` como DTO: o contrato some do OpenAPI. **DTO de request ≠ DTO de response** quando diferem (o request não traz `id`, `version` nem campos calculados).

Cada elemento tem um **papel**:
| Papel | O que é | No pacote |
|---|---|---|
| **Dado** | O conteúdo de domínio | `title`, `price`, `dueDate` |
| **Metadado** | Dado sobre o dado | `version`, `createdAt`, metadados de página (`pagination`) |
| **Id** | Identifica, estável e opaco | `id`, `isbn`. Em API **pública**, prefira id não sequencial (UUIDv7 — `data-modeling`) para não permitir enumeração |
| **Link** | Aponta para outro recurso ou ação | `_links` (`hateoas`) ou URL absoluta |

Três representações especiais já têm dono no pacote: o **relatório de erro** (`ExceptionResponse`/`ProblemDetail` — `exception-handling`); o **contexto** da requisição (autenticação, `traceparent`, `Idempotency-Key`, `Accept-Language`), que vai em **header**, não no corpo (`observability`, `idempotency`); e a **API key**, que identifica a aplicação cliente para limite e cobrança, nunca o usuário, e não substitui autenticação (`api-gateway`).

## 5. Granularidade e forma da resposta

### Entidade embutida × link

| Embuta (`"book": {"id": 1, "title": "..."}`) | Use link ou id (`"bookId": 1` + `_links.book`) |
|---|---|
| O cliente **sempre** precisa do dado junto | O dado é grande ou raramente usado |
| É um **resumo** pequeno e estável | Tem ciclo de vida próprio (muda sem o pai mudar) |
| Evita N chamadas por tela (frontend) | Embutir criaria payload enorme ou ciclo |

Nunca embuta **coleção sem limite** (os 2 mil empréstimos de um sócio dentro do `MemberDTO`): vira sub-recurso paginado (`/members/{id}/loans`). Resumo embutido é um DTO próprio (`BookSummaryDTO`), não a entity.

### O cliente escolhe os campos

Quando consumidores diferentes precisam de partes diferentes do mesmo recurso:
- **Visões nomeadas** (`?view=summary|full`), cada uma um DTO: a opção mais simples e a padrão do pacote; o contrato continua explícito no OpenAPI.
- **Lista de campos** (`?fields=id,title,price`): só para API pública com consumidores muito heterogêneos. Valide contra uma **lista de campos permitidos** (como a ordenação em `pagination`) e nunca exponha campo que o DTO completo não exporia.
- Se moldar a resposta virar o centro do problema (cada tela pede um grafo diferente), avalie GraphQL num BFF, com ADR.

### Request bundle

Várias operações numa chamada (`POST /api/book/v1/batch` com 200 livros) quando a **tagarelice** foi medida, não suposta:
- Limite de itens por requisição (como o `size` máximo da paginação).
- Resultado **por item** (`[{"index": 0, "status": 201, "id": 42}, {"index": 1, "status": 400, "errors": [...]}]`), e a semântica declarada: **tudo ou nada** (uma transação) ou **parcial**.
- Idempotência por lote ou por item (`idempotency`); volume grande ou lento vai para importação assíncrona (`file-import-export`).

## 6. Requisição condicional (ETag)

Dois usos diferentes do mesmo mecanismo.

**1. Economizar banda em leituras (`If-None-Match` → 304).** O `ShallowEtagHeaderFilter` do Spring calcula o hash do corpo e responde **304 Not Modified** quando o cliente manda o mesmo `ETag`:
```java
@Configuration
public class EtagConfig {

    @Bean
    public FilterRegistrationBean<ShallowEtagHeaderFilter> shallowEtagHeaderFilter() {
        var registration = new FilterRegistrationBean<>(new ShallowEtagHeaderFilter());
        registration.addUrlPatterns("/api/*");
        return registration;
    }
}
```
Ele **economiza rede, não processamento**: a consulta roda inteira e o corpo é bufferizado para calcular o hash. Não use em download grande ou streaming (`file-upload-download`). Para dado de referência, some `Cache-Control` (`ResponseEntity.ok().cacheControl(CacheControl.maxAge(Duration.ofHours(1)))`). Confirme o package do `FilterRegistrationBean` na versão do Boot (`library-docs`).

**2. Concorrência otimista via HTTP (`If-Match` → 412).** Dois atendentes abrem o mesmo livro e salvam: sem controle, o segundo apaga a alteração do primeiro (*lost update* — `data-modeling`). O `ETag` passa a ser a `@Version` da entity, exposta como metadado no DTO:
```java
@GetMapping(value = "/{id}", produces = MediaType.APPLICATION_JSON_VALUE)
@Override
public ResponseEntity<BookDTO> findById(@PathVariable("id") Long id) {
    var book = service.findById(id);
    return ResponseEntity.ok().eTag(String.valueOf(book.getVersion())).body(book);
}

@PutMapping(value = "/{id}", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
@Override
public ResponseEntity<BookDTO> update(@PathVariable("id") Long id,
                                      @RequestHeader(value = HttpHeaders.IF_MATCH, required = false) String ifMatch,
                                      @RequestBody BookDTO book) {
    if (ifMatch == null) throw new PreconditionRequiredException();
    var updated = service.update(id, parseVersion(ifMatch), book);
    return ResponseEntity.ok().eTag(String.valueOf(updated.getVersion())).body(updated);
}

private Long parseVersion(String ifMatch) {
    try {
        return Long.valueOf(ifMatch.replace("W/", "").replace("\"", "").trim());
    } catch (NumberFormatException e) {
        throw new PreconditionFailedException();
    }
}
```
```java
@Transactional
public BookDTO update(Long id, Long expectedVersion, BookDTO book) {
    var entity = repository.findById(id)
        .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
    if (!entity.getVersion().equals(expectedVersion)) throw new PreconditionFailedException();
    entity.setTitle(book.getTitle());
    entity.setPrice(book.getPrice());
    return parseObject(repository.save(entity), BookDTO.class);
}
```
- `PreconditionFailedException` → **412 Precondition Failed** (a versão mudou: o cliente relê e reaplica); `PreconditionRequiredException` → **428 Precondition Required** (a API exige `If-Match`). Ambas como as outras exceptions de domínio, com `@ResponseStatus` e handler (`exception-handling`).
- A comparação no service cobre o caso comum; a corrida entre a leitura e o `save` é pega pelo `@Version` do JPA (`ObjectOptimisticLockingFailureException`), que no mesmo fluxo também deve virar **412**.
- O `GET` com `ETag` no `ResponseEntity` já responde **304** a um `If-None-Match` igual, sem o filtro. Use **um** dos dois mecanismos por rota.
- Exija `If-Match` nos recursos de **dado operacional e mestre** com edição concorrente; nas transições de estado (seção 3) ele também protege contra agir sobre um estado que já mudou.

Teste os quatro caminhos (`testing`, `@WebMvcTest`): `GET` devolve `ETag`; `GET` com `If-None-Match` igual → 304; `PUT` com versão velha → 412; `PUT` sem `If-Match` → 428.

## 7. Garantias de ciclo de vida

A mecânica de versão está em `api-versioning`; aqui, a **promessa** que você faz ao consumidor, que deve ser publicada junto com a API:

| Garantia | O que promete | Quando usar |
|---|---|---|
| **Prévia experimental** | Nada: pode mudar ou sumir sem aviso | Validar um desenho com poucos consumidores que aceitaram o risco (`/api/book/v2-preview`, grupo separado no OpenAPI); nunca em produção crítica |
| **Duas em produção** | A versão anterior convive com a nova até a migração | Padrão do pacote (`api-versioning`: no máximo duas majors) |
| **Vida útil limitada** | Cada versão vive **N meses** depois da sucessora, com data publicada | API pública e de parceiros (6–12 meses é comum) |
| **Obsolescência agressiva** | Remoção com aviso curto | Exceção: falha de segurança ou custo insustentável, com comunicação direta a cada consumidor (`release-management`) |
| **Vida útil eterna** | Nunca quebra | Raro e caro: só para contrato muito estável e consumidores que não podem migrar |

**Versionamento semântico do contrato:** a **major** vai no path (`/v1` → `/v2`, quebra); **minor** (adição compatível) e **patch** (correção) vão no `info.version` do OpenAPI e no changelog da API. Mudança aditiva não muda o path.

## 8. Limites, planos e acordos

- **Rate limit**: por cliente (API key ou usuário), com **429** e `Retry-After` (`api-gateway`, `resilience`, `redis`).
- **Plano de uso** (cotas e cobrança por consumo): só quando a API é produto vendido; a medição é por API key e por operação (`technical-product-management`).
- **SLA**: o que a API promete (disponibilidade, latência) e a consequência de não cumprir, derivado do SLO interno (`technical-product-management`). API interna tem SLO; SLA é para pública e de parceiros.

## 9. Checklist de revisão de API

- A **visibilidade** e o **tipo de integração** estão registrados, e o rigor (versão, documentação, segurança) é compatível com eles?
- Cada endpoint tem **um papel**? Dado mestre e dado operacional estão separados?
- Mudança de estado de processo é **ação com nome de negócio**, não `PUT`/`PATCH` em `status`?
- `POST` de criação devolve **201 + `Location`**; função de cálculo **não tem efeito colateral**?
- DTO de request e de response separados quando diferem; nada de entity nem `Map<String, Object>`?
- Coleções **paginadas** e com limite; nada de coleção sem limite embutida?
- Edição concorrente protegida por **`If-Match`/`@Version`** (412/428)?
- Contexto (auth, trace, idempotência, idioma) em **header**; erros no formato do pacote?
- Em API pública: ids não enumeráveis, rate limit, garantia de ciclo de vida publicada?

## 10. Anti-patterns

- **API espelho do banco**: um endpoint por tabela, com colunas internas e FKs no JSON.
- **`PUT` genérico com `status`** para mudar estado de processo.
- **Endpoint "faz-tudo"** (`POST /api/operations` com `{"type": "RENEW"}`): esconde o contrato e o OpenAPI não o descreve.
- **Função de cálculo com efeito colateral** (uma "simulação" que grava).
- **Coleção sem limite** embutida ou devolvida por `findAll`.
- **Chatty API**: a tela faz 30 chamadas para montar uma página (agregue num BFF ou embuta o resumo).
- **Lista de campos livre** sem lista de permitidos.
- **Contexto no corpo** (token, `traceId` ou idioma como campo do DTO).
- **Visibilidade decidida por acidente**: a API interna exposta a parceiros sem revisão.
- **ETag sem validação**: devolver `ETag` e ignorar o `If-Match` no `PUT`.

---

## Regras principais

- **Decida visibilidade e tipo de integração primeiro**: pública, de parceiros ou interna; frontend ou backend. Elas definem o rigor de versão, documentação, segurança e SLA.
- **Um papel por endpoint**: processamento, dado operacional, mestre, de referência, link lookup ou transferência. Não misture dado mestre com contador operacional.
- **Operações com responsabilidade clara**: criação (`POST` → 201), consulta (`GET` paginado), **transição de estado como ação** (`POST /{id}/renewal`, regra no domínio, 409 para transição inválida), função de cálculo sem efeito.
- **Mensagens**: plano quando der, aninhado quando o domínio é; DTOs separados de request e response; cada elemento com papel (dado, metadado, id, link); contexto em header.
- **Embuta só resumo pequeno e sempre necessário**; o resto por link ou id; nunca coleção sem limite.
- **Visões nomeadas** antes de `?fields=`; lista de campos permitidos; request bundle com limite e resultado por item.
- **ETag**: filtro raso para economizar banda; `@Version` + `If-Match` para concorrência (412, 428 sem header), testado nos quatro caminhos.
- **Garantia de ciclo de vida publicada**; major no path, minor e patch no OpenAPI.
- **Sem Lombok** — deliberado.

## Referências

- Olaf Zimmermann, Mirko Stocker, Daniel Lübke, Uwe Zdun e Cesare Pautasso, *Patterns for API Design: Simplifying Integration with Loosely Coupled Message Exchanges* (Addison-Wesley, 2022): padrões de fundação, papéis e responsabilidades, estrutura de mensagens, qualidade, evolução e documentação. Os padrões foram reescritos com os exemplos do pacote (`Book`, `Loan`) e o Spring Boot 4.
