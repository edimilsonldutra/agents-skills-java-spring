# Changelog

Mudanças notáveis do plugin `squads`. A versão é a de `.claude-plugin/plugin.json`; quem já instalou só recebe uma mudança quando ela sobe.

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
