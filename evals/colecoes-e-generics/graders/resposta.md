---
type: llm
weight: 1
---

Aponta e corrige os 7 pontos: troca LinkedList por ArrayDeque (memória e localidade de cache), HashSet<LoanStatus> por EnumSet, new HashMap<>(100) por HashMap.newHashMap(100) por causa do load factor 0.75, TreeSet só por launchDate descartando livros empatados na mesma data (desempatar com id ou título), subtração a.getPages() - b.getPages() sujeita a overflow por Comparator.comparingInt(Book::getPages) / Integer.compare, cópia defensiva List.copyOf(books) no compact constructor do record CatalogSnapshot, e a ordem aleatória por JVM de Set.of corrigida com containsExactlyInAnyOrder no AssertJ. O agente só tem ferramentas de leitura: orientar basta.
