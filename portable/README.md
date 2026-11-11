# squads fora do Claude Code: Gemini CLI, Codex, GitHub Copilot e qualquer LLM

As 90 skills já estão no formato aberto [Agent Skills](https://agentskills.io/specification) (`SKILL.md`), que Gemini CLI, Codex e GitHub Copilot leem da mesma pasta de projeto, `.agents/skills/`. O que muda por ferramenta é o formato dos **7 agents** e o nome do **arquivo de contexto**. Esta pasta traz os dois, gerados a partir de `agents/*/*.md` por `scripts/portable.py` (não edite à mão: rode `python scripts/portable.py build`).

| Ferramenta | Skills | Agents | Arquivo de contexto |
|---|---|---|---|
| Gemini CLI | extensão (`gemini-extension.json` + `skills/` na raiz do repositório) ou `.agents/skills/` | `commands/squads/*.toml` → `/squads:<agent>` | `GEMINI.md` |
| Codex | `.agents/skills/` | `.codex/agents/*.toml` (custom agents, com `sandbox_mode`) | `AGENTS.md` |
| GitHub Copilot | `.agents/skills/` | `.github/agents/*.agent.md` → `/agent <agent>` | `.github/copilot-instructions.md` |
| Qualquer LLM | `.agents/skills/` | `agents/*.md` como system prompt | `AGENTS.md` |

## Instalar num projeto

Com Python 3 e este repositório clonado (ou baixado), na pasta do projeto de destino:

```bash
python <caminho-do-repo>/scripts/portable.py install --tool codex   --project .
python <caminho-do-repo>/scripts/portable.py install --tool copilot --project .
python <caminho-do-repo>/scripts/portable.py install --tool gemini  --project .
python <caminho-do-repo>/scripts/portable.py install --tool generic --project .
```

O instalador copia as skills para `.agents/skills/`, grava os agents no lugar que a ferramenta lê e **mescla** a seção do squads no arquivo de contexto (entre `<!-- squads:start -->` e `<!-- squads:end -->`, sem apagar o que já existe; rodar de novo atualiza só essa seção). Depois, revise a seção `## Project preferences` do arquivo de contexto: é ela que as skills leem no lugar do `CLAUDE.md`.

Sem Python, copie à mão: `skills/*` para `.agents/skills/` e a pasta da ferramenta daqui (`codex/`, `copilot/`, `generic/`) para a raiz do projeto.

### Gemini CLI, como extensão

```bash
gemini extensions install https://github.com/edimilsonldutra/agents-skills-java-spring
```

A extensão traz as 90 skills (descobertas automaticamente; `/skills list`) e os 7 agents como comandos `/squads:<agent> <pedido>`. O `GEMINI.md` da raiz do repositório é o contexto da extensão; o do projeto (`portable/gemini/GEMINI.md` ou o que o instalador mescla) guarda as preferências.

### Só as skills, por `npx skills`

```bash
npx skills add edimilsonldutra/agents-skills-java-spring --skill '*'
```

Instala as skills em várias ferramentas de uma vez (Cursor, Windsurf, Codex, Gemini, Copilot…), sem os agents.

## O que muda em relação ao Claude Code

- **Não há hooks.** Os guardrails `guard-commands` e `guard-edits` são do Claude Code. Fora dele, a confirmação antes de `git push`, deploy, comandos de nuvem e edição de migration depende das instruções dos agents e da política de aprovação da própria ferramenta (`sandbox_mode` no Codex, permissões no Copilot e no Gemini).
- **Delegação.** Codex e Copilot delegam a subagents; o `orchestrator` usa isso. No Gemini CLI os comandos não delegam: o `orchestrator` entrega um runbook com o brief de cada passo para você rodar um a um.
- **Modelo por tarefa.** Os nomes `haiku`/`sonnet`/`opus`/`fable` do orquestrador são do Claude; mapeie para os níveis da sua ferramenta ou use o modelo da sessão.
- **Referências a `CLAUDE.md`** nas skills significam o arquivo de contexto da ferramenta (o instalador escreve isso nele).
- **Verificado:** a geração e a instalação em pasta temporária, a sintaxe dos TOML e a ausência de referências ao Claude Code nos agents gerados. **Não verificado:** a execução dentro do Gemini CLI, do Codex e do Copilot, que não estão instalados onde isto foi produzido. Se um formato mudar, ajuste `scripts/portable.py` e rode `build`.
