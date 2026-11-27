---
tags: [gatilho, estilo]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Revise o uso de coleções e generics neste trecho de catálogo em memória: guardamos a fila de reindexação numa LinkedList, os status elegíveis num HashSet<LoanStatus>, criamos new HashMap<>(100) para exatamente 100 entradas, ordenamos os livros num TreeSet<>(Comparator.comparing(Book::getLaunchDate)) e em outro ponto com (a, b) -> a.getPages() - b.getPages(), expomos record CatalogSnapshot(String tenant, List<BookSummary> books) {} sem construtor compacto, e num teste comparamos Set.of("JAVA", "SPRING", "SQL").toString() com uma string fixa que às vezes quebra no CI. O que está errado e como corrigir no padrão do pacote?

(O projeto não está aberto nesta sessão: responda com os problemas e o código corrigido no padrão, sem pedir o repositório.)
