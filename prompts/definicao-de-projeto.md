# Definição de projeto

**Quando usar:** antes de criar um projeto novo, para registrar de uma vez como ele será: o problema, o domínio, as regras, a segurança, os requisitos de qualidade, as integrações e o deploy. É a versão completa de [`novo-projeto.md`](novo-projeto.md), que cobre só as escolhas técnicas da base.
**Como usar:** copie o bloco **Ficha** para `docs/projeto.md` na pasta do projeto novo, preencha e apague as linhas que não se aplicam. Campo sem resposta? Deixe `não sei`: o agent assume o default da skill e declara a suposição.
**Entrega:** um arquivo que as skills e os agents leem como fonte do projeto. Eles param de perguntar o que já está lá.

## Como rodar

Com a ficha preenchida em `docs/projeto.md`, siga três passos, nesta ordem:

| Passo | Onde | Pedido |
|---|---|---|
| 1. Base do projeto | Sessão normal (`claude`), comece com `/squads:scaffold` | `Crie o projeto descrito nas seções 1 e 2 de docs/projeto.md.` |
| 2. Preferências | Sessão normal, comece com `/squads:project-claude-md` | `Crie o CLAUDE.md a partir da seção 2 de docs/projeto.md. Mostre o arquivo antes de gravar.` |
| 3. Funcionalidades | `claude --agent squads:orchestrator` | `Entregue a primeira entrega descrita na seção 9 de docs/projeto.md, usando o restante da ficha como contexto.` |

Projeto médio ou grande, com dados pessoais ou integrações: no passo 3, peça antes `Faça o design doc e o threat model do sistema descrito em docs/projeto.md.` O `architect` grava em `docs/` com a sua confirmação.

## Ficha

```markdown
# <nome-do-projeto>

## 1. Visão geral
- Nome do artifact (kebab-case): <ex.: biblioteca-api>
- Em uma frase: <o que o sistema faz e para quem>
- Problema: <o que dói hoje, para quem, e como sabemos (dado, reclamação, ticket)>
- Usuários e papéis: <papel: o que faz | ...>
- Métrica de sucesso: <número que deve mudar, ex.: "reduzir atendimentos de balcão em 50% em 60 dias">
- Fora de escopo: <o que este projeto NÃO faz>

## 2. Base técnica (scaffold e CLAUDE.md)
- Group id e base package: <br.com.edimilsonldutra | outro>
- Java: <25 (LTS) | outro>
- Build: <Maven | Gradle Groovy | Gradle Kotlin DSL>
- Configuração: <YAML | properties>
- Idioma do texto para o cliente (mensagens de erro, validação, Swagger): <inglês | português>
- Comentários no código gerado: <não | sim>
- Injeção de dependência: <construtor | field>
- Persistência (Spring Data JPA): <sim | não>
  - Banco: <MySQL | PostgreSQL | SQL Server | Oracle | MariaDB>
  - Mapeamento entity/DTO: <Dozer | MapStruct>
  - Flyway: <sim | não>
- Exception handling (`ExceptionResponse`): <sim | não>
- Web config (CORS e formatos): <só JSON | JSON + XML | JSON + YAML | JSON + XML + YAML>
- Swagger / OpenAPI: <sim | não>
  - Annotations: <interface *ControllerDocs | direto no controller>
- Bean Validation: <sim | não>
- Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>

## 3. Domínio
Uma linha por entidade. Identificadores em inglês.
- <Entity>: <campo: tipo, obrigatório?, regra> | ...
  - Relações: <ex.: N:1 com Author>
  - Estados (se houver): <ex.: ACTIVE → RETURNED | ACTIVE → OVERDUE>
- <Entity>: ...

## 4. Regras de negócio
Uma por linha, verificável (vira critério de aceite).
- <ex.: um leitor tem no máximo 3 empréstimos ativos>
- <ex.: renovação só sem reserva pendente e sem multa>

## 5. API
- Estilo: <REST JSON | outro>
- Prefixo e versionamento: </api/v1 | header | não sei>
- Paginação nas listas: <sim | não>
- HATEOAS: <não | sim>
- Endpoints principais: <MÉTODO /caminho: o que faz, quem pode> | ...
- Idempotência em operações de escrita expostas a retry: <sim: quais | não>

## 6. Segurança e dados
- Autenticação: <nenhuma | JWT próprio | Cognito | outro provedor OIDC>
- Autorização: <papel → o que pode> | ...
- Dados pessoais ou sensíveis (LGPD): <sim: quais campos e por quê | não>
- Retenção e exclusão: <ex.: apagar dados do leitor 5 anos após o último empréstimo | não sei>
- Exposição: <interna (só rede da empresa) | pública na internet>

## 7. Requisitos de qualidade
Números decidem arquitetura; "rápido" não decide.
- Carga: <ex.: 50 req/s, pico 200 req/s | não sei>
- Latência: <ex.: p95 < 300 ms | não sei>
- Disponibilidade: <ex.: 99,9% | não sei>
- RTO/RPO: <ex.: RTO 1 h, RPO 15 min | não sei>
- Volume de dados: <ex.: 2 milhões de registros em 3 anos | não sei>
- Cobertura de testes mínima: <ex.: 80% de linhas no JaCoCo | não sei>

## 8. Integrações e infraestrutura
- Sistemas externos: <sistema: como (REST, fila, arquivo), quem chama quem> | nenhum
- Mensageria: <nenhuma | Kafka | RabbitMQ | SQS/SNS | EventBridge | não sei>
- Arquivos: <upload/download | importação/exportação XLSX/CSV | relatórios PDF | nenhum>
- E-mail: <SES | SMTP | nenhum>
- Cache: <nenhum | Redis | não sei>
- Arquitetura: <monólito | monólito modular | microsserviços | não sei>
- Nuvem: <AWS | GCP | Azure | on-premises>
- Runtime: <Docker Compose local | ECS Fargate | EKS/Kubernetes | Lambda | Cloud Run | não sei>
- Infraestrutura como código: <Terraform | nenhuma | não sei>
- CI/CD: <GitHub Actions | outro>
- Ambientes: <dev, homologação, produção>
- Observabilidade: <logs estruturados, métricas, tracing | não sei>

## 9. Entregas
Da primeira para a última. A primeira deve ser pequena e útil.
1. <ex.: CRUD de Book com Swagger e testes>
2. <ex.: empréstimo e devolução com as regras da seção 4>
3. <...>

## 10. Restrições e referências
- Prazo: <data | não há>
- Tecnologia obrigatória ou proibida: <...>
- Equipe: <tamanho e experiência relevante, ex.: "4 pessoas, sem experiência com Kafka">
- Referências: <PRD, protótipo, contrato OpenAPI, sistema legado, issues>
```

## Exemplo preenchido

```markdown
# biblioteca-api

## 1. Visão geral
- Nome do artifact (kebab-case): biblioteca-api
- Em uma frase: API de empréstimos da biblioteca municipal, para o app e o site dos leitores e para o balcão.
- Problema: 40% dos atendimentos de balcão são renovações e consultas de disponibilidade (relatório de março).
- Usuários e papéis: leitor: consulta, reserva e renova | bibliotecário: empresta, devolve e cadastra o acervo
- Métrica de sucesso: atendimentos de balcão caem 50% em 60 dias após o lançamento.
- Fora de escopo: pagamento de multa online; acervo digital.

## 2. Base técnica (scaffold e CLAUDE.md)
- Group id e base package: br.com.edimilsonldutra
- Java: 25 (LTS)
- Build: Maven
- Configuração: YAML
- Idioma do texto para o cliente: português
- Comentários no código gerado: não
- Injeção de dependência: construtor
- Persistência (Spring Data JPA): sim
  - Banco: PostgreSQL
  - Mapeamento entity/DTO: MapStruct
  - Flyway: sim
- Exception handling (`ExceptionResponse`): sim
- Web config (CORS e formatos): só JSON
- Swagger / OpenAPI: sim
  - Annotations: interface *ControllerDocs
- Bean Validation: sim
- Perfil de modelo: equilibrado

## 3. Domínio
- Book: title: string, obrigatório | author: string, obrigatório | isbn: string, obrigatório, único | copies: int, >= 0
- Reader: name: string, obrigatório | email: string, obrigatório, único | document: string, obrigatório (dado pessoal)
- Loan: book, reader, loanDate, dueDate, returnDate, renewals: int
  - Relações: N:1 com Book, N:1 com Reader
  - Estados: ACTIVE → RETURNED | ACTIVE → OVERDUE → RETURNED
- Reservation: book, reader, createdAt, status
  - Estados: PENDING → FULFILLED | PENDING → CANCELLED

## 4. Regras de negócio
- Um leitor tem no máximo 3 empréstimos ativos.
- O prazo do empréstimo é de 14 dias.
- A renovação adiciona 14 dias, até 2 vezes por empréstimo, e só sem reserva pendente do livro e sem multa.
- Devolução atrasada gera multa de R$ 1,00 por dia.

## 5. API
- Estilo: REST JSON
- Prefixo e versionamento: /api/v1
- Paginação nas listas: sim
- HATEOAS: não
- Endpoints principais: GET /books: busca no acervo, público | POST /loans: empresta, bibliotecário | POST /loans/{id}/renew: renova, leitor dono do empréstimo | POST /reservations: reserva, leitor
- Idempotência em operações de escrita expostas a retry: sim: POST /loans e POST /loans/{id}/renew

## 6. Segurança e dados
- Autenticação: Cognito
- Autorização: LIBRARIAN → acervo, empréstimos e devoluções | READER → só os próprios empréstimos e reservas
- Dados pessoais ou sensíveis (LGPD): sim: name, email e document do leitor, para identificar quem tomou o livro
- Retenção e exclusão: anonimizar o leitor 5 anos após o último empréstimo
- Exposição: pública na internet

## 7. Requisitos de qualidade
- Carga: 20 req/s, pico 100 req/s às segundas
- Latência: p95 < 300 ms
- Disponibilidade: 99,5%
- RTO/RPO: RTO 4 h, RPO 15 min
- Volume de dados: 50 mil livros e 500 mil empréstimos em 3 anos
- Cobertura de testes mínima: 80% de linhas no JaCoCo

## 8. Integrações e infraestrutura
- Sistemas externos: nenhum
- Mensageria: SQS/SNS, para notificar o vencimento
- Arquivos: importação do acervo em XLSX
- E-mail: SES, para o aviso de vencimento
- Cache: não sei
- Arquitetura: monólito modular
- Nuvem: AWS
- Runtime: ECS Fargate
- Infraestrutura como código: Terraform
- CI/CD: GitHub Actions
- Ambientes: dev, homologação, produção
- Observabilidade: logs estruturados, métricas e tracing

## 9. Entregas
1. CRUD de Book com Swagger, paginação e testes.
2. Empréstimo e devolução com as regras da seção 4, autenticação Cognito.
3. Renovação e reserva.
4. Aviso de vencimento por e-mail via SQS e SES.
5. Importação do acervo em XLSX.

## 10. Restrições e referências
- Prazo: entrega 2 em produção até 30/03
- Tecnologia obrigatória ou proibida: AWS obrigatória
- Equipe: 3 pessoas, experiência com Spring e AWS, nenhuma com Kafka
- Referências: protótipo do app no Figma (link interno)
```

## Dicas

- A ficha fica versionada no projeto (`docs/projeto.md`). Quando uma decisão mudar, atualize a ficha antes de pedir a próxima entrega.
- As seções 1 a 2 alimentam o `scaffold` e o `CLAUDE.md`. As seções 3 a 8 viram PRD, design doc e threat model. A seção 9 é a fila de pedidos do orquestrador.
- Regra de negócio sem número ("prazo curto") vira suposição do agent. Escreva o número.
- Nunca coloque segredos, tokens, IDs de conta nem dados pessoais reais na ficha. Use exemplos fictícios.
