"""One definition of "which programming language", shared by article 02.

Two different questions, kept apart on purpose, because conflating them is
the mistake this article is about.

  MENTIONS   the language name appears in the SKILL.md text. A skill that
             pastes one `bash` command mentions Bash without targeting it.
  EXT2LANG   the skill folder ships a file in that language. Far stricter,
             and the only one of the two that means the skill was written
             in that language.

The gap between them is uneven by language, which is the finding: skills
about Python ship Python, skills about Rust ship Python.

Measurement choices, RE2-safe (no lookahead or lookbehind), so the same
patterns run in DuckDB and in Python:
- bare `go` is unmeasurable noise in English prose, so Go is matched on
  toolchain signals (golang, go get/build/test/run/mod/install/fmt/vet);
- bare `c` is excluded for the same reason; C/C++ uses c++/gcc/clang;
- `\\b` separates java from javascript without lookahead;
- `ts` and `js` are deliberately included for TypeScript and JavaScript and
  are the loosest patterns here, which is part of why those two carry such
  large mention-to-authoring gaps. Treat their mention counts as ceilings.

Counting rule: **count skills or owners, never files.** File counts are
severely concentrated. In the 13,000-skill sample, 668 `.go` files come from
11 skills and 236 `.ex` files from a single one, so a file histogram reports
one repository vendoring a codebase as a language trend.
"""

import re

MENTIONS = {
    "Python":     r"\bpython\b",
    "JavaScript": r"\bjavascript\b|\bnode\.?js\b|\bjs\b",
    "TypeScript": r"\btypescript\b|\bts\b",
    "Shell/Bash": r"\bbash\b|\bzsh\b|shell script",
    "HTML/CSS":   r"\bhtml\b|\bcss\b",
    "SQL":        r"\bsql\b",
    "Rust":       r"\brust\b|\bcargo\b",
    "Java":       r"\bjava\b",
    "Go":         r"\bgolang\b|\bgo (get|build|test|run|mod|install|fmt|vet)\b",
    "C#":         r"\bc#|\bdotnet\b|\b\.net\b",
    "PowerShell": r"\bpowershell\b",
    "C/C++":      r"\bc\+\+|\bgcc\b|\bclang\b",
    "PHP":        r"\bphp\b",
    "Swift":      r"\bswift\b",
    "Ruby":       r"\bruby\b|\bgemfile\b",
    "Kotlin":     r"\bkotlin\b",
    "R":          r"\brstudio\b|\bggplot\b|\br language\b",
    "Elixir":     r"\belixir\b",
    "Lua":        r"\blua\b",
    "Perl":       r"\bperl\b",
    "Scala":      r"\bscala\b",
    "Haskell":    r"\bhaskell\b",
}

# The map lang_refs.py used to carry covered seven languages, which silently
# reported zero for C#, PowerShell, Elixir and R. Extensions are cheap; a
# missing one is an invisible zero.
EXT2LANG = {
    ".py": "Python", ".pyi": "Python", ".ipynb": "Python",
    ".sh": "Shell/Bash", ".bash": "Shell/Bash", ".zsh": "Shell/Bash",
    ".fish": "Shell/Bash",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".c": "C/C++", ".h": "C/C++", ".cpp": "C/C++", ".cc": "C/C++",
    ".hpp": "C/C++",
    ".cs": "C#", ".swift": "Swift", ".m": "Objective-C",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".sql": "SQL", ".r": "R", ".jl": "Julia", ".lua": "Lua", ".pl": "Perl",
    ".hs": "Haskell", ".clj": "Clojure", ".dart": "Dart", ".vim": "Vimscript",
    ".html": "HTML/CSS", ".css": "HTML/CSS", ".scss": "HTML/CSS",
}

# What a bundled file IS, beyond whether it is code. The spec names
# scripts/, references/ and assets/, so these categories are the spec's own
# shape rather than an invention.
DOCS = {".md", ".mdx", ".txt", ".rst", ".adoc"}
DATA = {".json", ".yaml", ".yml", ".csv", ".toml", ".xml", ".xsd", ".tsv",
        ".jsonl", ".ini", ".cfg"}
ASSETS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".ico", ".mp4",
          ".ttf", ".otf", ".woff", ".woff2", ".pdf"}


def ext(name: str) -> str:
    return ("." + name.rsplit(".", 1)[1].lower()) if "." in name else "(none)"


def kind(name: str) -> str:
    """Which of the spec's shapes a bundled file belongs to."""
    e = ext(name)
    if e in EXT2LANG:
        return "code"
    if e in DOCS:
        return "docs"
    if e in DATA:
        return "data/config"
    if e in ASSETS:
        return "asset"
    return "other"


def ext_case_sql(col: str, mapping: dict, default: str) -> str:
    """A CASE mapping a lowercased filename's extension to a label."""
    whens = "\n         ".join(
        f"WHEN lower({col}) LIKE '%{e}' THEN '{v}'" for e, v in mapping.items())
    return f"CASE {whens}\n         ELSE '{default}' END"


_M = {n: re.compile(p, re.I) for n, p in MENTIONS.items()}


def mentioned(text: str) -> set:
    return {n for n, rx in _M.items() if rx.search(text)}
