---
name: cognitive-complexity
description: Complexidade cognitiva por classe com Cognitive-Driven Development (CDD) — pontos de complexidade intrínseca (ICP) combinados pelo time num cdd.json versionado, limite por classe de produção e de teste, contagem auditável com arquivo:linha, o que fica de fora no layout flat-by-layer, comparação com a base do PR, sugestão de extração que de fato reduz os pontos e calibração do limite. Use quando pedirem para medir a legibilidade, achar classes grandes ou difíceis de entender, revisar código de um projeto com cdd.json ou definir um teto de complexidade para o time. Não use para complexidade ciclomática do Sonar/PMD nem para desempenho (jvm-performance).
---

Antes de aplicar, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (o layout que define o que entra na contagem). Para fazer a extração com segurança: [`../refactoring/SKILL.md`](../refactoring/SKILL.md). Para escolher para onde a regra vai: [`../solid/SKILL.md`](../solid/SKILL.md) e [`../design-patterns/SKILL.md`](../design-patterns/SKILL.md).

# Complexidade cognitiva (CDD)

**Cognitive-Driven Development** parte da Teoria da Carga Cognitiva: quem lê o código só consegue manter poucas coisas na cabeça ao mesmo tempo. Cada construção que exige atenção (um desvio, um loop, um `catch`, um tipo do projeto que é preciso conhecer) é um **ponto de complexidade intrínseca (ICP)**. O time combina **o que conta** e **o teto por classe**; a classe que passa do teto pede extração.

A diferença para uma métrica de ferramenta é que **a regra é do time e fica no repositório**: a contagem é auditável (cada ponto tem `arquivo:linha`) e a discussão deixa de ser "achei difícil de ler" para virar "esta classe tem 15 pontos e o combinado é 12".

| | CDD (esta skill) | Complexidade ciclomática / cognitiva do Sonar |
|---|---|---|
| Unidade | Classe inteira | Método |
| Acoplamento | Conta cada tipo do projeto que a classe conhece | Não conta |
| Lambdas | Contam (regra do time) | Só o que há dentro delas |
| Quem define | O time, no `cdd.json` | A ferramenta |

As duas convivem: o Sonar aponta o método emaranhado, o CDD aponta a classe que acumulou responsabilidade.

---

## 1. O `cdd.json` — sem ele não há contagem

A contagem **só usa as regras escritas** no `cdd.json`. Sem o arquivo, não invente pontuação: diga que não há regra combinada e ofereça o modelo de [`templates/cdd.json`](templates/cdd.json), que já vem calibrado para o layout do pacote. Criar o arquivo no projeto é decisão do time: mostre o conteúdo e **peça aprovação** antes de gravar.

**Qual vale:** o `cdd.json` mais próximo, subindo a árvore a partir do arquivo revisado até a raiz do repositório (um monorepo pode ter um por serviço). Se o usuário indicar outro caminho, vale esse.

| Campo | Obrigatório | Significado |
|---|---|---|
| `unit` | sim | `"class"`: cada tipo de nível superior com todos os seus membros (tipos aninhados, anônimos e lambdas contam na classe que os contém). `"file"`: cada arquivo `.java`. |
| `limit` | sim | Teto de pontos por unidade de produção (inteiro ≥ 1). |
| `testLimit` | não | Teto para unidades de teste. Sem ele, vale `limit`. Exige `tests`. |
| `tests` | condicional | Globs (relativos ao `cdd.json`, separador `/`, `**` = qualquer profundidade) que marcam arquivos de teste. Sem ele, tudo é produção. |
| `ignore` | não | Globs fora da contagem. Se um arquivo casa com `ignore` e com `tests`, é ignorado. |
| `ignoreMembers` | não | Nomes de métodos cujo corpo não conta (no pacote: `equals`, `hashCode` e `toString`, que seguem o molde de `code-style`). |
| `rules` | sim | Lista de regras: `id` (kebab-case, único), `points` (inteiro ≥ 0), `counts` (o texto que diz o que casa e o que fica de fora) e, opcional, `appliesTo`: `"main"`, `"test"` ou `"all"` (padrão). `appliesTo` diferente de `"all"` exige `tests`. |

**Arquivo inválido** (campo obrigatório ausente, campo desconhecido, `id` repetido, `testLimit` ou `appliesTo` sem `tests`): pare e mostre o erro. Contar com uma regra quebrada tira a auditabilidade, que é o objetivo.

### O modelo do pacote e por que o limite é 12

O artigo que definiu o CDD sugere **7** para aplicações web com times de experiência mista. No layout flat-by-layer, porém, todo service conhece entity, DTO, repository e duas exceptions só para existir. O CRUD de referência (`code-organization`, `spring-data-jpa`), contado com as regras do modelo:

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

    public List<BookDTO> findAll() {
        return mapper.toDtoList(repository.findAll());
    }

    public BookDTO findById(Long id) {
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        return mapper.toDto(entity);
    }

    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var entity = mapper.toEntity(book);
        return mapper.toDto(repository.save(entity));
    }

    public BookDTO update(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var entity = repository.findById(book.getId())
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        entity.setTitle(book.getTitle());
        entity.setPrice(book.getPrice());
        return mapper.toDto(repository.save(entity));
    }

    public void delete(Long id) {
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        repository.delete(entity);
    }
}
```

| Regra | Ocorrências | Pontos |
|---|---|---|
| `project-type` | `BookRepository`, `BookMapper`, `BookDTO`, `ResourceNotFoundException`, `RequiredObjectIsNullException` | 5 |
| `function-argument` | os três `() -> new ResourceNotFoundException(...)` | 3 |
| `branch` | os dois `if (book == null)` | 2 |
| **Total** | | **10** |

`Logger`/`LoggerFactory` são de biblioteca e `var` não nomeia o tipo (`var entity = mapper.toEntity(book)` não precisa citar `Book` explicitamente): nada disso conta. Com o limite em **12**, o CRUD passa com folga de 2 pontos, e uma regra de negócio de verdade (um `if/else` e mais um tipo) já cruza o teto. Esse é o sinal que interessa: o service deixou de ser CRUD e a regra nova merece um lugar próprio. Testes referenciam mais tipos (a classe testada, os dublês, os builders), por isso o modelo começa com `testLimit` 15. **Os dois números são ponto de partida.** Calibre no seu código (seção 6).

O modelo ignora `config/`, `controllers/docs/`, `data/dto/`, `mapper/` e `Startup.java`: são declaração e cola, e contar suas annotations e getters só gera ruído. `model/` **não** é ignorado: entity anêmica soma quase zero, e entity que ganhou comportamento precisa ser medida.

---

## 2. Como contar

1. **A regra manda.** Conta o que o texto de `counts` descreve, e só isso. Construção sem regra **não pontua**, por mais complexa que pareça: vai para "Sem regra" no relatório, como pergunta ao time.
2. **Conte o que está escrito, não a intenção.** `if (book == null) throw ...` é um `if` e conta em `branch`, mesmo sendo uma guarda.
3. **Cada regra conta por conta própria.** `if (a && b)` soma 1 em `branch` e 1 em `logical-operator`.
4. **Toda a classe conta:** métodos, construtores, inicializadores, lambdas, classes anônimas e tipos aninhados. Não contam comentários, literais de texto, imports, annotations (salvo regra) e o corpo dos métodos em `ignoreMembers`.
5. **Na dúvida, não conte.** Registre o trecho em "Sem regra / dúvidas" com a pergunta. Nunca estique o texto de uma regra.
6. **A contagem é da classe, não do grafo.** Os pontos de `BookRepository` não somam no `BookService`; o que soma é o fato de o service **conhecer** `BookRepository` (`project-type`).
7. **Produção ou teste** pelo arquivo onde a classe é declarada, contra os globs de `tests`. Uma regra com `appliesTo: "main"` não pontua em teste e vice-versa.

## 3. Escopo

- O que o usuário indicar (arquivos, pacote, módulo). Sem indicação, as classes `.java` alteradas na branch: `git diff --name-only <base>...HEAD -- '*.java'`.
- Com `unit: "class"`, a classe tocada pelo diff é contada **inteira**: a carga cognitiva é de quem lê a classe, não de quem lê o diff.
- Respeite `ignore`. Arquivo sem `cdd.json` aplicável fica de fora e aparece em "Não contados".

## 4. Passo a passo (com o contador determinístico)

Use o script [`scripts/cdd_counter.py`](scripts/cdd_counter.py) (somente stdlib do Python 3) para obter a contagem exata e auditável sem somar pontos de cabeça:
```bash
# contar classes alteradas em relação à main (plugin ou instalação portável):
python "${CLAUDE_PLUGIN_ROOT}/skills/cognitive-complexity/scripts/cdd_counter.py" --project . --base main
# ou em .agents/skills:
python .agents/skills/cognitive-complexity/scripts/cdd_counter.py src/main/java --project .
```
Se o Python não estiver disponível no ambiente, siga o cálculo manual abaixo (e declare que a contagem foi manual):

1. Ache e valide o `cdd.json` de cada arquivo do escopo.
2. Separe as unidades e marque produção/teste.
3. Percorra cada unidade anotando **cada ocorrência** com `arquivo:linha` (em `project-type`, a linha da primeira referência ao tipo).
4. Some `points × ocorrências` por regra e compare com o limite: **acima** → violação; **igual** → no fio; abaixo → não aparece no relatório.
5. **Num PR, compare com a base:** conte também a versão da base (`git show <base>:<arquivo>` ou `--base <branch>`). "Este PR levou a classe de 9 para 14" é o achado; "a classe já tinha 14 e continua com 14" é pré-existente.
6. Para cada violação, confira os trechos apontados pelo script, destaque os **2–3 pontos de maior peso** e proponha uma extração concreta (seção 5).

### Relatório

```
BookLoanService — src/main/java/br/com/edimilsonldutra/services/BookLoanService.java
CDD: 15 / 12 (produção) — VIOLAÇÃO · base: 10 (+5 neste PR)
  - project-type: 7 × 1 = 7
  - branch: 4 × 1 = 4
  - logical-operator: 2 × 1 = 2
  - function-argument: 2 × 1 = 2
Pontos de maior peso:
  - BookLoanService.java:58-71 — branch ×3, logical-operator ×2 (regra de renovação)
  - BookLoanService.java:12-19 — project-type: Member, Loan, LoanPolicy (só usados na renovação)
Extração: mover a decisão de renovação para Loan.canRenew(LocalDate) (ou para um LoanRenewalPolicy),
  o que tira 5 pontos daqui e acrescenta 1 (o tipo novo) → 11.
```

Depois das unidades, quando houver:

```
Sem regra / dúvidas (cdd.json da raiz):
  - switch com pattern matching (case Book b when ...) — 1 ocorrência, LoanService.java:40: o "when" conta em branch?
Não contados:
  - legacy/ImportJob.java — sem cdd.json aplicável
```

Sem violação: **"CDD: nenhuma classe acima do limite."** (as classes no fio continuam listadas).

**Na revisão de código (`code-reviewer`):** classe que o PR leva acima do limite, ou que já estava acima e o PR aumenta, é 🟠 **Major** (descumpre um combinado do time: corrigir ou justificar). Classe no fio é 🔵 **Nit**. Classe acima do limite que o PR não piorou é 🟣 **Pré-existente**.

---

## 5. Extrair de um jeito que reduz os pontos

A extração só vale se **leva os pontos para outra classe**. Mover um trecho para um método `private` da mesma classe não muda o total, e trocar uma lambda por method reference também não (as duas contam em `function-argument`). A classe nova custa **1 ponto** (`project-type`) para quem a usa, então extraia blocos que pesem bem mais que isso.

| Onde está o peso | Para onde vai | Skill |
|---|---|---|
| Decisão sobre o estado de uma entity (`if (loan.getRenewals() < 2 && ...)`) | Método no dono do dado (`loan.canRenew(today)`) ou policy dedicada | `solid` (coesão), `ddd-hexagonal` |
| O mesmo `if/switch` por tipo, que cresce a cada variação | Estratégias como beans | `design-patterns` |
| `try/catch` traduzindo exceptions em várias operações | `@ControllerAdvice` ou um adapter que já devolve exception de domínio | `exception-handling` |
| Muitos tipos do projeto usados por uma operação só | Um service novo para essa operação (responsabilidade separada) | `solid` (S) |
| Conversões e montagem de DTO espalhadas | O `mapper` | `spring-data-jpa` |
| Filtros dinâmicos montados com `if` | Specification ou query no repository | `design-patterns`, `spring-data-jpa` |

Faça a extração como refatoração (`refactoring`): testes verdes antes, passos pequenos, comportamento igual, e recontagem no fim para mostrar o antes e o depois.

**Não maquie a métrica.** Juntar dois tipos num genérico, espremer um `if` num ternário (a regra `ternary` conta igual) ou ignorar uma pasta para passar no limite esconde o problema. Mudar o `cdd.json` é decisão do time, registrada no PR que muda o arquivo, nunca no mesmo PR que precisava dela para passar.

## 6. Calibrar o limite

1. Conte o repositório inteiro e ordene as classes pelo total.
2. Olhe as primeiras da lista com o time: são mesmo as mais difíceis de ler? Se não, ajuste as regras (pontos, o que conta) antes de mexer no limite.
3. Escolha o limite em que **as classes que o time considera difíceis passam dele e as que o time considera boas ficam abaixo**. Em código legado, comece acima do maior valor tolerado e desça por etapas (como a catraca de cobertura em `test-coverage`).
4. Uma mudança no `cdd.json` vai num PR próprio, com o motivo na descrição. Se a regra virar política de arquitetura, registre num ADR (`architect`).

## 7. Quando não usar

- **Código gerado**, migrations, configuração e DTOs: não são lidos como lógica (por isso o modelo os ignora).
- **Como gate automático sem calibrar:** um limite arbitrário bloqueia PR bom e ensina o time a contornar a métrica.
- **Como substituto de revisão:** uma classe com poucos pontos ainda pode ter nomes ruins, regra no lugar errado ou bug. O CDD mede carga, não corretude.

---

## Referências

- Souza, A. L. O. T.; Pinto, V. H. S. C. *Toward a Definition of Cognitive-Driven Development*. ICSME 2020.
- Pereira, J. H. A.; Souza, A. L. O. T.; Pinto, V. H. S. C. *Cognitive Load Analyzer: A Support Tool for Cognitive-Driven Development*. SBES 2021.

## Regras principais

- **Sem `cdd.json`, sem contagem:** ofereça o modelo de `templates/cdd.json` e peça aprovação para gravá-lo; nunca conte com regras inventadas.
- **Só pontua o que uma regra descreve;** o resto vai para "Sem regra / dúvidas". Na dúvida, não conte.
- **Unidade = classe inteira**, com lambdas, anônimas e aninhadas; imports, comentários, literais e `equals`/`hashCode`/`toString` não contam.
- **Cada ponto com `arquivo:linha`;** acima do limite é violação, igual é "no fio".
- **Num PR, compare com a base:** subir acima do limite ou piorar uma classe acima dele é 🟠; já estar acima é 🟣.
- **Extração leva os pontos para outra classe** (método privado na mesma classe não conta); recontagem antes/depois; nada de maquiar a métrica.
- **Limite 12 / teste 15 no modelo do pacote** (o CRUD de referência soma 10); calibre com o time e mude o `cdd.json` em PR próprio.
- **Sem Lombok** — deliberado.
