#!/usr/bin/env python3
"""Valida a estrutura do plugin squads: skills, agents, hooks, prompts, evals, links e contagens.

Somente leitura e sem dependências (stdlib). Uso, na raiz do repositório:

    python scripts/validate-plugin.py

Sai com código 1 se houver erro; avisos não falham o build.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
TRIGGER = re.compile(r"\bUse (quando|ao|após|para|antes|depois|em|sempre)\b", re.I)
SKILL_LINK = re.compile(r"\.\./([a-z0-9-]+)/SKILL\.md")
BACKTICK_KEBAB = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
SQUADS_REF = re.compile(r"squads:([a-z0-9-]+)")

# Termos em `crase` com hífen que aparecem nos documentos e não são skills nem agents.
NOT_SKILLS = {
    "can-i-deploy",
    "ddl-auto",
    "guard-commands",
    "guard-edits",
    "max-file-size",
    "open-in-view",
    "padrao-spring-boot",
    "qualidade-maxima",
    "spring-boot-starter-validation",
    "spring-doc",
    "squads-kt",
    "test-hooks",
    "validate-plugin",
    "gemini-extension",
    "copilot-instructions",
    "workspace-write",
    "read-only",
}

# Ferramentas que um agent pode declarar e o que cada papel pode ou não ter.
KNOWN_TOOLS = {
    "Agent", "AskUserQuestion", "Bash", "Edit", "Glob", "Grep", "MultiEdit",
    "NotebookEdit", "Read", "Skill", "TodoWrite", "WebFetch", "WebSearch", "Write",
}
WRITE_TOOLS = {"Edit", "MultiEdit", "NotebookEdit", "Write"}
READ_ONLY_AGENTS = {"orchestrator", "tech-lead", "code-reviewer"}
SPECIALISTS = {"product-manager", "architect", "tech-lead", "developer", "qa", "code-reviewer"}

# Seções que todos os especialistas repetem palavra por palavra (um agent não consegue
# incluir outro arquivo): qualquer diferença é deriva, não intenção.
SHARED_SECTIONS = ("## Skills, perguntas e confirmações", "## Guardrails")

errors = []
warnings = []


def error(where, message):
    errors.append(f"{where}: {message}")


def warn(where, message):
    warnings.append(f"{where}: {message}")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read(path):
    return path.read_text(encoding="utf-8")


def frontmatter(path):
    match = FRONTMATTER.match(read(path))
    if not match:
        error(rel(path), "frontmatter ausente ou sem os delimitadores ---")
        return None
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def section(text, heading):
    """Devolve o corpo de uma seção `## …` até o próximo `## ` ou `---` de nível de página."""
    start = text.find(heading)
    if start < 0:
        return None
    body = text[start + len(heading):]
    end = len(body)
    for stop in ("\n## ", "\n---\n"):
        index = body.find(stop)
        if 0 <= index < end:
            end = index
    return body[:end].strip()


def check_skills():
    skills = {}
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        folder = skill_md.parent.name
        where = rel(skill_md)
        fields = frontmatter(skill_md)
        if fields is None:
            continue
        name = fields.get("name", "")
        description = fields.get("description", "")
        if not KEBAB.match(folder):
            error(where, f"pasta '{folder}' não está em kebab-case")
        if name != folder:
            error(where, f"name '{name}' diferente da pasta '{folder}'")
        if not description:
            error(where, "description ausente")
        elif description in (">", "|", ">-", "|-"):
            error(where, "description em bloco multilinha; use uma linha só")
        else:
            if len(description) > 1024:
                error(where, f"description com {len(description)} caracteres (máximo 1024)")
            if "<" in description or ">" in description:
                error(where, "description com < ou > (a especificação não aceita tags XML)")
            if not TRIGGER.search(description):
                error(where, "description sem gatilho ('Use quando…', 'Use ao…', 'Use após…')")
        body_lines = len(FRONTMATTER.sub("", read(skill_md)).strip().splitlines())
        if body_lines > 500:
            warn(where, f"corpo com {body_lines} linhas; considere mover detalhes para references/")
        if (skill_md.parent / "README.md").exists():
            warn(where, "README.md dentro da pasta da skill")
        skills[folder] = skill_md
    return skills


def check_agents(skills):
    agents = {}
    shared = {heading: {} for heading in SHARED_SECTIONS}
    for agent_md in sorted(ROOT.glob("agents/*/*.md")):
        folder = agent_md.parent.name
        where = rel(agent_md)
        fields = frontmatter(agent_md)
        if fields is None:
            continue
        if agent_md.stem != folder:
            error(where, f"arquivo '{agent_md.name}' deveria ser '{folder}.md'")
        if fields.get("name") != folder:
            error(where, f"name '{fields.get('name')}' diferente da pasta '{folder}'")
        for key in ("description", "tools", "model"):
            if not fields.get(key):
                error(where, f"campo '{key}' ausente no frontmatter")
        if folder in skills:
            error(where, f"agent e skill com o mesmo nome '{folder}'")

        tools = {tool.strip() for tool in fields.get("tools", "").split(",") if tool.strip()}
        for tool in sorted(tools - KNOWN_TOOLS):
            error(where, f"tool desconhecida '{tool}' no frontmatter")
        if folder in READ_ONLY_AGENTS and tools & WRITE_TOOLS:
            error(where, f"agent somente leitura declara {sorted(tools & WRITE_TOOLS)}")
        if folder in SPECIALISTS and "Skill" not in tools:
            error(where, "especialista sem a tool Skill (não conseguiria carregar as skills)")
        if folder == "orchestrator" and "Agent" not in tools:
            error(where, "orchestrator sem a tool Agent (não conseguiria delegar)")

        text = read(agent_md)
        if folder in SPECIALISTS:
            for heading in SHARED_SECTIONS:
                body = section(text, heading)
                if body is None:
                    error(where, f"seção compartilhada '{heading}' ausente")
                else:
                    shared[heading][folder] = body
        agents[folder] = agent_md

    for heading, bodies in shared.items():
        if len(set(bodies.values())) > 1:
            reference = bodies.get("developer") or next(iter(bodies.values()))
            for folder, body in bodies.items():
                if body != reference:
                    error(f"agents/{folder}/{folder}.md", f"seção '{heading}' diferente da dos outros agents (deriva do bloco compartilhado)")
    return agents


def check_links(skills, agents):
    # Nomes de prompts e de casos de eval também aparecem em crase nos documentos.
    prompts = {p.stem for p in ROOT.glob("prompts/*.md")}
    evals = {p.name for p in (ROOT / "evals").iterdir() if p.is_dir()} if (ROOT / "evals").exists() else set()
    known = set(skills) | set(agents) | NOT_SKILLS | prompts | evals
    for skill_md in skills.values():
        for target in SKILL_LINK.findall(read(skill_md)):
            if target not in skills:
                error(rel(skill_md), f"link para skill inexistente ../{target}/SKILL.md")

    documents = (
        list(ROOT.glob("agents/*/*.md"))
        + list(ROOT.glob("prompts/*.md"))
        + [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "docs/guide.md", ROOT / "skills/guide/SKILL.md"]
    )
    cited_in_agents = set()
    for doc in documents:
        if not doc.exists():
            continue
        text = read(doc)
        for token in sorted(set(BACKTICK_KEBAB.findall(text))):
            if token not in known:
                error(rel(doc), f"`{token}` não é skill nem agent (se não for para ser, inclua em NOT_SKILLS)")
        if doc.parent.parent.name == "agents":
            cited_in_agents.update(set(re.findall(r"`([a-z0-9-]+)`", text)) & set(skills))
        for ref in sorted(set(SQUADS_REF.findall(text))):
            if ref not in skills and ref not in agents:
                error(rel(doc), f"squads:{ref} não existe")

    for orphan in sorted(set(skills) - cited_in_agents - {"guide"}):
        warn(f"skills/{orphan}/SKILL.md", "skill não citada por nenhum agent (ninguém do time a carrega)")


def check_catalogs(skills):
    guide = read(ROOT / "docs/guide.md")
    in_guide = set(re.findall(r"`/squads:([a-z0-9-]+)`", guide))
    for missing in sorted(set(skills) - in_guide):
        error("docs/guide.md", f"skill '{missing}' fora do catálogo (linha com `/squads:{missing}`)")

    # Cada grupo do guia diz "(N skills)" e a tabela logo abaixo precisa ter N linhas.
    for match in re.finditer(r"^\*\*(.+?) \((\d+) skills?\)\*\*\s*$", guide, re.M):
        label, count = match.group(1), int(match.group(2))
        rest = guide[match.end():]
        next_group = re.search(r"^\*\*.+? \(\d+ skills?\)\*\*\s*$", rest, re.M)
        block = rest[: next_group.start()] if next_group else rest
        rows = re.findall(r"^\| `([a-z0-9-]+)` \| `/squads:", block, re.M)
        if len(rows) != count:
            error("docs/guide.md", f"grupo '{label}' diz ({count} skills) mas a tabela tem {len(rows)}")

    readme = read(ROOT / "README.md")
    listed = []
    for label, count, row in re.findall(r"^\| \*\*(.+?)\*\* \((\d+)\) \| (.+?) \|$", readme, re.M):
        names = re.findall(r"`([a-z0-9-]+)`", row)
        listed.extend(names)
        if int(count) != len(names):
            error("README.md", f"grupo '{label}' diz ({count}) mas lista {len(names)} skills")
    for missing in sorted(set(skills) - set(listed)):
        error("README.md", f"skill '{missing}' fora da tabela de grupos")
    for duplicated in sorted({n for n in listed if listed.count(n) > 1}):
        error("README.md", f"skill '{duplicated}' aparece em mais de um grupo")


def check_prompts():
    index = ROOT / "prompts/README.md"
    if not index.exists():
        error("prompts/README.md", "índice dos prompts ausente")
        return
    linked = set(re.findall(r"\[`([a-z0-9-]+\.md)`\]\(\1\)", read(index)))
    for prompt in sorted(ROOT.glob("prompts/*.md")):
        if prompt.name == "README.md":
            continue
        if prompt.name not in linked:
            error("prompts/README.md", f"prompt '{prompt.name}' fora da tabela")
        text = read(prompt)
        for required in ("**Quando usar:**", "## Exemplo preenchido"):
            if required not in text:
                error(rel(prompt), f"sem a seção '{required}'")
        if "## Prompt" not in text and "## Ficha" not in text:
            error(rel(prompt), "sem a seção '## Prompt' (ou '## Ficha')")


def check_hooks():
    hooks_json = ROOT / "hooks/hooks.json"
    if not hooks_json.exists():
        error("hooks/hooks.json", "arquivo ausente")
        return
    try:
        config = json.loads(read(hooks_json))
    except json.JSONDecodeError as exc:
        error("hooks/hooks.json", f"JSON inválido: {exc}")
        return
    referenced = set()
    for event, entries in config.get("hooks", {}).items():
        for entry in entries:
            if not entry.get("matcher"):
                error("hooks/hooks.json", f"entrada de {event} sem matcher")
            for hook in entry.get("hooks", []):
                command = hook.get("command", "")
                for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/(hooks/[A-Za-z0-9_.-]+)", command):
                    referenced.add(script)
                    if not (ROOT / script).exists():
                        error("hooks/hooks.json", f"command aponta para {script}, que não existe")
    for script in sorted(ROOT.glob("hooks/*.sh")) + sorted(ROOT.glob("scripts/*.sh")):
        raw = script.read_bytes()
        if b"\r\n" in raw:
            error(rel(script), "tem CRLF; o bash quebra com \\r (o .gitattributes força LF, confira o checkout)")
        if not raw.startswith(b"#!/usr/bin/env bash") and not raw.startswith(b"#!/bin/bash"):
            error(rel(script), "sem shebang bash na primeira linha")
        if script.parent.name == "hooks" and rel(script) not in referenced:
            warn(rel(script), "script em hooks/ não referenciado no hooks.json")


def check_evals(skills):
    evals = ROOT / "evals"
    if not evals.exists():
        return
    skill_regex = re.compile(r"\(\?:([a-z0-9|-]+)\)")
    for case in sorted(p for p in evals.iterdir() if p.is_dir() and p.name != "results"):
        where = rel(case)
        if not (case / "prompt.md").exists():
            error(where, "sem prompt.md")
        graders = case / "graders"
        if not graders.exists():
            error(where, "sem a pasta graders/")
            continue
        if not (graders / "skill-esperada.md").exists():
            error(where, "sem graders/skill-esperada.md")
        if not list(graders.glob("resposta*.md")):
            error(where, "sem grader de resposta (resposta.md ou resposta-<parte>.md)")
        for grader in sorted(graders.glob("*.md")):
            text = read(grader)
            fields = frontmatter(grader) or {}
            if fields.get("type") == "tool_used":
                for group in skill_regex.findall(text):
                    for name in group.split("|"):
                        if name not in skills:
                            error(rel(grader), f"input_match cita a skill inexistente '{name}'")
                if grader.name.startswith("nao-"):
                    expected = grader.name[len("nao-"):-len(".md")]
                    if expected not in skills:
                        error(rel(grader), f"nome do grader cita a skill inexistente '{expected}'")
                    if fields.get("max") != "0":
                        error(rel(grader), "grader 'nao-' precisa de max: 0")
            elif fields.get("type") != "llm":
                error(rel(grader), f"type '{fields.get('type')}' desconhecido (tool_used ou llm)")


def check_counts_and_version(skills, agents):
    total_skills = len(skills)
    total_agents = len(agents)
    readme = read(ROOT / "README.md")
    guide = read(ROOT / "docs/guide.md")
    marketplace = read(ROOT / ".claude-plugin/marketplace.json")
    patterns = [
        ("README.md", readme, r"skills-(\d+)-informational", total_skills),
        ("README.md", readme, r"agents-(\d+)-informational", total_agents),
        ("README.md", readme, r"\*\*(\d+) skills\*\*", total_skills),
        ("README.md", readme, r"\| \*\*Skills\*\* \| (\d+) —", total_skills),
        ("README.md", readme, r"(\d+) skills em \d+ grupos", total_skills),
        ("docs/guide.md", guide, r"\*\*Skills \((\d+)\)\*\*", total_skills),
        ("docs/guide.md", guide, r"\*\*Total: (\d+) skills", total_skills),
        (".claude-plugin/marketplace.json", marketplace, r"(\d+) skills \(", total_skills),
    ]
    for where, text, pattern, expected in patterns:
        found = re.findall(pattern, text)
        if not found:
            warn(where, f"contagem não encontrada (padrão {pattern})")
        for value in found:
            if int(value) != expected:
                error(where, f"diz {value}, mas existem {expected}")

    # Qualquer "N skills"/"N agents" solto no texto (diagramas, árvore, frases): os grupos
    # têm menos de 40 skills, então um número maior que isso só pode ser o total.
    documents = [ROOT / "README.md", ROOT / "docs/guide.md", ROOT / "skills/guide/SKILL.md", ROOT / "GEMINI.md", ROOT / "portable/README.md"]
    documents += list(ROOT.glob("agents/*/*.md")) + list(ROOT.glob("prompts/*.md")) + list(ROOT.glob("portable/**/*.md"))
    for doc in documents:
        text = read(doc)
        for value in re.findall(r"\b(\d+) skills\b", text):
            if int(value) >= 40 and int(value) != total_skills:
                error(rel(doc), f"menciona '{value} skills', mas existem {total_skills}")
        for value in re.findall(r"\b(\d+) agents\b", text):
            if int(value) != total_agents:
                error(rel(doc), f"menciona '{value} agents', mas existem {total_agents}")
    for value in re.findall(r"mapa completo de (\d+)", readme):
        if int(value) != total_skills:
            error("README.md", f"'mapa completo de {value}', mas existem {total_skills} skills")

    plugin = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
    declared = {path.removeprefix("./") for path in plugin.get("agents", [])}
    for agent_md in agents.values():
        if rel(agent_md) not in declared:
            error(".claude-plugin/plugin.json", f"agent {rel(agent_md)} fora da lista 'agents' (não seria carregado)")
    for path in sorted(declared):
        if not (ROOT / path).exists():
            error(".claude-plugin/plugin.json", f"lista 'agents' aponta para arquivo inexistente {path}")

    version = plugin.get("version")
    badge = re.search(r"version-([0-9.]+)-blue", readme)
    if not version:
        error(".claude-plugin/plugin.json", "campo 'version' ausente")
    elif not badge or badge.group(1) != version:
        error("README.md", f"badge de versão diferente do plugin.json ({version})")

    gemini = ROOT / "gemini-extension.json"
    if not gemini.exists():
        error("gemini-extension.json", "ausente (a instalação como extensão do Gemini CLI depende dele)")
    elif json.loads(read(gemini)).get("version") != version:
        error("gemini-extension.json", f"version diferente do plugin.json ({version})")

    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        error("CHANGELOG.md", "ausente (toda versão nova precisa de uma entrada)")
    elif version:
        first = re.search(r"^## \[?([0-9.]+)\]?", read(changelog), re.M)
        if not first:
            error("CHANGELOG.md", "sem nenhuma entrada '## <versão>'")
        elif first.group(1) != version:
            error("CHANGELOG.md", f"a entrada mais recente é {first.group(1)}, mas o plugin.json diz {version}")


def check_portable():
    """O material para Gemini, Codex, Copilot e LLMs genéricos é gerado: precisa estar em dia."""
    script = ROOT / "scripts/portable.py"
    if not script.exists():
        error("scripts/portable.py", "ausente")
        return
    spec = importlib.util.spec_from_file_location("portable", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        agents = module.load_agents()
        files = module.generated_files(agents)
    except SystemExit as exc:
        error("scripts/portable.py", f"geração falhou: {exc}")
        return
    for relative, content in files.items():
        path = ROOT / relative
        if not path.exists():
            error(relative, "arquivo gerado ausente (rode `python scripts/portable.py build`)")
        elif read(path) != content:
            error(relative, "defasado em relação aos agents (rode `python scripts/portable.py build`)")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    skills = check_skills()
    agents = check_agents(skills)
    check_links(skills, agents)
    check_catalogs(skills)
    check_prompts()
    check_hooks()
    check_evals(skills)
    check_portable()
    check_counts_and_version(skills, agents)

    for message in warnings:
        print(f"AVISO  {message}")
    for message in errors:
        print(f"ERRO   {message}")
    status = "FALHOU" if errors else "OK"
    print(f"\n{status}: {len(skills)} skills, {len(agents)} agents, {len(errors)} erros, {len(warnings)} avisos")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
