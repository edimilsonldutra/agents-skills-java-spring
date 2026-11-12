#!/usr/bin/env bash
# PreToolUse (Edit/Write/MultiEdit): devolve "ask" antes de alterar arquivos que as regras
# do pacote protegem — migration Flyway já versionada, workflow de CI/CD, segredos e
# credenciais, configuração do Claude Code — e antes de mudanças que escondem problema
# (@Disabled em teste, pular testes ou baixar o piso do JaCoCo no build).
# Não bloqueia nada sozinho: só obriga a confirmação.
#
# Entrada (stdin): o JSON do hook, com tool_input.file_path e, no Edit, old_string/new_string
# (no Write, content). Saída: nada (segue normal) ou o JSON com permissionDecision "ask".
# Só bash (sem jq); o único subprocesso é o git, e só para migrations.
# Teste: bash scripts/test-hooks.sh

input=$(cat)
input=${input//$'\r'/ }
input=${input//$'\n'/ }

json_string() {
  local re='"'"$1"'"[[:space:]]*:[[:space:]]*"((\\.|[^"\\])*)"' value
  [[ $input =~ $re ]] || return 0
  value=${BASH_REMATCH[1]}
  value=${value//\\\"/\"}
  value=${value//\\n/ }
  value=${value//\\t/ }
  value=${value//\\\\/\\}
  printf '%s' "$value"
}

ask() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"squads guardrail: %s — confirme antes de alterar."}}\n' "$1"
  exit 0
}

path=$(json_string file_path)
[ -z "$path" ] && exit 0
norm=${path//\\//}

# O orchestrator só grava o ledger da entrega (docs/delivery/*.md). Vale quando o Claude Code
# informa o agent no campo agent_type (subagent ou sessão aberta com --agent).
case "$(json_string agent_type)" in
  orchestrator|*:orchestrator)
    case "$norm" in
      docs/delivery/*.md|*/docs/delivery/*.md) ;;
      *) ask "o orchestrator só grava o ledger em docs/delivery/*.md; o resto é trabalho dos especialistas" ;;
    esac
    ;;
esac

# Exemplos e modelos de .env não são segredo.
case "$norm" in
  *.env.example|*.env.sample|*.env.template|*.env.dist) ;;
  *.env|*/.env.*)                                        ask "arquivo .env (segredos)" ;;
esac

case "$norm" in
  */.github/workflows/*|.github/workflows/*)            ask "workflow de CI/CD (permissões, segredos e deploy passam por aqui)" ;;
  *.pem|*.p12|*.jks|*.pfx|*.keystore|*/id_rsa|*/id_ed25519|*.key) ask "chave, certificado ou keystore" ;;
  */.aws/credentials|*/.aws/config|*/.ssh/*|*/.kube/config|*/.docker/config.json) ask "credenciais do usuário" ;;
  */.claude/settings.json|*/.claude/settings.local.json|*/hooks/hooks.json) ask "configuração do Claude Code ou do plugin (permissões e hooks)" ;;
esac

# Migration Flyway já versionada no Git: editar quebra o checksum em todo ambiente onde ela rodou.
case "$norm" in
  */db/migration/*|*/db/migrations/*|*/V[0-9]*__*.sql|*/R__*.sql)
    dir=${norm%/*}
    [ "$dir" = "$norm" ] && dir=.
    if git -C "$dir" ls-files --error-unmatch -- "$norm" >/dev/null 2>&1; then
      ask "migration Flyway já versionada no Git (edite só a que você criou e ainda não commitou; para mudar o schema, crie uma nova)"
    fi
    ;;
esac

# Conteúdo que esconde problema em vez de resolver.
new=$(json_string new_string)
[ -z "$new" ] && new=$(json_string content)
[ -z "$new" ] && exit 0

case "$norm" in
  */src/test/*|*Test.java|*Tests.java|*IT.java|*Spec.groovy|*Test.kt)
    re='@Disabled|@Ignore([^[:alnum:]_]|$)|assumeTrue\(false|@EnabledIf\("false"'
    if [[ $new =~ $re ]]; then
      ask "teste sendo desabilitado (@Disabled/@Ignore) — o padrão é corrigir a causa, não esconder o teste"
    fi
    ;;
  */pom.xml|*/build.gradle|*/build.gradle.kts|*/gradle.properties|*/maven.config|*/.mvn/*)
    re='<skipTests>|skipTests=|-DskipTests|maven\.test\.skip|jacoco\.skip|<minimum>|minimum[[:space:]]*=|<haltOnFailure>false|ignoreFailures|<testFailureIgnore>true|excludes?[[:space:]]*[=(>]'
    if [[ $new =~ $re ]]; then
      ask "build pulando testes, afrouxando o piso de cobertura ou excluindo classes do JaCoCo"
    fi
    ;;
esac

exit 0
