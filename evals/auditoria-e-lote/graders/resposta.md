---
type: llm
weight: 1
---

Configura auditoria com @EnableJpaAuditing, AuditingEntityListener, @CreatedDate/@LastModifiedDate/@CreatedBy/@LastModifiedBy, AuditorAware sem usuário anônimo e as colunas criadas por migration Flyway; explica que IDENTITY impede o batch JDBC de inserts e propõe JdbcTemplate.batchUpdate ou SEQUENCE com allocationSize igual ao INCREMENT BY (decisão registrada), com hibernate.jdbc.batch_size e flush/clear por lote para não estourar o contexto de persistência. O agente só tem ferramentas de leitura: orientar basta.
