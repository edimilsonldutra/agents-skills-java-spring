# Gradle (Groovy e Kotlin DSL) — Equivalência Completa com Maven

Referência complementar de [`../SKILL.md`](../SKILL.md) quando o projeto usa **Gradle** (`Build tool: Gradle`) ou quando é necessário traduzir `pom.xml` ↔ `build.gradle` / `build.gradle.kts`.

---

## 1. Mapeamento Maven → Gradle

| Maven | Gradle, Groovy DSL | Gradle, Kotlin DSL |
|---|---|---|
| `<dependency>` com compile scope | `implementation 'group:artifact'` | `implementation("group:artifact")` |
| `<scope>runtime</scope>` (JDBC driver) | `runtimeOnly '…'` | `runtimeOnly("…")` |
| `<scope>test</scope>` | `testImplementation '…'` | `testImplementation("…")` |
| devtools (`runtime` + `optional`) | `developmentOnly '…'` | `developmentOnly("…")` |
| version em `<properties>` (`${x.version}`) | `ext { set('xVersion', '1.2.3') }` e `"group:artifact:${xVersion}"` | `val xVersion = "1.2.3"` e `"group:artifact:$xVersion"` |
| sem `<version>` (gerenciada pelo Boot BOM) | sem version — o plugin `io.spring.dependency-management` decide | igual |
| `<exclusions>` | `testImplementation('…') { exclude group: 'g', module: 'a' }` | `testImplementation("…") { exclude(group = "g", module = "a") }` |
| `annotationProcessorPaths` (MapStruct) | `annotationProcessor 'org.mapstruct:mapstruct-processor:…'` | `annotationProcessor("…")` |
| `<java.version>` | `java { toolchain { languageVersion = JavaLanguageVersion.of(N) } }` | igual |
| `spring-boot-maven-plugin` | o plugin `org.springframework.boot`, já em `plugins` | igual |
| `argLine` do surefire (agent do Mockito) | a configuration `mockitoAgent` e os `jvmArgs` que o `scaffold` escreve | igual |
| `flyway-maven-plugin` | o plugin `org.flywaydb.flyway` (abaixo) | igual |

Exemplos declarados em Groovy DSL e Kotlin DSL:

```groovy
ext {
    set('springdocVersion', '{latest 3.x}')
    set('restAssuredVersion', '{latest}')
    set('greenmailVersion', '{latest}')
}

dependencies {
    implementation "org.springdoc:springdoc-openapi-starter-webmvc-ui:${springdocVersion}"
    implementation 'tools.jackson.dataformat:jackson-dataformat-yaml'
    testImplementation "io.rest-assured:rest-assured:${restAssuredVersion}"
    testImplementation("com.icegreen:greenmail-junit5:${greenmailVersion}") {
        exclude group: 'org.eclipse.angus', module: 'jakarta.mail'
    }
}
```
```kotlin
val springdocVersion = "{latest 3.x}"
val restAssuredVersion = "{latest}"
val greenmailVersion = "{latest}"

dependencies {
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:$springdocVersion")
    implementation("tools.jackson.dataformat:jackson-dataformat-yaml")
    testImplementation("io.rest-assured:rest-assured:$restAssuredVersion")
    testImplementation("com.icegreen:greenmail-junit5:$greenmailVersion") {
        exclude(group = "org.eclipse.angus", module = "jakarta.mail")
    }
}
```

---

## 2. Diferenças críticas no Gradle

- **O Gradle ignora os repositories declarados no POM de uma dependency; o Maven os segue.** O `jasperreports-pdf` precisa do OpenPDF do repository da Jaspersoft (`pdf-reports`):
```groovy
repositories {
    mavenCentral()
    maven { url 'https://jaspersoft.jfrog.io/jaspersoft/third-party-ce-artifacts/' }
}
```
No Kotlin DSL: `maven("https://jaspersoft.jfrog.io/jaspersoft/third-party-ce-artifacts/")`.
- **Annotation processors não são descobertos pelo classpath** — declare `mapstruct-processor` (e `spring-boot-configuration-processor`) com `annotationProcessor`.
- **Dois jars são construídos**: `bootJar` gera `build/libs/<name>-<version>.jar` (executável) e `jar` gera `<name>-<version>-plain.jar`. Dockerfiles e pipelines não devem copiar o `-plain.jar` (`docker-and-docker-compose`).
- **Testes são pulados quando nada mudou** (`:test UP-TO-DATE`). Para forçá-los, execute `cleanTest test`.
- **O Flyway plugin roda fora do classpath da aplicação**, então o módulo do database e o JDBC driver vão em `buildscript` (antes de `plugins`), com versions explícitas obtidas via `./gradlew dependencies --configuration runtimeClasspath`. Somente valores de desenvolvimento local:
```groovy
buildscript {
    dependencies {
        classpath 'org.flywaydb:flyway-mysql:{flyway version of the BOM}'
        classpath 'com.mysql:mysql-connector-j:{driver version of the BOM}'
    }
}

plugins {
    id 'org.flywaydb.flyway' version '{flyway version of the BOM}'
}

flyway {
    url = 'jdbc:mysql://localhost:3306/{db_name}?useTimezone=true&serverTimezone=UTC'
    user = 'root'
    password = 'admin123'
}
```
No Kotlin DSL: `classpath("…")`, `id("org.flywaydb.flyway") version "…"` e `url = "…"`.

---

## 3. Comandos equivalentes

| Tarefa | Maven (`./mvnw`) | Gradle (`./gradlew`) |
|---|---|---|
| build e execução de todos os testes | `mvn clean package` | `./gradlew clean build` |
| build, pulando os testes | `mvn clean package -DskipTests` | `./gradlew clean build -x test` |
| todos os testes | `mvn test` | `./gradlew cleanTest test` |
| uma test class | `mvn test -Dtest=PersonServicesTest` | `./gradlew cleanTest test --tests PersonServicesTest` |
| executar a aplicação | `mvn spring-boot:run` | `./gradlew bootRun` |
| aplicar as migrations | `mvn flyway:migrate` | `./gradlew flywayMigrate` |
| árvore de dependencies | `mvn dependency:tree` | `./gradlew dependencies --configuration runtimeClasspath` |
| o jar executável | `target/<name>-<version>.jar` | `build/libs/<name>-<version>.jar` |

No Windows o wrapper é `mvnw.cmd` / `gradlew.bat`.
