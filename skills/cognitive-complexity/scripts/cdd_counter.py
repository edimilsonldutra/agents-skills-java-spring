#!/usr/bin/env python3
"""Contador determinístico de Complexidade Cognitiva (CDD) para Java / Spring Boot.

Lê o `cdd.json` mais próximo de cada arquivo `.java`, descobre os tipos declarados no
repositório e calcula os pontos de cada regra com `arquivo:linha`, comparando opcionalmente
com uma branch/commit base (`--base main`).

Somente biblioteca padrão do Python 3. Uso:

    python cdd_counter.py [arquivos_ou_pastas...] [--base main] [--project <raiz>] [--json]
    python cdd_counter.py --self-test
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_CDD_KEYS = {"unit", "limit", "rules"}
ALLOWED_CDD_KEYS = {"unit", "limit", "testLimit", "tests", "ignore", "ignoreMembers", "rules"}
KNOWN_RULE_IDS = {
    "branch",
    "switch-case",
    "ternary",
    "loop",
    "exception-handling",
    "logical-operator",
    "project-type",
    "function-argument",
}

TYPE_DECL_RE = re.compile(r"\b(?:class|interface|enum|record|@interface)\s+([A-Z][A-Za-z0-9_]*)")


def strip_comments_and_strings(source: str) -> str:
    """Substitui comentários e literais de texto/char por espaços preservando quebras de linha."""
    out: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
        elif ch == "/" and nxt == "*":
            out.append("  ")
            i += 2
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            if i < n:
                out.append("  ")
                i += 2
        elif source.startswith('"""', i):
            out.append('"" ')
            i += 3
            while i < n and not source.startswith('"""', i):
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            if i < n:
                out.append("   ")
                i += 3
        elif ch in ('"', "'"):
            quote = ch
            out.append(quote)
            i += 1
            while i < n and source[i] != quote:
                if source[i] == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            if i < n:
                out.append(quote)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def strip_ignored_members(cleaned: str, ignore_members: set[str]) -> str:
    """Esvazia o corpo `{ ... }` de métodos listados em ignoreMembers preservando linhas."""
    if not ignore_members:
        return cleaned
    names_alt = "|".join(re.escape(m) for m in sorted(ignore_members))
    sig_re = re.compile(rf"\b(?:public|protected|private)\b[^{{;]*?\b(?:{names_alt})\s*\([^{{;]*?\)\s*\{{")
    chars = list(cleaned)
    pos = 0
    while True:
        match = sig_re.search("".join(chars), pos)
        if not match:
            break
        brace_open = match.end() - 1
        depth = 1
        idx = brace_open + 1
        while idx < len(chars) and depth > 0:
            if chars[idx] == "{":
                depth += 1
            elif chars[idx] == "}":
                depth -= 1
                if depth == 0:
                    break
            if chars[idx] != "\n":
                chars[idx] = " "
            idx += 1
        pos = idx + 1
    return "".join(chars)


def glob_matches(rel_posix: str, patterns: list[str]) -> bool:
    for pat in patterns:
        norm = pat.lstrip("./")
        if fnmatch.fnmatch(rel_posix, norm):
            return True
        if norm.startswith("**/") and fnmatch.fnmatch(rel_posix, norm[3:]):
            return True
    return False


def find_nearest_cdd(file_path: Path, project_root: Path) -> Path | None:
    cur = file_path.parent
    root = project_root.resolve()
    while True:
        candidate = cur / "cdd.json"
        if candidate.is_file():
            return candidate
        if cur == root or cur.parent == cur:
            break
        cur = cur.parent
    return None


def load_and_validate_cdd(cdd_path: Path) -> dict:
    data = json.loads(cdd_path.read_text(encoding="utf-8"))
    missing = REQUIRED_CDD_KEYS - set(data)
    unknown = set(data) - ALLOWED_CDD_KEYS
    if missing:
        raise ValueError(f"{cdd_path}: campos obrigatórios ausentes: {sorted(missing)}")
    if unknown:
        raise ValueError(f"{cdd_path}: campos desconhecidos: {sorted(unknown)}")
    if data["unit"] not in ("class", "file"):
        raise ValueError(f"{cdd_path}: unit deve ser 'class' ou 'file'")
    if not isinstance(data["limit"], int) or data["limit"] < 1:
        raise ValueError(f"{cdd_path}: limit deve ser inteiro >= 1")
    has_tests = bool(data.get("tests"))
    if "testLimit" in data and not has_tests:
        raise ValueError(f"{cdd_path}: testLimit exige 'tests'")
    seen_ids: set[str] = set()
    for rule in data["rules"]:
        rid = rule.get("id", "")
        if not rid or rid in seen_ids:
            raise ValueError(f"{cdd_path}: id de regra ausente ou duplicado '{rid}'")
        seen_ids.add(rid)
        applies = rule.get("appliesTo", "all")
        if applies != "all" and not has_tests:
            raise ValueError(f"{cdd_path}: appliesTo='{applies}' na regra '{rid}' exige 'tests'")
    return data


def discover_project_types(project_root: Path, extra_types: set[str] | None = None) -> set[str]:
    types: set[str] = set(extra_types or set())
    for java_file in project_root.rglob("*.java"):
        if any(part in ("target", "build", ".git", "node_modules") for part in java_file.parts):
            continue
        try:
            cleaned = strip_comments_and_strings(java_file.read_text(encoding="utf-8"))
        except OSError:
            continue
        types.update(TYPE_DECL_RE.findall(cleaned))
    return types


def count_java_source(
    source: str,
    cdd: dict,
    project_types: set[str],
    is_test: bool,
) -> dict:
    cleaned = strip_comments_and_strings(source)
    declared_in_file = set(TYPE_DECL_RE.findall(cleaned))
    cleaned = strip_ignored_members(cleaned, set(cdd.get("ignoreMembers", [])))
    lines = cleaned.splitlines()

    hits: dict[str, list[tuple[int, str]]] = {r["id"]: [] for r in cdd["rules"]}
    active_rules = {
        r["id"]: r
        for r in cdd["rules"]
        if r.get("appliesTo", "all") == "all"
        or (is_test and r.get("appliesTo") == "test")
        or (not is_test and r.get("appliesTo") == "main")
    }

    seen_project_types: set[str] = set()
    external_project_types = project_types - declared_in_file
    type_word_re = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")

    do_depth_lines = 0
    for lineno, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("package ", "import ")):
            continue

        if "branch" in active_rules:
            # 'else if' conta 1; 'if' isolado conta 1; 'else' final conta 1.
            line_no_elseif = re.sub(r"\belse\s+if\b", lambda m: (hits["branch"].append((lineno, "else if")) or " "), raw_line)
            for _ in re.finditer(r"\bif\s*\(", line_no_elseif):
                hits["branch"].append((lineno, "if"))
            for _ in re.finditer(r"\belse\b", line_no_elseif):
                hits["branch"].append((lineno, "else"))

        if "switch-case" in active_rules:
            for _ in re.finditer(r"\bcase\b", raw_line):
                hits["switch-case"].append((lineno, "case"))
            # Ignora 'default' de método de interface (default Tipo nome(...)).
            for m in re.finditer(r"\bdefault\s*(:|->)", raw_line):
                hits["switch-case"].append((lineno, "default"))

        if "ternary" in active_rules:
            # Remove genéricos <...> antes de procurar '?'.
            no_generics = raw_line
            while True:
                nxt = re.sub(r"<[^<>]*>", "", no_generics)
                if nxt == no_generics:
                    break
                no_generics = nxt
            for _ in re.finditer(r"\?(?![.?])", no_generics):
                hits["ternary"].append((lineno, "?:"))

        if "loop" in active_rules:
            for _ in re.finditer(r"\bfor\s*\(", raw_line):
                hits["loop"].append((lineno, "for"))
            for _ in re.finditer(r"\bdo\s*(\{|$)", raw_line):
                hits["loop"].append((lineno, "do-while"))
                do_depth_lines += 1
            for m in re.finditer(r"\bwhile\s*\(", raw_line):
                prefix = raw_line[: m.start()].strip()
                is_closing_do = (prefix.endswith("}") or stripped.startswith("} while")) and do_depth_lines > 0
                if is_closing_do and ";" in raw_line[m.end() :]:
                    do_depth_lines -= 1
                else:
                    hits["loop"].append((lineno, "while"))

        if "exception-handling" in active_rules:
            for kw in ("try", "catch", "finally"):
                for _ in re.finditer(rf"\b{kw}\b", raw_line):
                    hits["exception-handling"].append((lineno, kw))

        if "logical-operator" in active_rules:
            for op in re.findall(r"&&|\|\|", raw_line):
                hits["logical-operator"].append((lineno, op))

        if "function-argument" in active_rules:
            # Exclui setas de switch (case ... -> ou default ->).
            is_switch_arrow = bool(re.search(r"\b(?:case\b.*|default)\s*->", raw_line))
            if not is_switch_arrow:
                for _ in re.finditer(r"->", raw_line):
                    hits["function-argument"].append((lineno, "lambda"))
            for _ in re.finditer(r"::", raw_line):
                hits["function-argument"].append((lineno, "method-ref"))
            for _ in re.finditer(r"\bnew\s+[A-Z][A-Za-z0-9_.<>]*\s*\([^;{}]*\)\s*\{", raw_line):
                hits["function-argument"].append((lineno, "anonymous-class"))

        if "project-type" in active_rules and external_project_types:
            for candidate in type_word_re.findall(raw_line):
                if candidate in external_project_types and candidate not in seen_project_types:
                    seen_project_types.add(candidate)
                    hits["project-type"].append((lineno, candidate))

    breakdown = {}
    total = 0
    unknown_rules = []
    for rule in cdd["rules"]:
        rid = rule["id"]
        if rid not in KNOWN_RULE_IDS:
            unknown_rules.append(rid)
            continue
        if rid not in active_rules:
            continue
        count = len(hits[rid])
        pts = count * int(rule["points"])
        total += pts
        if count > 0:
            breakdown[rid] = {
                "occurrences": count,
                "points_per_occurrence": int(rule["points"]),
                "subtotal": pts,
                "locations": hits[rid],
            }

    limit = int(cdd.get("testLimit", cdd["limit"])) if is_test else int(cdd["limit"])
    primary_type = next(iter(TYPE_DECL_RE.findall(cleaned)), "File")
    return {
        "unit_name": primary_type,
        "is_test": is_test,
        "total": total,
        "limit": limit,
        "status": "VIOLACAO" if total > limit else ("NO_FIO" if total == limit else "OK"),
        "breakdown": breakdown,
        "unknown_rules": unknown_rules,
    }


def git_show(project_root: Path, base_ref: str, rel_posix: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(project_root), "show", f"{base_ref}:{rel_posix}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.stdout if proc.returncode == 0 else None


def git_changed_java_files(project_root: Path, base_ref: str) -> list[Path]:
    proc = subprocess.run(
        ["git", "-C", str(project_root), "diff", "--name-only", f"{base_ref}...HEAD", "--", "*.java"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return []
    return [project_root / line.strip() for line in proc.stdout.splitlines() if line.strip() and (project_root / line.strip()).is_file()]


def run_self_test() -> int:
    template = Path(__file__).resolve().parent.parent / "templates" / "cdd.json"
    cdd = load_and_validate_cdd(template)
    sample = """
package br.com.edimilsonldutra.services;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class BookService {

    private static final Logger logger = LoggerFactory.getLogger(BookService.class);

    private final BookRepository repository;
    private final BookMapper mapper;

    public BookService(BookRepository repository, BookMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public List<BookDTO> findAll() {
        return mapper.toDtoList(repository.findAll());
    }

    public BookDTO findById(Long id) {
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        return mapper.toDto(entity);
    }

    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var entity = mapper.toEntity(book);
        return mapper.toDto(repository.save(entity));
    }

    public BookDTO update(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var entity = repository.findById(book.getId())
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        entity.setTitle(book.getTitle());
        entity.setPrice(book.getPrice());
        return mapper.toDto(repository.save(entity));
    }

    public void delete(Long id) {
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        repository.delete(entity);
    }
}
"""
    project_types = {
        "BookService",
        "BookRepository",
        "BookMapper",
        "BookDTO",
        "Book",
        "ResourceNotFoundException",
        "RequiredObjectIsNullException",
    }
    res = count_java_source(sample, cdd, project_types, is_test=False)
    assert res["total"] == 10, f"esperado total=10 no CRUD de referência, obtido={res['total']} ({res['breakdown']})"
    assert res["breakdown"]["project-type"]["subtotal"] == 5
    assert res["breakdown"]["function-argument"]["subtotal"] == 3
    assert res["breakdown"]["branch"]["subtotal"] == 2
    assert res["status"] == "OK"
    print("OK: self-test do CRUD de referência passou (10 / 12 pontos: project-type=5, function-argument=3, branch=2)")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", help="arquivos .java ou pastas a analisar")
    parser.add_argument("--project", default=".", help="raiz do repositório (padrão: diretório atual)")
    parser.add_argument("--base", help="branch ou commit base para comparar evolução (ex.: main)")
    parser.add_argument("--json", action="store_true", help="imprime resultado em JSON")
    parser.add_argument("--self-test", action="store_true", help="executa auto-teste contra o CRUD de referência")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    project_root = Path(args.project).resolve()
    files: list[Path] = []
    if args.targets:
        for raw in args.targets:
            p = Path(raw).resolve()
            if p.is_file() and p.suffix == ".java":
                files.append(p)
            elif p.is_dir():
                files.extend(sorted(p.rglob("*.java")))
    elif args.base:
        files = git_changed_java_files(project_root, args.base)
    else:
        files = sorted(project_root.rglob("*.java"))

    project_types = discover_project_types(project_root)
    cdd_cache: dict[Path, dict] = {}
    results = []
    skipped_no_cdd = []

    for java_file in files:
        try:
            rel_posix = java_file.relative_to(project_root).as_posix()
        except ValueError:
            rel_posix = java_file.as_posix()
        cdd_path = find_nearest_cdd(java_file, project_root)
        if cdd_path is None:
            skipped_no_cdd.append(rel_posix)
            continue
        if cdd_path not in cdd_cache:
            cdd_cache[cdd_path] = load_and_validate_cdd(cdd_path)
        cdd = cdd_cache[cdd_path]
        rel_to_cdd = java_file.relative_to(cdd_path.parent).as_posix()
        if glob_matches(rel_to_cdd, cdd.get("ignore", [])):
            continue
        is_test = glob_matches(rel_to_cdd, cdd.get("tests", []))
        res = count_java_source(java_file.read_text(encoding="utf-8"), cdd, project_types, is_test=is_test)
        res["file"] = rel_posix
        if args.base:
            base_src = git_show(project_root, args.base, rel_posix)
            if base_src is not None:
                base_res = count_java_source(base_src, cdd, project_types, is_test=is_test)
                res["base_total"] = base_res["total"]
                res["delta"] = res["total"] - base_res["total"]
        results.append(res)

    if args.json:
        print(json.dumps({"results": results, "uncounted": skipped_no_cdd}, ensure_ascii=False, indent=2))
        return 0

    violations = [r for r in results if r["status"] in ("VIOLACAO", "NO_FIO")]
    if not violations:
        print("CDD: nenhuma classe acima do limite.")
    for r in violations:
        kind = "teste" if r["is_test"] else "produção"
        label = "VIOLAÇÃO" if r["status"] == "VIOLACAO" else "NO FIO"
        base_note = ""
        if "base_total" in r:
            sign = "+" if r["delta"] >= 0 else ""
            base_note = f" · base: {r['base_total']} ({sign}{r['delta']} neste PR)"
        print(f"{r['unit_name']} — {r['file']}")
        print(f"CDD: {r['total']} / {r['limit']} ({kind}) — {label}{base_note}")
        for rid, info in r["breakdown"].items():
            locs = ", ".join(f"L{ln}({tok})" for ln, tok in info["locations"][:8])
            more = f" (+{len(info['locations']) - 8})" if len(info["locations"]) > 8 else ""
            print(f"  - {rid}: {info['occurrences']} × {info['points_per_occurrence']} = {info['subtotal']} [{locs}{more}]")
        if r["unknown_rules"]:
            print(f"  - Sem suporte automático (conferir manualmente): {', '.join(r['unknown_rules'])}")
        print()

    if skipped_no_cdd:
        print("Não contados (sem cdd.json aplicável):")
        for item in skipped_no_cdd:
            print(f"  - {item}")
    return 1 if any(r["status"] == "VIOLACAO" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
