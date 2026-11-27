# Changelog

Mudanças notáveis do plugin `squads`. A versão é a de `.claude-plugin/plugin.json`; quem já instalou só recebe uma mudança quando ela sobe.

## 2.22.0 — 2026-11-26

### Nova skill: DDD estratégico
- Nova skill `strategic-ddd` (fundamentada em Vlad Khononov, *Learning Domain-Driven Design*): identificação de subdomínios (Core, Supporting, Generic) por vantagem competitiva, complexidade e volatilidade; linguagem ubíqua; bounded contexts × subdomínios; context map com as 7 relações (Partnership, Shared Kernel, Customer–Supplier, Conformist, ACL, Open-Host Service, Separate Ways) e diagrama Mermaid; EventStorming em 10 passos; árvore de decisão tática (Transaction Script, Active Record, Domain Model, event sourcing → camadas, ports & adapters, CQRS → pirâmide invertida, diamante, pirâmide); evolução das decisões (mudança de tipo de subdomínio, migração entre padrões com evento de migração, mudanças de organização).
- `ddd-hexagonal`: a seção estratégica passa para `strategic-ddd`; fica um resumo do que chega ao código.
- `saga-pattern`: saga × process manager. `service-communication`: tradução com estado na ACL. `test-patterns`: forma da suíte pela lógica de negócio. `requirements-engineering`: EventStorming entre as técnicas de elicitação.
- Encadeada em `microservices`, `monolith-decomposition`, `guide`, `README.md`, `docs/guide.md`, `architect`, `orchestrator`, `tech-lead` e `code-reviewer`.
- Eval `subdominios-e-context-map` (gatilho de `strategic-ddd`, sem disparar `microservices`). Ainda não executado.
- 99 skills.

## 2.21.0 — 2026-11-26

### Padrões de implementação (Kent Beck)
- `code-style`: seção "Código que comunica" (valores comunicação, simplicidade e flexibilidade; princípios consequências locais, minimizar repetição, lógica e dados juntos, simetria, expressão declarativa e taxa de mudança), nomes que revelam intenção e método composto; seção "Coleções" (interface pela semântica, vazia em vez de `null`, imutáveis, cópia de segurança respeitando o Dozer, parâmetro coletor); referências.
- `refactoring`: Replace Method with Method Object e nome que não revela intenção no catálogo de smells.
- `code-reviewer`: achados de nome sem intenção, mistura de níveis de abstração, coleção `null` e `List` no lugar de `Set`.
- Eval `codigo-que-comunica` (gatilho de `code-style`/`refactoring`, sem disparar `cognitive-complexity`). Ainda não executado.

## 2.20.0 — 2026-11-26

### Design orientado a objetos simples (Aniche)
- `solid`: tipos próprios nas fronteiras (sem classes de SDK em services e domínio); pré-condição × regra de validação de negócio como componente próprio; estado com regra muda só por método de negócio da entity, mantendo os setters do flat-by-layer para o Dozer (sem setter e com coleção imutável só em contexto DDD); quando **criar** uma abstração e o que a torna boa; novas linhas na tabela de revisão.
- `design-patterns`: regra generalizada, com a regra no código e os valores em dado (`ExtendedLoanPromotion`), e quando usar Strategy em vez dela.
- `ddd-hexagonal`: usar a infraestrutura por inteiro atrás de operações com nome de negócio, contrapeso ao "banco é detalhe".
- `modular-monolith`: módulos profundos (interface pequena sobre funcionalidade complexa), compatibilidade, pontos de extensão, dono e acoplamento acidental documentado.
- `exception-handling`: exceptions de infraestrutura traduzidas no adapter para exceptions de domínio.
- `code-reviewer`: achados de setter de estado chamado pelo service, tipo de SDK circulando e regra repetida com valores diferentes.
- Eval `design-simples` (gatilho de `solid`/`design-patterns`, sem disparar `ddd-hexagonal`). Ainda não executado.

## 2.19.0 — 2026-11-26

### Microsserviços orientados a eventos (Bellemare)
- `messaging`: princípio do escritor único, as três formas de evento (sem chave, com chave, de entidade) e regras de desenho (um tipo por stream, propósito único sem campo `action`, tipos estreitos, evento não é semáforo, envolver os consumidores).
- `kafka`: tópico compactado para eventos de entidade com tombstone; estado materializado no consumidor (`@Payload(required = false)`, upsert por versão, reconstrução com grupo novo); grupos de consumidores, reprocessamento lado a lado, reset de offset e quebra de schema no deploy; governança de tópicos (dono, metadados, ACL, cotas).
- `monolith-decomposition`: liberar dados do legado como eventos (por consulta, CDC nas tabelas, outbox) e seus riscos; `transactional-outbox`: CDC na outbox, não nas tabelas de domínio.
- `code-reviewer`: achados de escritor único, tópico misturado, campo `action`, evento-semáforo, evento de entidade sem chave ou sem compactação, cópia local sem versão e CDC como contrato.
- Eval `eventos-de-entidade` (gatilho de `kafka`/`messaging`, sem disparar `cqrs-event-sourcing`). Ainda não executado.
- Processamento de streams com estado (janelas, tempo do evento, *state stores*) ficou fora desta versão.

## 2.18.0 — 2026-11-26

### Padrões de projeto: o catálogo GoF completo
- `design-patterns` ampliada com base em Gamma, Helm, Johnson e Vlissides, *Padrões de Projeto* (GoF): princípios do catálogo (programe para a interface, composição antes de herança, encapsule o que varia), tabela de causas de reprojeto com os padrões que as evitam e como escolher; mapa dos 23 padrões no Java 25 + Spring (usado, o Spring faz, o Java faz, raro); Factory Method × Abstract Factory; seções novas de Prototype (cópia explícita, nunca `clone()`), Composite (regras `AllOf`/`AnyOf`), Bridge e Flyweight, Command (record + handler), Mediator, Visitor como `switch` exaustivo sobre `sealed`, e Iterator, Memento e Interpreter (SpEL só com `SimpleEvaluationContext`); anti-padrões e testes correspondentes; referências.
- `refactoring` ganha a linha "causa de reprojeto" no catálogo de smells; `code-reviewer` ganha achados de `clone()`, cadeia de `instanceof`, Visitor manual e barramento de comandos sem motivo. `guide` e `docs/guide.md` atualizados.
- Eval `padroes-gof` (gatilho de `design-patterns`, sem disparar `refactoring`). Ainda não executado.

## 2.17.0 — 2026-11-26

### Novas skills: Concorrência e Mapeamento JPA avançado
- Nova skill `concurrency`: bean singleton thread-safe (campo mutável, `SimpleDateFormat`/`HashMap` compartilhados), `ConcurrentHashMap` com `computeIfAbsent`/`merge`, `AtomicLong` × `LongAdder`, locks (`synchronized`, `ReentrantLock` com `tryLock`, `ReadWriteLock`, ordem de aquisição, `InterruptedException`) e por que lock em memória não vale com várias réplicas; `@Async` com `spring.task.execution.*` (fila e concorrência limitadas, rejeição, shutdown, propagação de contexto, executor por tipo de trabalho, exceptions de `@Async void`); `CompletableFuture` e scatter-gather com executor explícito, `orTimeout`/`completeOnTimeout` e `CompletionException`; `Semaphore` com virtual threads; parallel streams; produtor-consumidor em memória × broker; `@Scheduled`; testes de corrida; checklist.
- Nova skill `jpa-advanced-mapping`: auditoria do Spring Data (`AuditorAware`, `DateTimeProvider` com `Clock`) e callbacks; `@Embeddable` record e `AttributeConverter`; herança (`@MappedSuperclass`, `SINGLE_TABLE`, `JOINED`, `TABLE_PER_CLASS`) × composição; `@ElementCollection`, `@OrderBy`/`@OrderColumn`; bidirecional sincronizado, cascade e `orphanRemoval`; `persist` × `merge`, `getReferenceById`; escrita em lote (`IDENTITY` × `SEQUENCE` com `allocationSize`, `flush`/`clear`); lock pessimista com timeout; `@SoftDelete`; cache de segundo nível.
- Fontes: documentação do JDK 25, Spring Framework 7, Spring Boot 4, Hibernate 7 e Jakarta Persistence 3.2; properties e anotações conferidas nos jars do Maven Central (Spring Boot 4.2.0, Spring Framework 7.1.0, Spring Data JPA 4.2.0, Hibernate 7.4.17). Os livros de Jay Wang (*Java Concurrency and Parallelism*) e Nisha Kurur (*Mastering JPA*) foram avaliados e não usados; *Java Coding Problems* (Anghel Leonard) entrou só como apoio em virtual threads.
- Encadeadas em `java-modern-features`, `jvm-performance`, `spring-data-jpa`, `data-modeling`, `test-patterns`, `guide`, `README.md`, `docs/guide.md`, `orchestrator`, `tech-lead`, `developer`, `qa` e `code-reviewer`.
- Evals `estado-em-bean` (gatilho de `concurrency`, sem disparar `jvm-performance`) e `auditoria-e-lote` (gatilho de `jpa-advanced-mapping`, sem disparar `data-modeling`). Ainda não executados.
- 98 skills.

## 2.16.0 — 2026-11-26

### Nova skill: Desenho de API
- Nova skill `api-design` (fundamentada em Zimmermann, Stocker, Lübke, Zdun e Pautasso, *Patterns for API Design*): visibilidade (pública, de parceiros, interna) e tipo de integração (frontend × backend) como decisão; papéis de endpoint (recurso de processamento, dado operacional, mestre e de referência, link lookup, transferência de dados); responsabilidades de operação (criação, consulta, transição de estado como ação com nome de negócio, função de cálculo); estrutura de mensagens e papéis dos elementos (dado, metadado, id, link, contexto em header); entidade embutida × link, visões nomeadas × `?fields=`, request bundle; requisição condicional com `ShallowEtagHeaderFilter` (304) e `@Version` + `If-Match` (412/428); garantias de ciclo de vida (prévia experimental, duas em produção, vida útil limitada, obsolescência agressiva, vida útil eterna) e versionamento semântico do contrato; checklist de revisão e anti-patterns.
- Encadeada em `api-versioning`, `technical-product-management`, `code-organization`, `guide`, `README.md`, `docs/guide.md`, `orchestrator`, `architect`, `tech-lead`, `developer`, `qa` e `code-reviewer`.
- Eval `desenho-de-api` (gatilho de `api-design`, sem disparar `hateoas`). Ainda não executado.
- 96 skills.

## 2.15.0 — 2026-11-26

### Arquitetura Limpa (Robert C. Martin)
- `code-organization`: trade-off do flat-by-layer frente a empacotar por recurso, por portas e adaptadores ou por componente (arquitetura que "grita" o domínio, tudo `public`, regra das camadas só por revisão ou ArchUnit), sinais para migrar para módulos e `Startup`/`config/` como componente Main.
- `modular-monolith`: nova seção 8, coesão e acoplamento entre módulos (fechamento comum, reúso comum, reúso e versão, sem ciclos, dependências na direção da estabilidade, módulo estável expõe abstração, instabilidade como diagnóstico).
- `ddd-hexagonal`: limites parciais (pular o último passo, limite unidimensional, fachada), mapeamento dos círculos da Arquitetura Limpa para `domain`/`application`/adapters, banco, web e framework como detalhes, dados simples cruzando a fronteira e dois anti-patterns novos.
- `test-patterns`: Humble Object e API de teste. `microservices`: serviços não são arquitetura (a feature transversal). `prioritization`: os dois valores do software e a matriz de Eisenhower. `solid`: referências.
- `architect` e `code-reviewer`: estabilidade das dependências entre módulos, limite parcial, detalhe cruzando a fronteira do use case e regra de negócio em `@Configuration`. `guide` e `docs/guide.md` atualizados.
- Ideias reescritas com os exemplos e o vocabulário do pacote; nenhum trecho do livro copiado.

## 2.14.0 — 2026-11-26

### Desenho de casos de teste (Aniche, *Effective Software Testing*)
- `test-patterns`, seção 6: roteiro de 7 passos do teste a partir da especificação (entender → explorar → partições → limites → casos → automatizar → ampliar), pontos on/off/in/out, critério de fronteira de laço (0, 1 e N iterações), heurísticas para quando as combinações explodem e "especificação primeiro, cobertura depois". Seção 14: contratos (pré e pós-condições, invariantes, Liskov) e testabilidade como design (domínio × infraestrutura, controlabilidade, observabilidade de métodos `void`, métodos privados, estáticos). Checklist da seção 15, regras principais e nova seção de referências.
- `spring-data-jpa`: "Que casos escrever para uma query" (MC/DC no `WHERE`/`JOIN`/`HAVING`, `NULL` como terceiro valor, nenhuma linha, duplicata por `JOIN 1:N`, grupos, empate na ordenação, isolamento entre donos, dados mínimos e asserts sobre as linhas exatas).
- `test-coverage`: cobertura lida depois dos casos por especificação; ramo descoberto é pergunta, não alvo.
- `qa`: roteiro de geração de casos e técnicas de laço, contrato e query. `code-reviewer`: achados de laço sem zero iterações, query sem caso de `NULL`/duplicata e código pouco testável. `guide` e `docs/guide.md` atualizados.
- Técnicas reescritas com os exemplos do pacote; nenhum trecho do livro copiado.

## 2.13.0 — 2026-11-26

### Nova skill: Engenharia de Requisitos
- Nova skill `requirements-engineering` (fundamentada em Vazquez & Simões, *Engenharia de Requisitos: software orientado ao negócio*): ciclo em 3 Marcos (Necessidade, Consenso de Escopo, Detalhamento 80/20 e nível de detalhe por horizonte); taxonomia completa (`RNeg`, `RPI`, `RF` em 3 níveis, `RN`, `RNF` via ISO/IEC 25010 e FURPS+, `RT` de Transição, `RI` Inversos, `REST` de negócio × técnicas e `PREM` Premissas); Mapa de Partes Interessadas com autoridade; elicitação em 4 passos (Preparar → Executar → Documentar entendimento → Confirmar) e 5 técnicas com Glossário do domínio; modelagem ambiental e análise (Diagrama de Contexto Mermaid, processos As-Is/To-Be, decomposição funcional, modelagem de domínio, Casos de Uso × Histórias INVEST+CCC, prototipação); Verificação pelos 8 critérios de qualidade × Validação; Controle de Questões, Gestão de Mudanças e rastreabilidade bidirecional (pré e pós).
- `prd-writing` enriquecida com origem (`RNeg`/`RPI`), regras de negócio (`RN-n`), requisitos de transição (`RT-n`), separação Restrições × Premissas, Controle de questões em aberto e verificação pelos 8 critérios de qualidade antes da validação. Encadeada também em `product-discovery`, `user-stories`, `backlog-refinement`, `design-docs` (que também referencia `data-modeling`), `guide`, `README.md`, `docs/guide.md`, `product-manager`, `orchestrator`, `architect`, `tech-lead`, `qa` e `code-reviewer`.
- Eval `engenharia-de-requisitos` (gatilho de `requirements-engineering`, sem disparar `product-discovery`). Ainda não executado.
- 95 skills.

## 2.12.0 — 2026-11-26

### Nova skill: Modelagem de dados e consistência
- Nova skill `data-modeling`: escolha de banco e consistência com Teorema CAP, PACELC (`PC/EC`, `PA/EL`, `PA/EC`, `PC/EL`) e ACID × BASE; níveis de isolamento SQL (`READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`), anomalias (lost update, write skew, phantom), MVCC e locking (`@Version` × `SELECT FOR UPDATE` / `SKIP LOCKED`); modelagem conceitual/lógica/física (`erDiagram`), normalização (1FN–3FN/BCNF) × desnormalização controlada, chaves (`BIGINT IDENTITY`, `UUIDv7`, sem `UUIDv4` nem PII como PK), constraints no banco, estados explícitos × soft delete (impacto em `UNIQUE` e LGPD), JSONB, índices compostos e parciais (`EXPLAIN`), particionamento × sharding e read replicas. Integrada em `spring-data-jpa`, `flyway-migrations`, `aws-dynamodb`, `aws-keyspaces`, `guide`, `README.md`, `docs/guide.md`, `orchestrator`, `architect`, `tech-lead`, `developer`, `qa` e `code-reviewer`.
- Eval `modelagem-cap-pacelc` (gatilho de `data-modeling`, sem disparar `spring-data-jpa`). Ainda não executado.
- 94 skills.

## 2.11.0 — 2026-11-26

### Nova skill: Redis e Valkey
- Nova skill `redis`: uso direto de Redis e Valkey em produção com Spring Boot 4 / Spring Data Redis — decisão Redis × banco relacional × broker, `StringRedisTemplate`/`RedisTemplate` com Jackson 3 (sem serialização Java), TTL por cache com `RedisCacheManagerBuilderCustomizer`, estruturas de dados, scripts Lua atômicos (rate limiting distribuído e locks distribuídos com liberação segura conferindo dono), revogação de JWT e sessões, Redis Streams × Pub/Sub, política de memória/eviction com isolamento entre cache e estado crítico, `SCAN` (proibindo `KEYS *`), Lettuce, Sentinel × Cluster com hash tags, Amazon ElastiCache (Serverless e Multi-AZ) e testes com Testcontainers. Integrada em `caching`, `localstack`, `guide`, `README.md`, `docs/guide.md`, `orchestrator`, `architect`, `tech-lead`, `developer`, `qa` e `code-reviewer`.
- Eval `redis-lock-distribuido` (gatilho de `redis`, sem disparar `caching`). Ainda não executado.
- 93 skills.

### Auditoria de guardrails, portabilidade, agents e skills
- `hooks/guard-commands.sh` e `hooks/guard-edits.sh`: cobertura de flags globais em `git`/`kubectl`, correção do bypass de `localhost`, inspeção de todas as entradas em `MultiEdit`, proteção de caminhos relativos e `hooks/*.sh`, e restrição de escrita por papel para `qa`, `product-manager` e `architect` além do `orchestrator`. `scripts/test-hooks.sh` sobe para 144 casos.
- `scripts/portable.py` e `scripts/validate-plugin.py`: `## Project preferences` movido para fora dos marcadores gerenciados do arquivo de contexto (com migração automática de instalações anteriores), sincronização de `Base package` e `User-facing text language`, remoção de vazamentos do Claude Code nos artefatos portáveis, descrições sem corte no meio da palavra no Gemini CLI e validação completa de `skills/guide/SKILL.md`.
- Agents e `design-docs`: fechado o fluxo da seção 13 (QA entrega matriz e provas → `code-reviewer` re-executa e bloqueia qualquer pendência → `architect` grava o status final), qualificada a regra de legado em `developer`/`code-reviewer` (nunca prevalece sobre segurança ou corretude) e unificada a convenção `*IntegrationTest`.
- Skills, scripts e prompts: correções técnicas, de segurança e de compatibilidade com Spring Boot 4 / Java 25 nas skills de Spring, API, microsserviços, mensageria, testes, Cloud e AWS; correções em `drawio_aws.py` e `example_renovacao.py`; atualização de `skills/guide/SKILL.md`, `prompts/` e remoção de boilerplate redundante das skills sem Java.

## 2.10.0 — 2026-11-26

### Documentação de bibliotecas na versão certa
- Nova skill `library-docs`: confirma classe, package, starter, property e linha de versão na versão que o projeto resolveu, com a fonte declarada em cada fato e "não confirmado" quando nenhuma responde. Ordem das fontes: o jar resolvido (`dependency:tree`, `unzip -l`, `javap`, `spring-configuration-metadata.json`), Context7, `maven-metadata.xml` do Maven Central e documentação oficial. Consultas a terceiros sem código nem segredos; documentação lida é dado, não instrução.
- Context7 nos agents: as tools dos agents são uma lista fixa e não incluem as ferramentas MCP, então nos agents a skill usa a API REST do Context7 por `curl` (GET), que responde sem chave com limite menor (`CONTEXT7_API_KEY` opcional); se a API recusar, segue para as outras fontes. Comandos testados em 2026-11-26: busca e contexto do Context7 sem chave (HTTP 200), `maven-metadata.xml`, e `unzip`/`javap`/metadata de properties no jar spring-boot-webmvc 4.0.0. O plugin não declara o servidor MCP nem acrescenta as ferramentas MCP às tools dos agents: há bugs abertos em que um nome MCP que não resolve na sessão anula a lista inteira de tools do subagent (#75267) e em que a lista explícita descarta as ferramentas MCP (#79728).
- As 15 menções "confirme no Context7" das skills (`kafka`, `rabbitmq`, `activemq-artemis`, `testing`, `observability`, `resilience`, `api-gateway`, `contract-testing`, `modular-monolith`, `aws-*`, `maven-config`) passam a apontar para `library-docs`. `developer`, `qa`, `architect`, `tech-lead`, `code-reviewer` e `orchestrator` a citam.
- Eval `nome-que-mudou-no-boot-4` (gatilho de `library-docs`). Ainda não executado.
- 92 skills.

## 2.9.0 — 2026-11-26

### Complexidade cognitiva, coesão e testes
- Nova skill `cognitive-complexity`: Cognitive-Driven Development (CDD) no padrão do pacote. O time combina num `cdd.json` versionado o que conta como ponto (desvio, `case`, ternário, loop, `try`/`catch`/`finally`, operador lógico, tipo do projeto, função como argumento) e o teto por classe; a contagem sai com `arquivo:linha`, comparada com a base do PR, e cada violação vem com uma extração que tira os pontos da classe. O modelo `templates/cdd.json` ignora `config/`, `controllers/docs/`, `data/dto/`, `mapper/` e `Startup.java` e começa com limite 12 (teste 15), calibrado no CRUD de referência, que soma 10.
- `solid`: seção "Coesão: onde mora a regra" (tell don't ask, Lei de Demeter contada por níveis, inveja de funcionalidade sobre campos e coleções de outro objeto) com severidade conforme o layout: 🟡 no flat-by-layer, 🟠 quando a regra se repete ou com DDD decidido; leitura para reexpor não é achado.
- `test-patterns`: dublê só na fronteira (entity e colaborador interno sem I/O reais; `@WebMvcTest` é a exceção), sem matcher coringa (`any()`) onde o teste conhece o valor, por que testar o limite e não o meio da faixa, e MC/DC em condições compostas com exemplo parametrizado.
- `code-reviewer`: gatilho de `cognitive-complexity` quando o repositório tem `cdd.json` (🟠 classe que o PR leva acima do limite ou piora; 🔵 no fio; 🟣 já acima), achados de coesão e de testes (matcher coringa, entity mockada, limite sem os dois lados, condição composta sem MC/DC). `qa`, `developer` e `tech-lead` passam a usar as mesmas regras.
- Eval `classe-dificil-de-ler` (gatilho de `cognitive-complexity`). Ainda não executado: rode a suíte antes de confiar nele.
- 91 skills.

## 2.8.0 — 2026-11-11

### Orquestrador: ledger em arquivo
- `orchestrator` ganha `Write` e grava o ledger da entrega em `docs/delivery/<feature>.md` (pipeline com 2+ delegações) ao mostrar o pipeline, a cada passo concluído, em cada gate e no relatório final. A entrega passa a sobreviver ao fim da sessão, ao contexto esgotado e à troca de modelo ou de ferramenta: basta pedir para retomar pelo arquivo. Aprovações ficam como citação literal e não valem numa sessão nova. Se a gravação falhar, ele mostra o bloco `Retomada` como antes.
- Ao começar, o `orchestrator` procura em `docs/delivery/` uma entrega `em andamento` para o mesmo pedido e retoma por ela, conferindo artefatos e `git` antes.
- `hooks/guard-edits.sh`: quando o Claude Code informa `agent_type` do orchestrator, pede confirmação para qualquer gravação fora de `docs/delivery/*.md`. `scripts/test-hooks.sh` ganha 7 casos.
- `scripts/validate-plugin.py`: o orchestrator pode declarar só `Write` (nunca `Edit`/`MultiEdit`) e precisa restringir a gravação a `docs/delivery/`.
- `scripts/portable.py`: o system prompt genérico do orchestrator diz que ele grava só o ledger; no Codex ele continua com `sandbox_mode` somente leitura.

## 2.7.0 — 2026-11-11

### Outras ferramentas: Gemini CLI, Codex, GitHub Copilot e qualquer LLM
- `gemini-extension.json` + `GEMINI.md` + `commands/squads/*.toml`: o repositório passa a ser instalável como extensão do Gemini CLI (`gemini extensions install <url>`), com as 90 skills descobertas automaticamente e os 7 agents como comandos `/squads:<agent>`.
- `scripts/portable.py build` gera, a partir de `agents/*/*.md`, os agents para Codex (`.codex/agents/*.toml`, com `sandbox_mode` somente leitura para `tech-lead`, `code-reviewer` e `orchestrator`), para GitHub Copilot (`.github/agents/*.agent.md`) e para qualquer LLM (`agents/*.md` como system prompt), trocando o que é específico do Claude Code (`Skill`, `AskUserQuestion`, `Agent`, `CLAUDE.md`, hooks) pelo equivalente de cada ferramenta.
- `scripts/portable.py install --tool codex|copilot|gemini|generic --project <dir>` copia as skills para `.agents/skills/`, grava os agents e mescla a seção do squads (com `## Project preferences`) no arquivo de contexto, sem apagar o que já existe; idempotente.
- `portable/README.md` explica cada caminho, o que muda fora do Claude Code (sem hooks, delegação, modelos) e o que foi ou não verificado.
- Validador e CI: o material gerado precisa estar em dia (`build --check`), a versão de `gemini-extension.json` precisa bater com a do `plugin.json`, e a instalação é testada em pasta temporária para as quatro ferramentas.

## 2.6.0 — 2026-11-10

### Guardrails
- `hooks/guard-commands.sh` reescrito só em bash (regex nativa, sem `grep`/`sed` por padrão): responde em milissegundos também no Windows, lê o comando do campo `tool_input.command` em vez de varrer o JSON inteiro (a `description` não dispara mais falso positivo) e trata aspas escapadas.
- Novos padrões: PowerShell (`del`, `rd`, `rmdir`, `Clear-Content`), `gcloud` e `az` que alteram recursos, `tofu`, `docker rm/rmi`, `mvn release:`, `liquibase`, mais clients de banco, `ssh`/`scp`/`sftp`/`rsync`, `curl`/`wget`/`Invoke-RestMethod` que enviam dados para fora de `localhost`, leitura de `.env`, `~/.aws`, `~/.ssh`, chaves e keystores, `printenv`/`env`/`Get-ChildItem Env:`. O motivo do pedido de confirmação agora mostra o trecho que casou.
- Novo `hooks/guard-edits.sh` (`Edit`/`Write`/`MultiEdit`): pede confirmação antes de editar migration Flyway já versionada no Git, workflow de CI/CD, arquivo de segredo ou chave, `.claude/settings.json`, e antes de gravar `@Disabled`/`@Ignore` em teste ou `skipTests`, piso do JaCoCo e exclusões no `pom.xml`/`build.gradle`.

### Processo
- `orchestrator`: bloco **Retomada** no fim de toda parada (gate, contexto esgotado, pendência), para continuar a entrega numa sessão nova sem perder o ledger.
- `scripts/test-hooks.sh`: 115 casos (comandos e edições que devem ou não pedir confirmação), rodados no CI.
- `scripts/validate-plugin.py`: passa a conferir as tools dos agents (conhecidas; nenhuma de escrita em agent somente leitura; `Skill` nos especialistas e `Agent` no orquestrador), a identidade das seções compartilhadas entre os especialistas, skills que nenhum agent carrega (aviso), os grupos do guia, o índice e as seções dos prompts, o `hooks.json` e os scripts (LF, shebang), a estrutura dos evals, qualquer contagem solta de skills/agents nos documentos e a entrada do changelog.
- CI: `shellcheck` nos scripts, testes dos hooks, compilação dos scripts Python das skills, `concurrency` e action fixada por SHA (como a skill `github-actions` recomenda).

### Evals
- Novos casos de gatilho: `email-pela-aws` (`aws-ses`), `fan-out-aws` (`aws-sns-sqs`), `clique-duplo` (`idempotency`), `listagem-sem-limite` (`pagination`) e `migration-ja-aplicada` (`flyway-migrations`). Ainda não executados: rode a suíte antes de confiar neles.

### Documentação
- README, guia e estrutura atualizados (contagem de 90 skills corrigida em quatro lugares, novo hook, changelog e testes no roteiro de contribuição).

## 2.5.0 — 2026-11-10

- Skill `aws-architecture-diagram` (diagrama de infraestrutura AWS no draw.io) e prompt `definicao-de-projeto`.
- Prova por critério no fluxo spec-driven: matriz critério → tarefa → prova no design doc, verificação da spec pelo `code-reviewer`, cobertura dos conjuntos.
- Evals `criterios-provados` e `diagrama-aws`.
- 90 skills.

## 2.0.0

- O plugin `padrao-spring-boot` passou a se chamar `squads` e o marketplace `padrao` passou a ser `edimilsonldutra` (migração manual: veja o README).
