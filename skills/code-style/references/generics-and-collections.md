# Generics e Coleções — Guia de referência

Complementa a seção **Coleções e generics** de [`../SKILL.md`](../SKILL.md), com base em Naftalin, Wadler e Marks (*Java Generics and Collections*, 2ª ed., O'Reilly, 2025).

---

## 1. Escolha da implementação na JCF

Em hardware moderno, **estruturas apoiadas em arrays vencem listas encadeadas** quase sempre: referências contíguas cabem na mesma *cache line* da CPU (64 bytes), enquanto cada nó de `LinkedList` aloca ~24 bytes extras e espalha ponteiros pela heap.

| Necessidade | Escolha padrão | Observação prática |
|---|---|---|
| Lista de uso geral | `ArrayList` | Leitura `O(1)`, iteração amigável ao cache; `List.of` / `List.copyOf` quando não muda |
| Fila FIFO ou pilha LIFO | `ArrayDeque` | Substitui `LinkedList` e a legada `Stack`; não aceita `null` |
| Conjunto sem ordem / com ordem de inserção | `HashSet` / `LinkedHashSet` | Pré-dimensione com `HashSet.newHashSet(n)` / `LinkedHashSet.newLinkedHashSet(n)` |
| Conjunto de constantes de `enum` | `EnumSet` | Vetor de bits num único `long` (até 64 constantes); atenção: `EnumSet.of(...)` é **mutável** (envolva com `Collections.unmodifiableSet` ou `Sets` se for expor) |
| Mapa geral / com ordem de inserção | `HashMap` / `LinkedHashMap` | Pré-dimensione com `HashMap.newHashMap(n)` / `LinkedHashMap.newLinkedHashMap(n)` |
| Mapa cuja chave é `enum` | `EnumMap` | Array indexado por `ordinal()`, sem colisão de hash: `new EnumMap<>(LoanStatus.class)` |
| Conjunto ou mapa ordenado por chave | `TreeSet` / `TreeMap` (`NavigableSet`/`NavigableMap`) | `O(log n)`; exige `Comparable` ou `Comparator` **consistente com `equals`** |
| Fila por prioridade | `PriorityQueue` | `iterator()` **não** percorre em ordem de prioridade — só `poll()` retira na ordem |
| Concorrência entre threads | `ConcurrentHashMap`, `ConcurrentHashMap.newKeySet()`, `CopyOnWriteArrayList`, `ArrayBlockingQueue` | `ConcurrentHashMap` e `ArrayBlockingQueue` rejeitam `null` com `NullPointerException` |

**O que não usar em código novo:**
- **`LinkedList`**: mais memória e pior localidade de cache que `ArrayList` e `ArrayDeque`.
- **`Vector`, `Stack`, `Hashtable`, `Enumeration`**: legados sincronizados por método.
- **`Collections.synchronizedList`/`Map`**: ainda exigem `synchronized` manual ao iterar e sofrem corrida em operações compostas ("verifica e age").
- **`WeakHashMap` como cache**: mantém referências fracas para as *chaves*, não para os valores; para cache em memória, use Caffeine (`caching`).

---

## 2. Ownership: views vivas × snapshots imutáveis

"Não modificável" (*unmodifiable*) **não** é sinônimo de imutável:

| Fábrica / wrapper | Aceita `null`? | O que acontece se a coleção original mudar depois? | Ordem de iteração |
|---|---|---|---|
| `List.of(...)`, `Set.of(...)`, `Map.of(...)` | Não (`NPE`); `Set.of`/`Map.of` também lançam `IllegalArgumentException` em duplicata | Não há coleção de origem | `List.of` fixa; **`Set.of`/`Map.of` mudam de ordem a cada execução da JVM** |
| `List.copyOf(c)`, `Set.copyOf(c)`, `Map.copyOf(m)` | Não (`NPE`) | **Nada** — é um snapshot independente (e evita cópia se `c` já veio de `*.of`) | Igual acima |
| `Stream.toList()` | Sim | **Nada** — lista não modificável independente | Ordem do stream |
| `Collections.unmodifiableList(backing)` | Sim | **Vaza para quem lê** — é apenas uma *view* somente-leitura sobre `backing` | A de `backing` |
| `Arrays.asList(array)` | Sim | **Muta nos dois sentidos** — tamanho fixo (`add`/`remove` lançam `UOE`), mas `set(i, x)` altera `array[i]` | Ordem do array |

Regra de *ownership*:
- **Na entrada** (construtor de aggregate, value object, `record` ou configuração): copie com `List.copyOf(items)` / `Set.copyOf(items)` para cortar o *aliasing* com o chamador.
- **Na saída** de objeto mutável interno: `Collections.unmodifiableSet(tags)` é barata quando o próprio dono controla as mutações, ou `Set.copyOf(tags)` se o chamador precisar de um retrato estável no tempo.
- Quando o chamador **precisa** de uma coleção mutável a partir de um stream, deixe explícito: `.collect(Collectors.toCollection(ArrayList::new))` (pois `Collectors.toList()` não promete mutabilidade para sempre e `Stream.toList()` é imutável).

---

## 3. Operações compostas em `Map` e armadilhas de `null`

Prefira operações compostas a pares `containsKey` + `get`/`put`:

```java
Map<Author, List<Book>> byAuthor = HashMap.newHashMap(authorsCount);
for (var book : books) {
    byAuthor.computeIfAbsent(book.getAuthor(), _ -> new ArrayList<>()).add(book);
}

Map<Long, BigDecimal> fineByMember = new HashMap<>();
for (var fine : fines) {
    fineByMember.merge(fine.memberId(), fine.amount(), BigDecimal::add);
}
```

Cuidados sutis do contrato de `Map`:
- Em `computeIfAbsent(key, mappingFn)`, se `mappingFn` retornar `null`, **nenhuma entrada é inserida**.
- Em `compute`, `computeIfPresent` e `merge`, se a função de remapeamento retornar `null`, **a chave existente é removida do mapa**.
- Em `merge(key, value, remappingFn)`, passar `value == null` lança `NullPointerException` imediatamente.
- Em mapas que aceitam valores `null` (`HashMap`), `getOrDefault(k, padrao)` devolve `null` quando a chave está mapeada para `null`, enquanto `putIfAbsent(k, novo)` sobrescreve o `null` associado.

---

## 4. `Comparable`, `Comparator` e invariantes de ordenação

```java
Comparator<Book> byLaunchThenTitle = Comparator
        .comparing(Book::getLaunchDate, Comparator.nullsLast(Comparator.naturalOrder()))
        .thenComparing(Book::getTitle)
        .thenComparingLong(Book::getId);
```

- **Proibido subtrair números para comparar** (`return this.pages - other.pages;`): valores com sinais opostos estouram `int`/`long` e invertem a ordem. Use `Integer.compare(this.pages, other.pages)` ou `Comparator.comparingInt(Book::getPages)` (que também evita *autoboxing*).
- **Unbox de `null`**: comparar ou somar `Integer`/`Long` vindo de lista/mapa com elemento `null` lança `NullPointerException` no unboxing implícito.
- **Consistência com `equals` (`x.compareTo(y) == 0` se e só se `x.equals(y)`)**: `TreeSet` e `TreeMap` decidem igualdade **pelo `compareTo`/`Comparator`, não por `equals`**.
  - `new BigDecimal("4.0").compareTo(new BigDecimal("4.00")) == 0`, mas `equals` é `false`: num `HashSet` entram dois valores; num `TreeSet`, só um.
  - Um `new TreeSet<>(Comparator.comparing(Book::getLaunchDate))` **descarta silenciosamente** um segundo livro lançado no mesmo dia! Desempate sempre até uma chave única (`.thenComparingLong(Book::getId)`).

---

## 5. Generics pragmáticos

- ***Cast-Iron Guarantee***: os casts implícitos inseridos pelo compilador após o *type erasure* nunca lançam `ClassCastException` em runtime — **desde que o código compile sem warnings `unchecked`**. Um único cast bruto ou `@SuppressWarnings("unchecked")` errado invalida a garantia e faz o `ClassCastException` estourar longe da origem (*heap pollution*).
- **Onde suprimir**: nunca anote a classe ou um método grande com `@SuppressWarnings("unchecked")`. Extraia uma variável local apenas para a expressão do cast e anote-a.
- **Evite *type variable* de uso único**: se `<T>` aparece uma vez só na assinatura e não relaciona dois parâmetros nem o retorno, troque por `?`:
  ```java
  public static boolean hasAnyElement(Collection<?> items) {
      return items != null && !items.isEmpty();
  }
  ```
- **PECS (*Get and Put Principle*)** em métodos utilitários e contratos reutilizáveis (não polua assinaturas simples de CRUD onde não há subtipagem):
  - **`? extends T`** quando o método só **lê** (*get*/produz) elementos da estrutura: `BigDecimal totalPrice(Collection<? extends PricedItem> items)`.
  - **`? super T`** quando o método só **insere** (*put*/consome) elementos ou compara: `Comparator<? super Book>`, `void appendActive(Collection<? super Book> target)`.
  - **Sem wildcard** (`List<T>`) quando o método lê **e** escreve na mesma coleção.
  - **`List<? extends Book>` não é imutável**: o compilador bloqueia `add(book)`, mas `clear()`, `remove(0)`, `removeIf(...)` e `sort(...)` continuam compilando. Para impedir mutação, use `List.copyOf` ou `Collections.unmodifiableList`.
- **Captura de wildcard**: quando precisar do tipo dentro da implementação, exponha o wildcard na assinatura pública e delegue a um helper privado genérico (`private static <T> void swapFirstLast(List<T> list)`).
- **`@SafeVarargs`**: só é permitido em métodos que não podem ser sobrescritos (`static`, `private` ou `final`). Dentro dele, **nunca** armazene outro valor no array `T...` nem devolva/exponha o array `T[]` para fora (o array real em runtime pode ser `Object[]` e causar `ClassCastException` no chamador). Na dúvida, receba `List<? extends T>` e deixe o chamador passar `List.of(...)`.
- **Tokens de tipo em runtime**: como `T` sofre *erasure*, passe `Class<T>` para APIs reflexivas/registries ou `ParameterizedTypeReference<List<BookDTO>>` no `RestClient` (`restClient.get().uri("/api/book/v1").retrieve().body(new ParameterizedTypeReference<>() {})`).
