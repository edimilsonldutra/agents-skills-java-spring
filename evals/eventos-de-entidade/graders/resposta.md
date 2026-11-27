---
type: llm
weight: 1
---

Aplica o escritor único (só o catálogo publica o estado do livro; reservas usa o próprio tópico ou comandos), troca o campo action por eventos de propósito único ou por um evento de entidade com o estado completo, publicado com a chave do livro num tópico compactado com tombstone para exclusão, e faz o empréstimo manter uma cópia local com upsert por versão, reconstruível por um grupo de consumidores novo lendo desde o início, aceitando consistência eventual. O agente só tem ferramentas de leitura: orientar basta.
