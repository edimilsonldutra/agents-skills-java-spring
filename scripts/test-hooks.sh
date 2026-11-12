#!/usr/bin/env bash
# Testa os hooks do plugin com entradas no formato que o Claude Code envia (PreToolUse).
# Uso, na raiz do repositório:  bash scripts/test-hooks.sh
# Sai com 1 se algum caso falhar. Sem dependências além de bash, sed, grep e git.

set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
COMMANDS="$ROOT/hooks/guard-commands.sh"
EDITS="$ROOT/hooks/guard-edits.sh"
failures=0
total=0

# Repositório Git temporário com uma migration já commitada e outra ainda não.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
(
  cd "$TMP" || exit 1
  git init -q
  git config user.email test@example.com
  git config user.name test
  mkdir -p src/main/resources/db/migration
  echo "create table book (id bigint);" > src/main/resources/db/migration/V1__create_book.sql
  git add -A && git commit -qm init
  echo "alter table book add column title varchar(255);" > src/main/resources/db/migration/V2__add_title.sql
) || { echo "não consegui preparar o repositório temporário"; exit 1; }

# json_escape: só o que os casos abaixo precisam (barra invertida e aspas).
esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

run() {  # run <hook> <esperado: ask|ok> <nome> <json>
  local hook=$1 expected=$2 name=$3 json=$4 out decision
  total=$((total + 1))
  out=$(printf '%s' "$json" | bash "$hook" 2>&1)
  if printf '%s' "$out" | grep -q '"permissionDecision":"ask"'; then decision=ask; else decision=ok; fi
  if [ "$decision" != "$expected" ]; then
    failures=$((failures + 1))
    printf 'FALHOU  %-9s esperado=%s obtido=%s  %s\n' "$(basename "$hook" .sh)" "$expected" "$decision" "$name"
    [ -n "$out" ] && printf '        saída: %s\n' "$out"
  fi
}

cmd() {  # cmd <esperado> <comando> [descrição]
  local expected=$1 command=$2 description=${3:-}
  run "$COMMANDS" "$expected" "$command" \
    "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$(esc "$command")\",\"description\":\"$(esc "$description")\"}}"
}

edit() {  # edit <esperado> <file_path> [new_string]
  local expected=$1 path=$2 new=${3:-}
  run "$EDITS" "$expected" "$path" \
    "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$(esc "$path")\",\"old_string\":\"x\",\"new_string\":\"$(esc "$new")\"}}"
}

write() {  # write <esperado> <file_path> <content>
  local expected=$1 path=$2 content=$3
  run "$EDITS" "$expected" "$path" \
    "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$(esc "$path")\",\"content\":\"$(esc "$content")\"}}"
}

# ---------- guard-commands: deve pedir confirmação ----------
cmd ask 'git push origin feature/x'
cmd ask 'git push --force-with-lease'
cmd ask 'git commit -m "feat: x"'
cmd ask 'git commit'                                   # no fim do comando, sem espaço depois
cmd ask 'git reset --hard HEAD~1'
cmd ask 'git checkout -- src/Main.java'
cmd ask 'git checkout .'
cmd ask 'git restore --staged pom.xml'
cmd ask 'git rebase -i main'
cmd ask 'git branch -D feature/old'
cmd ask 'git stash drop'
cmd ask 'rm -rf target'
cmd ask 'rm -r build'
cmd ask 'rm --recursive --force out'
cmd ask 'Remove-Item -Recurse -Force target'
cmd ask 'del /s /q target'
cmd ask 'rmdir /s target'
cmd ask 'kubectl apply -f k8s/'
cmd ask 'kubectl delete pod api-0'
cmd ask 'helm upgrade --install api ./chart'
cmd ask 'terraform apply -auto-approve'
cmd ask 'tofu destroy'
cmd ask 'argocd app sync api'
cmd ask 'aws s3 cp build.jar s3://bucket/'
cmd ask 'aws sqs create-queue --queue-name x'
cmd ask 'aws ecs update-service --cluster c --service s'
cmd ask 'aws configure'
cmd ask 'gcloud run deploy api --image x'
cmd ask 'az containerapp update -n api -g rg'
cmd ask 'docker push ghcr.io/org/api:abc'
cmd ask 'docker rm -f mysql'
cmd ask 'docker compose down -v'
cmd ask './mvnw deploy'
cmd ask './gradlew publish'
cmd ask 'mvn release:prepare'
cmd ask 'npm publish'
cmd ask 'gh pr create --fill'
cmd ask 'gh api repos/o/r/issues -f title=x'
cmd ask './mvnw flyway:clean'
cmd ask 'mvn flyway:migrate -Dflyway.url=jdbc:mysql://prod/db'
cmd ask 'psql -h prod -U app -c "drop table book"'
cmd ask 'mysql -h db.internal -e "select 1"'
cmd ask 'ssh deploy@prod.example.com'
cmd ask 'scp target/app.jar deploy@prod:/opt/'
cmd ask 'curl -X POST https://api.example.com/v1/x -d @body.json'
cmd ask 'curl --data "a=1" https://hooks.example.com/'
cmd ask 'Invoke-RestMethod -Method POST -Uri https://api.example.com/x -Body $b'
cmd ask 'cat ~/.aws/credentials'
cmd ask 'cat $HOME/.ssh/id_rsa'
cmd ask 'cat .env'
cmd ask 'cat .env.production'
cmd ask 'printenv | grep SECRET'
cmd ask 'env'
cmd ask 'env | sort'
cmd ask 'Get-ChildItem Env:'
cmd ask 'keytool -list -keystore app.jks'
cmd ask 'echo ok; git push'                            # composto
cmd ask 'git log --oneline && git push origin main'    # composto com leitura antes

# ---------- guard-commands: não deve pedir ----------
cmd ok 'git status'
cmd ok 'git log --oneline -20'
cmd ok 'git diff main...HEAD'
cmd ok 'git branch -a'
cmd ok 'git stash list'
cmd ok 'git commit-graph verify'                         # não é git commit
cmd ok 'ls -la target'
cmd ok 'rm notes.txt'                                    # sem -r/-f
cmd ok './mvnw clean verify'
cmd ok './gradlew cleanTest test --tests BookServiceTest'
cmd ok 'docker compose up -d'
cmd ok 'docker compose down'
cmd ok 'docker ps'
cmd ok 'kubectl get pods -n api'
cmd ok 'kubectl logs api-0'
cmd ok 'helm template api ./chart'
cmd ok 'terraform plan'
cmd ok 'aws sts get-caller-identity'
cmd ok 'aws s3 ls s3://bucket/'
cmd ok 'gcloud run services list'
cmd ok 'gh pr view 42'
cmd ok 'gh pr checks 42'
cmd ok 'gh run view 123 --log-failed'
cmd ok 'curl http://localhost:8080/actuator/health'
cmd ok 'curl -X POST http://localhost:8080/api/book/v1 -d @book.json'   # API local
cmd ok 'curl -s https://repo1.maven.org/maven2/x/maven-metadata.xml'  # GET externo
cmd ok 'cat .env.example'
cmd ok 'cat src/main/resources/application.yml'
cmd ok 'env JAVA_HOME=/opt/jdk ./mvnw -v'                 # env como prefixo, não imprime
cmd ok 'grep -rn "faz push" docs/'                        # "faz" não é "az"
cmd ok 'echo "o time faz deploy às terças"'
cmd ok 'ssh-keygen -l -f key.pub'                         # ssh-keygen não é ssh
cmd ok 'git status' 'Mostra o estado; depois faremos git push'   # texto só na descrição
cmd ok 'cat README.md' 'Ler o guia (menciona rm -rf)'              # idem

# ---------- guard-edits: deve pedir ----------
edit ask "$TMP/src/main/resources/db/migration/V1__create_book.sql" "alter table book add x int;"   # já commitada
edit ask "$TMP/.github/workflows/ci.yml" "permissions: write-all"
edit ask "$TMP/.env" "DB_PASSWORD=x"
edit ask "$TMP/config/.env.production" "X=1"
edit ask "$TMP/certs/server.pem" "---"
edit ask "$TMP/.claude/settings.json" "{}"
edit ask "$TMP/src/test/java/BookServiceTest.java" "@Disabled(\"flaky\") @Test void x() {}"
edit ask "$TMP/src/test/java/BookServiceTest.java" "@Ignore"
edit ask "$TMP/pom.xml" "<minimum>0.70</minimum>"
edit ask "$TMP/pom.xml" "<skipTests>true</skipTests>"
edit ask "$TMP/build.gradle.kts" "minimum = \"0.5\".toBigDecimal()"
edit ask "$TMP/build.gradle" "jacocoTestCoverageVerification { violationRules { rule { excludes = ['*'] } } }"
write ask "$TMP/src/test/java/BookControllerTest.java" "class BookControllerTest { @Disabled @Test void x() {} }"
write ask "$TMP/.env" "SECRET=1"

# ---------- guard-edits: não deve pedir ----------
edit ok "$TMP/src/main/resources/db/migration/V2__add_title.sql" "alter table book add title varchar(255);"   # ainda não commitada
write ok "$TMP/src/main/resources/db/migration/V3__add_author.sql" "alter table book add author varchar(255);" # nova
edit ok "$TMP/src/main/java/BookService.java" "return repository.findById(id);"
edit ok "$TMP/src/test/java/BookServiceTest.java" "@Test void findsById() { assertThat(x).isNotNull(); }"
edit ok "$TMP/src/test/java/BookServiceTest.java" "// enabled by default; see @DisplayName"          # Disabled como parte de outra palavra? não: DisplayName
edit ok "$TMP/pom.xml" "<dependency><groupId>org.flywaydb</groupId><artifactId>flyway-core</artifactId></dependency>"
edit ok "$TMP/.env.example" "DB_PASSWORD=change-me"
edit ok "$TMP/docs/adr/ADR-001-x.md" "# ADR-001"
edit ok "$TMP/README.md" "Rode git push depois"            # texto em doc não é comando

# ---------- guard-edits: o orchestrator só grava o ledger ----------
agent_write() {  # agent_write <esperado> <agent_type> <file_path>
  local expected=$1 agent=$2 path=$3
  run "$EDITS" "$expected" "$agent → $path" \
    "{\"agent_type\":\"$agent\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$(esc "$path")\",\"content\":\"# Entrega\"}}"
}
agent_write ok  "squads:orchestrator" "$TMP/docs/delivery/renovacao-online.md"
agent_write ok  "orchestrator"        "docs/delivery/renovacao-online.md"
agent_write ok  "squads:orchestrator" 'C:\proj\docs\delivery\renovacao.md'
agent_write ask "squads:orchestrator" "$TMP/src/main/java/BookService.java"
agent_write ask "squads:orchestrator" "$TMP/docs/product/prd-renovacao.md"
agent_write ask "orchestrator"        "$TMP/docs/delivery/notas.txt"
agent_write ok  "squads:developer"    "$TMP/src/main/java/BookService.java"   # outro agent: regra não se aplica

if [ "$failures" -eq 0 ]; then
  echo "OK: $total casos, 0 falhas"
  exit 0
fi
echo "FALHOU: $total casos, $failures falhas"
exit 1
