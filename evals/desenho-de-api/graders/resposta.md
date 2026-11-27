---
type: llm
weight: 1
---

Trata a abertura a parceiros como mudança de visibilidade (rigor de contrato, documentação, segurança e garantia de ciclo de vida), substitui o PUT com status por uma ação de transição de estado (POST /api/loan/v1/{id}/renewal com a regra no servidor e 409 para transição inválida, citando mass assignment), e resolve a sobrescrita com ETag derivado do @Version e If-Match no PUT (412 para versão velha, 428 sem o header), com os testes desses caminhos. O agente só tem ferramentas de leitura: orientar basta.
