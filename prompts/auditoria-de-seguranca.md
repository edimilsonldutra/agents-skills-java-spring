# Auditoria de segurança e privacidade (AppSec / LGPD)

**Quando usar:** antes de expor uma API pública ou a parceiros, auditar um serviço existente contra o OWASP API Security Top 10 e a LGPD, ou planejar e corrigir achados de segurança (`SR-n`) um a um com prova automatizada.
**Pipeline:** `architect` (`threat-modeling` do sistema real) + `code-reviewer` (`application-security` §13) + `product-manager` (`privacy-lgpd`: dados pessoais, base legal, retenção e eliminação), em paralelo (somente leitura) → gate humano sobre o relatório consolidado → *(se aprovado corrigir)* `developer` + `qa` um achado por vez → `code-reviewer`.
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovação:** gravar os relatórios em `docs/security/` e decidir quais achados corrigir agora vs aceitar risco com dono e prazo.

## Prompt

```text
Execute uma auditoria de segurança e privacidade (AppSec / LGPD) em: <serviço, módulo ou pasta>.

Exposição da API: <pública na internet | parceiros B2B | interna no cluster>
Autenticação atual: <JWT próprio | AWS Cognito | OAuth2 | não sei>
Dados sensíveis ou pessoais tratados: <CPF, e-mail, endereço, financeiro, arquivos | descubra no código>
Escopo: <somente diagnóstico e relatório | diagnóstico + correção após minha aprovação>
Exceções e riscos já aceitos: <caminhos em docs/adr/ ou docs/security/ | nenhum>
Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>
```

## Exemplo preenchido

```text
Execute uma auditoria de segurança e privacidade (AppSec / LGPD) em: serviço de empréstimos (pasta src/main/java/br/com/edimilsonldutra).

Exposição da API: pública na internet
Autenticação atual: JWT próprio
Dados sensíveis ou pessoais tratados: descubra no código
Escopo: diagnóstico + correção após minha aprovação
Exceções e riscos já aceitos: docs/adr/
Perfil de modelo: auto
```

## Dicas

- Só entra como achado o que tiver evidência verificada no código (`arquivo:linha` e cenário de exploração); suspeitas sem prova ficam em "a verificar".
- Correções que alteram o contrato externo (ex.: remover campo sensível de resposta pública ou passar a exigir dono do recurso) seguem `api-versioning` e `release-management`, nunca quebra silenciosa.
