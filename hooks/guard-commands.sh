#!/usr/bin/env bash
# PreToolUse (Bash/PowerShell): devolve "ask" para comandos destrutivos ou externos,
# para que o usuário confirme mesmo quando um agent ignora as instruções do prompt.
# Não bloqueia nada sozinho: só obriga a confirmação.
#
# Entrada (stdin): o JSON do hook, com o comando em tool_input.command.
# Saída: nada (segue normal) ou o JSON com permissionDecision "ask".
# Só bash (sem jq, sem subprocessos no caminho comum — roda em milissegundos também no Windows).
# Teste: bash scripts/test-hooks.sh

input=$(cat)
input=${input//$'\r'/ }
input=${input//$'\n'/ }

# Extrai o valor string de uma chave do JSON ("command", "description"…), respeitando
# aspas escapadas, e desfaz os escapes mais comuns. Imprime vazio se a chave não existir.
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

command=$(json_string command)
# Sem o campo (formato inesperado), analisa a entrada inteira: melhor um "ask" a mais
# do que um push sem confirmação.
[ -z "$command" ] && command=${input//\\\"/\"}

S='[[:space:]]+'
B='(^|[^[:alnum:]_./-])'   # início de palavra de comando (evita "faz " casar com "az ")
E='([^[:alnum:]_-]|$)'     # fim de palavra

patterns=(
  # Git: publica, reescreve histórico ou descarta trabalho
  "git${S}push"
  "git${S}(commit|merge|tag)${E}"
  "git${S}reset${S}--(hard|merge)"
  "git${S}clean"
  "git${S}checkout${S}(--|\\.)"
  "git${S}restore"
  "git${S}switch${S}--discard-changes"
  "git${S}rebase"
  "git${S}branch${S}-(D|-delete)"
  "git${S}stash${S}(drop|clear)"
  "git${S}(filter-branch|filter-repo|update-ref|reflog${S}expire|gc${S}--prune|worktree${S}remove)"
  # Apagar arquivos (bash, cmd e PowerShell)
  "${B}rm${S}-[[:alpha:]]*[rRf]"
  "${B}rm${S}[^;&|]*--(recursive|force)"
  "${B}(del|erase|rd|rmdir)${S}"
  "(Remove-Item|Clear-Content)"
  # Cluster e entrega
  "kubectl${S}(apply|create|delete|replace|patch|edit|scale|rollout|drain|cordon|uncordon|taint|label|annotate|exec|set)"
  "helm${S}(install|upgrade|uninstall|delete|rollback|push)"
  "(terraform|tofu)${S}(apply|destroy|import|state|taint|untaint|force-unlock|workspace${S}delete)"
  "argocd${S}(app${S}(sync|delete|rollback|set|create|patch|terminate-op)|proj${S}(create|delete))"
  # Nuvem (AWS, GCP, Azure): tudo que cria, altera ou apaga recursos
  "aws${S}s3${S}(cp|mv|rm|sync|rb|mb)"
  "aws${S}[[:alnum:]-]+${S}(create|delete|put|update|terminate|run|start|stop|modify|attach|detach|remove|send|publish|invoke|reboot|restore|tag|untag)"
  "aws${S}(configure|sso${S}login)"
  "gcloud${S}[^;&|]*${S}(create|delete|deploy|update|set-iam-policy|add-iam-policy-binding|remove-iam-policy-binding|ssh|scp)${E}"
  "${B}az${S}[^;&|]*${S}(create|delete|deploy|update|start|stop|restart|assign|import|upload)${E}"
  # Containers e registries
  "docker${S}(push|login|rm|rmi|system${S}prune|container${S}(rm|prune)|image${S}(rm|prune)|volume${S}(rm|prune))"
  "docker${S}compose${S}down${S}[^\"]*(-v|--volumes)"
  # Publicação de artefatos
  "(mvnw?|mvnw\\.cmd|gradlew?|gradlew\\.bat)${S}[^\"|;&]*(deploy|publish|release:(prepare|perform))"
  "npm${S}(publish|unpublish|deprecate)"
  "${B}gh${S}(pr${S}(create|merge|close|comment|review)|release|repo${S}(delete|create)|secret|variable|workflow${S}run|api)"
  # Banco de dados: migrations fora do build e clients diretos
  "flyway[:[:space:]]+[^\"|;&]*(clean|migrate|repair|baseline|undo)"
  "liquibase[:[:space:]]+[^\"|;&]*(update|rollback|drop)"
  "${B}(psql|mysql|mysqladmin|mysqldump|pg_dump|pg_restore|sqlcmd|sqlplus|mongosh|mongo|redis-cli)${S}"
  # Acesso remoto e envio de dados para fora
  "${B}(ssh|scp|sftp|rsync)${S}"
  "${B}(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm)${S}[^;&|]*(-X[[:space:]]*|--request${S}|-Method${S})(POST|PUT|DELETE|PATCH)${E}"
  "${B}(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm)${S}[^;&|]*(${S}-d${S}|--data|--upload-file|${S}-T${S}|--post-data|-Body${S}|-InFile${S})"
  # Segredos e credenciais: ler ou imprimir
  "(~|\\\$HOME|%USERPROFILE%|\\\$env:USERPROFILE)/\\.(aws|ssh|kube|docker)/"
  "(id_rsa|id_ed25519|\\.pem|\\.p12|\\.jks|\\.pfx)${E}"
  "${B}\\.env(\\.(local|production|prod|staging|stage|dev|development|test|secret|secrets))?([^[:alnum:]_.-]|$)"
  "(^|[;&|][[:space:]]*)(printenv|env|set)[[:space:]]*(\\||;|>|$)"
  "(Get-ChildItem|gci|ls|dir)${S}[Ee][Nn][Vv]:"
)

# Chamadas HTTP para a própria máquina (API rodando em localhost) não precisam de confirmação.
local_http='(localhost|127\.0\.0\.1|\[::1\]|host\.docker\.internal|0\.0\.0\.0)'

for pattern in "${patterns[@]}"; do
  if [[ $command =~ $pattern ]]; then
    hit=${BASH_REMATCH[0]}
    case "$pattern" in
      *curl*) [[ $command =~ $local_http ]] && continue ;;
    esac
    hit=${hit//\"/}
    hit=${hit//\\/}
    hit=${hit:0:60}
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"squads guardrail: comando destrutivo ou externo (%s) — confirme antes de executar."}}\n' "$hit"
    exit 0
  fi
done

exit 0
