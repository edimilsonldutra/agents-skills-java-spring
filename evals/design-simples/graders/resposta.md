---
type: llm
weight: 1
---

Move a transição para um método de negócio da entity (loan.renew(clock)) mantendo os setters que o Dozer usa, encapsula o SDK de chat num adapter que recebe e devolve tipos do projeto, e troca os 30 ifs por uma regra generalizada com os valores (autores e dias extras) em dado, carregados pelo service e passados a uma regra pura testável, com validação e dono para o cadastro. Não propõe migrar para hexagonal nem um motor de regras. O agente só tem ferramentas de leitura: orientar basta.
