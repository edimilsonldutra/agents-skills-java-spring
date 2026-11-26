# Revisão de código

**Quando usar:** antes de commit, push ou merge; para revisar um PR.
**Quem roda:** `squads:code-reviewer` (somente leitura). Diff grande: peça ao `squads:orchestrator` para revisar em paralelo por ângulo.
**Entrega:** achados por severidade (🔴 blocker, 🟠 major, 🟡 minor, 🔵 nit, 🟣 legado fora do diff) com `arquivo:linha`, cenário de falha e sugestão; verificação da spec quando houver design doc (`design-docs`); checagem de complexidade cognitiva (`cognitive-complexity`, `cdd.json`) e confirmação de versões com `library-docs`; e um veredito.

## Prompt

```text
Revise <o diff não commitado | a branch <nome> contra <main> | o PR #<número> | os arquivos <lista>>.

Contexto da mudança: <o que ela deveria fazer, em 1–2 frases>
Especificação para conferir: <caminho do design doc, PRD ou issue | nenhuma>
Provas da spec (se houver): <seção 13 do design doc ou relatório do QA | não se aplica>
Rodada: <primeira | nova rodada após correções (R1…)>
Foco extra: <segurança | concorrência | contrato de API | migrations | testes | performance | nenhum>
Pode ignorar: <arquivos gerados, formatação | nada>
```

## Exemplo preenchido

```text
Revise a branch feature/renovacao-online contra main.

Contexto da mudança: adiciona POST /api/v1/loans/{id}/renew com limite de 2 renovações.
Especificação para conferir: docs/design/DD-003-renovacao.md
Foco extra: segurança (IDOR: leitor renovando empréstimo de outro) e migrations
Pode ignorar: nada
```

## Dicas

- Para forçar o modelo mais forte em uma revisão crítica: acrescente "revise com opus" (já é o padrão do `code-reviewer`) ou peça `fable` explicitamente.
- O revisor não edita nada; para aplicar as correções, passe os achados ao `developer`.
