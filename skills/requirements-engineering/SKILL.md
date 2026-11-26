---
name: requirements-engineering
description: Engenharia de Requisitos orientada ao negócio (Vazquez & Simões) — os 3 marcos (necessidade, consenso de escopo, detalhamento 80/20), taxonomia completa (negócio, partes interessadas, solução em 3 níveis de granularidade, NFRs via ISO/IEC 25010/FURPS+, requisitos de transição, regras de negócio RN-n, restrições de negócio/técnicas, premissas e requisitos inversos), elicitação em 4 passos (preparar, executar, documentar entendimento, confirmar) e 5 técnicas (análise de documentos, glossário, observação, entrevista, questionário), modelagem (contexto, processos As-Is/To-Be, decomposição funcional, domínio, casos de uso, prototipação), verificação (8 critérios) vs validação, controle de questões e pré/pós-rastreabilidade. Use quando levantar, elicitar, analisar, verificar, validar ou gerenciar requisitos de um sistema. Não use para experimentos de descoberta (product-discovery) nem desenho técnico (design-docs).
---

Antes de aplicar este pattern, leia também [`../product-discovery/SKILL.md`](../product-discovery/SKILL.md) (validação de valor/problema), [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (PRD enxuto), [`../user-stories/SKILL.md`](../user-stories/SKILL.md) (histórias INVEST e fatias verticais) e [`../privacy-lgpd/SKILL.md`](../privacy-lgpd/SKILL.md). Depois dos requisitos aprovados, o detalhamento técnico segue para [`../design-docs/SKILL.md`](../design-docs/SKILL.md), [`../data-modeling/SKILL.md`](../data-modeling/SKILL.md) e [`../threat-modeling/SKILL.md`](../threat-modeling/SKILL.md).

# Engenharia de Requisitos orientada ao negócio

**Engenharia de Requisitos** é a disciplina de descobrir, analisar, especificar, verificar, validar e gerenciar **o que** o software precisa entregar para atender às necessidades reais do negócio — antes de gastar engenharia construindo a coisa errada. Baseada na abordagem orientada ao negócio (*Vazquez & Simões, 2016*), ela fecha a ponte entre a descoberta do problema (`product-discovery`) e a especificação técnica (`design-docs`).

> **Nunca invente fatos, regras de negócio, métricas ou restrições.** Tudo que não veio de documento real, stakeholder ou código verificado é registrado como **hipótese** ou entra no **Controle de Questões** com dono e prazo.

---

## 1. Os 3 Marcos do processo (extensão antes de profundidade)

O erro clássico é detalhar uma funcionalidade cedo demais sem enxergar o escopo inteiro (a síndrome de "90% pronto" quando metade do sistema nem foi vista). Conduza o levantamento em **três marcos progressivos**:

```text
MARCO 1 — Definição da Necessidade (Domínio do Problema)
   Por quê o projeto existe? Quais são os Requisitos de Negócio (RNeg), Restrições, Premissas
   e Partes Interessadas (com autoridade de decisão)?
         │
         ▼
MARCO 2 — Consenso sobre o Escopo (Extensão do "lago", sem mergulhar ainda)
   Onde começa e termina o sistema? Diagrama de Contexto, Processo de Negócio (As-Is → To-Be),
   Decomposição Funcional, Glossário inicial e Requisitos Inversos (fora de escopo).
   ──► [Gate: consenso de escopo com stakeholders]
         │
         ▼
MARCO 3 — Detalhamento dos Requisitos (Profundidade 80/20 por valor e risco)
   Detalhe primeiro os ~20% de requisitos de maior risco/valor: RF (objetivo de usuário),
   Regras de Negócio (RN), RNF (ISO/IEC 25010), Requisitos de Transição (RT), Casos de Uso /
   Histórias (INVEST + CCC), Modelo de Domínio, Verificação (8 critérios) → Validação.
   ──► [Gate: aprovação formal do PRD/Spec antes do design doc/plano]
```

### Calibrando o nível de detalhe

**O ótimo é inimigo do bom:** detalhe apenas o suficiente para reduzir o risco daquele projeto. Aumente o nível de detalhe quando houver:
- **Equipe externa / terceirizada** ou **geograficamente dispersa** (menos conversa informal).
- **Domínio pouco conhecido** pela equipe técnica ou **alta rotatividade** esperada.
- **Casos de teste ou estimativas formais** derivados diretamente da especificação.
- **Regulação/auditoria** que exige rastreabilidade formal ou aprovação contratual.

Diminua o formalismo (mantenha enxuto: histórias + critérios + glossário) quando o time é interno, coeso, conhece o domínio e tem acesso frequente ao negócio.

---

## 2. Taxonomia: Tipos de Requisitos, Restrições e Premissas

Separar corretamente cada tipo evita misturar objetivo de negócio, regra volátil, detalhe técnico e limitação inegociável:

| ID | Tipo | O que é | Exemplo |
|---|---|---|---|
| `RNeg-n` | **Requisito de negócio** | Objetivo, problema ou meta da organização (o *porquê* o projeto existe) | "Reduzir em 30% as multas por atraso em 8 semanas" |
| `RPI-n` | **Requisito de parte interessada** | Necessidade de um grupo/papel específico (ponte entre negócio e solução) | "O bibliotecário precisa identificar rapidamente livros com reserva pendente" |
| `RF-n` | **Requisito funcional** *(solução)* | Comportamento ou serviço que o software executa em resposta a um evento | "Renovar empréstimo ativo de um sócio" |
| `RN-n` | **Regra de negócio** | Política, cálculo ou restrição do negócio — **reutilizada** por vários RFs e muda em ritmo próprio | "RN-1: Máximo de 2 renovações por empréstimo"; "RN-2: Multa de R\$ 1,00/dia útil" |
| `RNF-n` | **Requisito não funcional** *(solução)* | Atributo de qualidade **elaborado/negociável** (ISO/IEC 25010 / FURPS+), sempre com número | "Renovação responde em p95 < 300 ms com 50 req/s" |
| `RT-n` | **Requisito de transição** | Capacidade **temporária** necessária para sair do estado atual ao novo — descartada após o corte | "Migrar 500 mil empréstimos históricos do sistema legado com reconciliação; operar em paralelo por 15 dias; treinar atendentes" |
| `RI-n` | **Requisito inverso** *(não-escopo)* | O que o sistema **explicitamente NÃO faz** (evita suposições e *scope creep*) | "Não haverá pagamento online de multas nesta fase" |
| `REST-n` | **Restrição** *(negócio ou técnica)* | Limitação **externa e inegociável** imposta ao produto (não é NFR!) | Negócio: "Lei LGPD exige retenção máx. de 5 anos". Técnica: "Autenticação obrigatória via Cognito corporativo" |
| `PREM-n` | **Premissa** | Suposição adotada como verdadeira para planejar — **se falhar, vira risco/mudança** | "O serviço `catalog` exporá consulta de reservas antes da entrega 2" |

> **Software = Requisitos de Solução (`RF` + `RNF` + `RN`) + Requisitos de Transição (`RT`).** Em substituições de legado, os **Requisitos de Transição** (conversão/limpeza de dados, carga inicial, operação paralela, convivência de integrações, treinamento) costumam esconder metade da complexidade real do projeto — **nunca os omita**.

### Granularidade dos Requisitos Funcionais (`RF`)

Todo requisito funcional cai em um de três níveis:
1. **Objetivo agregador** (macrofunção / épico — ex.: *"Gerenciar empréstimos"*): útil no **Marco 2** para delimitar escopo; **insuficiente** para implementar ou estimar.
2. **Objetivo de usuário** *(nível-alvo de especificação)*: uma tarefa completa, executada por um ator em resposta a um evento externo, que deixa o negócio em estado consistente (ex.: *"Renovar empréstimo"*, *"Registrar devolução"*).
3. **Objetivo de subfunção** (fragmento interno — ex.: *"Validar formato do CPF"*, *"Exibir modal de confirmação"*): **evite listar como RF solto**; ele pertence ao fluxo interno de um requisito de objetivo de usuário ou a uma `RN-n`.

### Classificação de Requisitos Não Funcionais (ISO/IEC 25010 e FURPS+)

Use a **ISO/IEC 25010** como checklist para não esquecer dimensões inteiras (traduzindo cada item aplicável em número com `technical-product-management`):
- **Adequação funcional** (completude/correção) · **Eficiência de desempenho** (latência p95/p99, vazão, recursos) · **Compatibilidade** (coexistência, interoperabilidade/contratos) · **Usabilidade** (acessibilidade WCAG, aprendizado, proteção contra erro) · **Confiabilidade** (disponibilidade/SLO, tolerância a falhas, RPO/RTO) · **Segurança** (autenticação, autorização por objeto, auditoria, confidencialidade — `application-security`) · **Manutenibilidade** (modularidade, testabilidade, observabilidade) · **Portabilidade** (instalação/deploy, adaptabilidade).
- *Alternativa enxuta:* **FURPS+** (*Functionality, Usability, Reliability, Performance, Supportability* + restrições de design, implementação, interface e físicas).

### Mapa de Partes Interessadas (quem precisa ser ouvido e quem decide)

**Cliente ≠ Usuário ≠ Parte Interessada.** Mapeie antes da elicitação:
```markdown
| Parte interessada | Papel no negócio | Interesse / impacto | Participa da elicitação? | Autoridade (DACI / aprova escopo?) |
|---|---|---|---|---|
| Diretoria da Biblioteca | Patrocinador | Reduzir filas no balcão | Marco 1 e aprovação | Aprovador |
| Bibliotecários | Operador diário | Agilidade na devolução/reserva | Sim (entrevista + observação) | Consultado |
| Sócios / leitores | Usuário final | Renovar sem multa | Sim (entrevista + protótipo) | Consultado |
| Jurídico / DPO | Conformidade | LGPD, retenção e auditoria | Sim (análise de docs) | Aprovador de privacidade |
| Time do `catalog` | Sistema externo | Contrato da API de reservas | Sim (contexto/contrato) | Consultado |
```

---

## 3. Elicitação sistemática (4 atividades + 5 técnicas)

**Elicitar não é "tirar pedido":** é um processo investigativo de aquisição de conhecimento do negócio (muitos requisitos são **implícitos** ou estão em conflito entre áreas).

### As 4 atividades obrigatórias de qualquer sessão de elicitação

1. **Preparação:** defina objetivo, leia documentos/código existentes antes (não pergunte o que já está escrito), agende as pessoas certas pelo mapa de partes interessadas, prepare o roteiro e a técnica.
2. **Execução:** conduza de forma ativa e sem viés (ouça mais que fale, separe **fatos** de **opiniões**, cave exceções: *"e quando dá errado?"*, *"qual é o contorno manual hoje?"*).
3. **Documentação (Documento de Entendimento):** compile os resultados **por assunto** (não transcrição bruta), separando: tópicos discutidos, decisões tomadas, requisitos/regras descobertos, termos novos para o **Glossário** e dúvidas para o **Controle de Questões**.
4. **Confirmação:** envie o Documento de Entendimento aos participantes para validação rápida. **Informação não confirmada ainda é risco de mal-entendido.**

### As 5 técnicas de elicitação (quando combinar cada uma)

| Técnica | Quando usar | Cuidado principal |
|---|---|---|
| **Análise de documentos** | **Sempre primeiro** — leis, normas, contratos, planilhas, manuais, sistema legado, logs/tickets | Documentos podem estar desatualizados; confirme se ainda refletem a prática real |
| **Glossário** *(produto e processo)* | **Desde o dia 1**, em todo projeto — alinha siglas, termos de negócio e sistemas externos | Termos comuns não entram; cada termo tem **uma definição única** sem ambiguidade (vira a linguagem ubíqua do código) |
| **Observação (etnografia)** | Quando o usuário não consegue explicar o que faz ou há muitos requisitos implícitos/contornos em planilhas | Pode causar efeito observador; combine com perguntas curtas depois (observação ativa) |
| **Entrevista** *(estruturada, semiestruturada ou aberta)* | Aprofundar regras, fluxos e exceções com stakeholders-chave | Prepare roteiro; evite perguntas fechadas ou tendenciosas; registre fatos ≠ opiniões |
| **Pesquisa / Questionário** | Muitos usuários dispersos (ex.: várias filiais) para quantificar frequência ou priorizar dores | Perguntas curtas e objetivas; teste-piloto antes de disparar (não serve para descobrir regras complexas) |

**Template de Glossário (`docs/product/glossario.md`):**
```markdown
| Termo / Sigla | Definição no domínio | Sinônimos evitados | Exemplo / observação |
|---|---|---|---|
| **Exemplar** | Unidade física identificável de um Título no acervo (possui código de barras próprio) | "Livro" (ambíguo) | Um Título pode ter 5 Exemplares |
| **Título** | Obra bibliográfica identificada por ISBN, autor e edição | "Livro" | Cadastrado no serviço `catalog` |
```

---

## 4. Modelagem ambiental e análise (Exame → Decomposição → Síntese)

A **análise** transforma anotações brutas da elicitação em modelos coerentes por três movimentos: **exame** (entender tarefas atuais e inovações no fluxo), **decomposição** (quebrar agregadores até objetivo de usuário) e **síntese** (unificar visões de vários stakeholders resolvendo conflitos).

### Modelos que fecham o Marco 2 e o Marco 3

Use **Mermaid** no Markdown (`design-docs` §9) e escolha apenas os modelos que esclarecem dúvidas reais:

1. **Diagrama de Contexto (fronteira do sistema — Marco 2):** representa o sistema como **um único nó central**, cercado pelas **entidades externas** (atores e sistemas) e **depósitos de dados externos**, ligado apenas por **fluxos de informação** (o que entra e o que sai — nunca fluxo físico).
   ```mermaid
   flowchart LR
       Socio["Sócio (Web)"] -->|"Pedido de renovação"| SYS["Sistema de Empréstimos"]
       SYS -->|"Novo vencimento / motivo da recusa"| Socio
       SYS -->|"Consulta reservas por exemplar"| CAT["Serviço catalog"]
       CAT -->|"Status de reserva"| SYS
       SYS -->|"Envio de notificação"| SES["Serviço de E-mail"]
   ```
2. **Modelagem de Processos de Negócio (As-Is → To-Be — Marco 2):** mapeia o fluxo operacional ponta a ponta entre áreas/sistemas (quem faz o quê, eventos de disparo, gargalos) para deixar claro **quais atividades o software automatiza** e quais continuam manuais.
3. **Decomposição Funcional (Marco 2):** árvore hierárquica de macrofunções (`agregadores`) → funcionalidades (`objetivos de usuário`). Expõe visualmente **buracos de escopo** (ramos "finos" que ninguém investigou) antes de detalhar.
4. **Modelagem de Domínio — Conceitos de Negócio (Marco 3):** substantivos do Glossário + atributos essenciais + relacionamentos e cardinalidades (`erDiagram` sem detalhes de tabela SQL — serve de entrada direta para `data-modeling` e `ddd-hexagonal`).
5. **Especificação comportamental — escolha conforme o contexto:**
   - **Histórias de Usuário (INVEST + CCC: *Card, Conversation, Confirmation*)** (`user-stories`): padrão para times ágeis iterativos e entregas em fatias verticais.
   - **Casos de Uso** (Ator, Pré-condições, Pós-condições, Fluxo Principal, Fluxos Alternativos, Fluxos de Exceção + referências a `RN-n`): prefira quando o fluxo tem muitas ramificações, integrações críticas ou exigência formal/regulatória.
6. **Prototipação:** classifique conscientemente antes de construir:
   - **Baixa × Alta fidelidade** (rabisco/wireframe rápido para validar fluxo × visual próximo do real para usabilidade).
   - **Horizontal × Vertical** (várias telas rasas para validar navegação/escopo × um fluxo completo até dados para validar viabilidade).
   - **Descartável × Evolutiva** (deixe explícito quando um protótipo é descartável para o negócio não exigir colocá-lo em produção!).

---

## 5. Verificação (8 critérios) × Validação

Nunca confunda as duas — **verifique antes de validar**, senão o negócio perde tempo corrigindo ambiguidade e contradição que a equipe deveria ter pegado:

- **Verificação de requisitos** (*"especificamos certo?"*): revisão interna (PM + `tech-lead` + `qa` + `architect`) conferindo a consistência entre modelos (Diagrama de Contexto ↔ Processo ↔ RF ↔ RN ↔ Modelo de Domínio) e os **8 critérios de qualidade** abaixo.
- **Validação de requisitos** (*"especificamos o produto certo para o negócio?"*): revisão com as **partes interessadas** usando protótipo, walkthrough de cenários/casos de uso e aprovação formal. **Derivação antecipada de casos de teste pelo `qa`** atua como revisão poderosa: requisito que o `qa` não consegue transformar em teste está ambíguo ou incompleto.

### Os 8 critérios de qualidade da especificação (checklist de verificação)

| # | Critério | O que checar antes de aprovar |
|---|---|---|
| 1 | **Correta** | Reflete fielmente uma necessidade real de negócio/stakeholder (sem requisito inventado ou distorcido) |
| 2 | **Completa** | Cobre fluxo principal, exceções, limites, `RN-n`, `RNF-n`, `RT-n` (transição), segurança/LGPD e nenhum "TBD/a definir" oculto |
| 3 | **Clara (não ambígua)** | Admite **uma única interpretação** (termos definidos no Glossário; sem "rápido", "intuitivo", "adequado", "etc.") |
| 4 | **Consistente** | Sem contradição interna (ex.: `RF-3` diz 2 renovações e `RN-1` diz 3; Diagrama de Contexto omite integração citada no `RF-4`) |
| 5 | **Modificável** | Estrutura organizada com IDs únicos e **regras de negócio (`RN-n`) em um só lugar** (mudar uma regra não obriga editar 12 textos) |
| 6 | **Priorizada** | Cada requisito tem prioridade explícita (MoSCoW / timeboxing) acordada com quem tem autoridade |
| 7 | **Verificável (testável)** | Existe um critério objetivo (Given/When/Then ou número) que permite provar que passa ou falha |
| 8 | **Rastreável** | Tem origem (`RNeg`/`RPI` — pré-rastreabilidade) e ID único pronto para ligar a `CA-n`, tarefas e testes (pós-rastreabilidade) |

---

## 6. Gerência de Requisitos (Questões, Mudanças e Rastreabilidade)

Requisitos mudam; gerência de requisitos garante que a mudança seja **consciente, avaliada e rastreada** (práticas do CMMI-DEV: entender requisitos → obter comprometimento → gerenciar mudanças → manter rastreabilidade bidirecional → identificar inconsistências).

### Controle de Questões (*Issues*)

Toda dúvida aberta, conflito entre áreas ou dado faltante entra em uma tabela viva (evita perguntas perdidas em ata ou e-mail):
```markdown
| ID | Questão / Conflito | Origem | Requisitos impactados | Responsável | Prazo | Status | Decisão |
|---|---|---|---|---|---|---|---|
| Q-1 | Prazo de renovação é 14 dias para livros de referência também? | Entrevista Bibliotecários | RF-1, RN-2 | Operações | 2026-03-10 | Pendente | — |
| Q-2 | Como migrar empréstimos abertos do legado? | Análise legado | RT-1 | Tech Lead + Operações | 2026-03-12 | Resolvida | Carga via CSV validado 24 h antes do corte |
```
**Regra:** nenhum requisito bloqueado por uma questão `Pendente` de impacto alto entra em implementação sem decisão registrada (ou premissa formal aprovada com plano de contingência).

### Gestão de Mudanças e Aprovação

1. **Aprovação proporcional ao contexto:** apresente os requisitos em linguagem de negócio (contexto, regras, protótipo, impactos e exclusões — nunca despeje 50 páginas secas esperando que o stakeholder leia sozinho).
2. **Qualquer mudança pós-aprovação** passa por **análise de impacto** (quais `RF`, `RN`, `RNF`, `RT`, `CA-n`, tarefas, testes, prazo e custo são afetados) antes da decisão de aprovar, postergar ou trocar escopo (`prioritization`: MoSCoW / *timeboxing*). Registre no histórico de decisões.

### Rastreabilidade Bidirecional (Pré e Pós · Vertical e Horizontal)

A rastreabilidade precisa funcionar nos dois sentidos (**para frente** e **para trás**):
- **Pré-rastreabilidade (para trás, até a origem):** por que este requisito existe? Quem pediu? Qual `RNeg-n` ou norma legal o motiva? *(Evita "ouro folheado" — gold plating — e permite avaliar se um requisito ainda faz sentido quando o negócio muda.)*
- **Pós-rastreabilidade (para frente, até entrega e prova):** onde este requisito foi desenhado, implementado e provado? *(Liga ao fluxo spec-driven de `design-docs` §13!)*
- **Vertical** (entre níveis do ciclo de vida: Negócio → PRD → Design Doc → Tarefa → Código → Teste) e **Horizontal** (entre versões do mesmo artefato ou dependências entre requisitos).

```markdown
| Origem (Pré) | Requisito (PRD) | Regra / Transição | Spec (`design-docs`) | Tarefa (`tech-lead`) | Prova (`qa` / `code-reviewer`) |
|---|---|---|---|---|---|
| RNeg-1 · RPI-1 | RF-1 (Renovar online) | RN-1, RN-2 | DD-003 · CA-1, CA-4 | T2, T3 | `LoanRenewalIntegrationTest#renewsAnActiveLoan` |
| RNeg-1 · Legado | RT-1 (Carga inicial) | — | DD-003 · §6 | T5 | Script de reconciliação em staging |
```

**Atributos mínimos recomendados por requisito** (para projetos médios/grandes): `ID`, `Origem`, `Prioridade (MoSCoW)`, `Risco`, `Estabilidade (baixa/média/alta)` e `Status (rascunho / verificado / validado / aprovado / implementado)`.

---

## 7. Como o time de agents usa

| Agent | Papel com esta skill |
|---|---|
| `product-manager` | Conduz os 3 Marcos, mapeia partes interessadas, mantém **Glossário**, **Controle de Questões**, `RNeg`/`RPI`/`RF`/`RN`/`RNF`/`RT`/`RI`, Restrições e Premissas; coordena Verificação interna e Validação com o negócio |
| `architect` | Participa do Marco 2 (Diagrama de Contexto, restrições técnicas, NFRs ISO 25010, Requisitos de Transição) e liga os IDs do PRD (`RF-n`/`RN-n`/`RNF-n`/`RT-n`) aos critérios `CA-n` do design doc (`design-docs`) mantendo rastreabilidade bidirecional |
| `tech-lead` | Participa da Verificação (viabilidade, granularidade, dependências, `RT-n` de migração/corte) e mantém a rastreabilidade até as tarefas do plano |
| `qa` | Participa da Verificação derivando cenários de teste cedo (detecta ambiguidade e incompletude antes do código) e fecha a pós-rastreabilidade com provas executáveis |
| `code-reviewer` | Confere desvios contra `RF`/`RN`/`RNF`/`RT` aprovados quando há PRD/design doc e cobra rastreabilidade de mudanças de escopo |

---

## 8. Anti-padrões (dificuldades clássicas — Cap. 4)

- **Pular o Marco 2 (consenso de escopo):** sair detalhando telas e endpoints sem Diagrama de Contexto, Processo de Negócio e Requisitos Inversos.
- **Esquecer Requisitos de Transição (`RT`):** descobrir na véspera do lançamento que há 500 mil registros legados para migrar ou equipe sem treinamento.
- **Misturar Restrição técnica com NFR ou com Decisão de arquitetura:** tratar uma escolha interna como restrição, ou tentar negociar uma lei/obrigação externa.
- **Duplicar Regras de Negócio (`RN`) em várias histórias:** mudar uma alíquota ou prazo gera contradição entre artefatos.
- **Sem Glossário:** negócio diz "livro" para Título e engenharia entende Exemplar — erro silencioso que chega ao banco de dados.
- **Sessão de elicitação sem Documento de Entendimento nem Confirmação:** cada participante sai com um sistema diferente na cabeça.
- **Validar antes de verificar:** levar especificação ambígua e inconsistente para o stakeholder (que acaba não lendo e aprovando no escuro).
- **Requisitos sem pré-rastreabilidade** (*gold plating* — ninguém sabe por que existe) ou **sem Controle de Questões** (dúvidas morrem sem dono).

---

## Regras principais

- Conduza em **3 marcos**: Definição da Necessidade (`RNeg`, Restrições, Premissas, Partes Interessadas com autoridade) → Consenso de Escopo (Diagrama de Contexto, Processo As-Is/To-Be, Decomposição Funcional, Glossário, Requisitos Inversos) → Detalhamento 80/20.
- Calibre o **nível de detalhe** (extensão × profundidade) pelo risco e contexto do time — sem subespecificar projetos críticos nem burocratizar demandas simples.
- Separe rigorosamente **Requisitos de Negócio (`RNeg`)**, **Partes Interessadas (`RPI`)**, **Funcionais (`RF` no nível de objetivo de usuário)**, **Regras de Negócio (`RN` catalogadas à parte)**, **Não Funcionais (`RNF` via ISO/IEC 25010/FURPS+ com números)**, **Requisitos de Transição (`RT`)**, **Requisitos Inversos (`RI`)**, **Restrições (inegociáveis)** e **Premissas (suposições)**.
- Toda elicitação segue **Preparação → Execução → Documentação (Documento de Entendimento) → Confirmação**; combine análise de documentos, **Glossário**, observação, entrevista e questionário conforme o caso.
- **Verifique antes de validar:** aplique os **8 critérios de qualidade** (Correta, Completa, Clara, Consistente, Modificável, Priorizada, Verificável, Rastreável), confira consistência entre modelos e envolva o `qa` cedo na derivação de cenários; depois valide com o negócio (protótipo/walkthrough).
- Mantenha **Controle de Questões** com dono/prazo/requisitos bloqueados, **Gestão de Mudanças** com análise de impacto e **rastreabilidade bidirecional (pré e pós)** da necessidade de negócio até o teste/prova.
- Nunca invente regras, números ou decisões de negócio: marque como hipótese ou abra uma questão no Controle de Questões.
