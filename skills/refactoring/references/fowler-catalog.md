# Índice Completo — As 61 Refatorações do Catálogo de Fowler

Referência complementar de [`../SKILL.md`](../SKILL.md) com as 61 refatorações mecânicas de Martin Fowler (*Refactoring*, 2ª ed.), adaptadas ao Java 25 e Spring Boot 4 do pacote.

---

## Primeiro conjunto

| Refatoração | Quando |
|---|---|
| Extract Function / Inline Function | Separar a intenção da implementação / desfazer indireção que não ajuda |
| Extract Variable / Inline Variable | Dar nome a uma expressão / remover nome que não diz mais que a expressão |
| Change Function Declaration | Renomear ou mudar parâmetros (com migração gradual se é API pública) |
| Encapsulate Variable | Antes de mexer em dado de escopo amplo: acesso por métodos |
| Rename Variable | O nome não revela a intenção (`code-style`) |
| Introduce Parameter Object | Grupo de parâmetros que anda junto vira record |
| Combine Functions into Class | Várias funções sobre os mesmos dados viram métodos de uma classe |
| Combine Functions into Transform | Derivações de um dado concentradas numa transformação (um mapper que enriquece) |
| **Split Phase** | Código que faz duas coisas em sequência (ler e calcular, calcular e formatar) |

## Encapsulamento

| Refatoração | Quando |
|---|---|
| Encapsulate Record | Estrutura de dados exposta vira classe ou record com acesso controlado |
| **Encapsulate Collection** | Getter de coleção mutável: devolva cópia imutável e ofereça `add`/`remove` (`jpa-advanced-mapping`, com a ressalva do MapStruct/Dozer) |
| Replace Primitive with Object | `String isbn`, `BigDecimal` com moeda: value object (record) |
| Replace Temp with Query | Variável calculada uma vez e usada adiante vira método de consulta |
| Extract Class / Inline Class | Classe faz duas coisas / classe não faz quase nada |
| Hide Delegate / Remove Middle Man | Esconder a cadeia de navegação / remover o delegador que só repassa |
| Substitute Algorithm | Trocar um algoritmo inteiro por um mais claro (com os mesmos testes) |

## Mover recursos

| Refatoração | Quando |
|---|---|
| Move Function / Move Field | A função ou o dado está na classe errada (inveja de recursos) |
| Move Statements into Function / to Callers | Código que sempre acompanha a chamada entra na função / o que varia por chamador sai dela |
| Replace Inline Code with Function Call | O trecho já existe como função (inclusive do JDK: `Collections.max`, `String.join`) |
| Slide Statements | Aproximar linhas relacionadas antes de extrair |
| **Split Loop** | Um laço faz duas coisas: dois laços (meça só se o volume justificar) |
| **Replace Loop with Pipeline** | Laço que filtra e transforma vira `stream()` |
| Remove Dead Code | Código sem uso, conferido também em reflexão e configuração |

## Organizar dados

| Refatoração | Quando |
|---|---|
| Split Variable | Uma variável reaproveitada para dois propósitos |
| Rename Field | O nome do campo não diz o que é (em entity, cuidado com JSON e JPQL) |
| **Replace Derived Variable with Query** | Campo que só guarda um cálculo de outros campos vira método |
| **Change Reference to Value** | Objeto pequeno sem identidade vira record imutável |
| Change Value to Reference | Muitas cópias do mesmo dado que precisam mudar juntas viram uma referência (entity) |

## Simplificar lógicas condicionais

| Refatoração | Quando |
|---|---|
| Decompose Conditional | Condição e ramos extraídos para métodos com nome |
| Consolidate Conditional Expression | Vários `if` com o mesmo resultado viram um, com nome |
| Replace Nested Conditional with Guard Clauses | `if` aninhado vira guarda de uma linha (`code-style`) |
| Replace Conditional with Polymorphism | `switch` por tipo repetido vira Strategy ou `switch` sobre `sealed` (`design-patterns`) |
| **Introduce Special Case** | `if (x == null)` espalhado vira um objeto de caso especial (`Member.UNKNOWN`, `Optional`) |
| Introduce Assertion | Explicitar uma premissa: no pacote, guarda que lança exception, não `assert` (`test-patterns`, contratos) |

## Refatorar APIs

| Refatoração | Quando |
|---|---|
| **Separate Query from Modifier** | Método que devolve valor **e** muda estado vira dois (`code-style`: consulta não muda estado) |
| Parameterize Function | Funções quase iguais que diferem num valor viram uma com parâmetro |
| **Remove Flag Argument** | `process(id, true)` vira dois métodos com nome (`renew`, `renewWithoutFee`) |
| **Preserve Whole Object** | Extrair três campos de um objeto para passar adiante: passe o objeto |
| Replace Parameter with Query / Query with Parameter | O chamado consegue obter o valor sozinho / tirar uma dependência escondida (o `Clock` vira parâmetro) |
| Remove Setting Method | Campo que não deve mudar depois da criação perde o setter (fora do mapeamento do MapStruct/Dozer) |
| Replace Constructor with Factory Function | Nome que diz a intenção (`Loan.start(...)`) ou escolha do tipo concreto |
| Replace Function with Command / Command with Function | Função complexa vira objeto (o objeto método do Beck) / comando simples volta a ser função |

## Lidar com herança

| Refatoração | Quando |
|---|---|
| Pull Up Method / Field / Constructor Body | Duplicação entre subclasses sobe para a superclasse |
| Push Down Method / Field | O que só uma subclasse usa desce para ela |
| Replace Type Code with Subclasses | Código de tipo com comportamento diferente (prefira `sealed` + records) |
| Remove Subclass / Collapse Hierarchy | Subclasse que não diferencia mais / hierarquia que não se paga |
| Extract Superclass | Duas classes com comportamento comum (antes, considere composição) |
| **Replace Subclass with Delegate** | Herança usada para variar comportamento vira composição |
| **Replace Superclass with Delegate** | A subclasse não é "um" da superclasse (herança recusada) |
