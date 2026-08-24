"""Which programming languages do skills reference?

Counts distinct representative skills whose SKILL.md text mentions each
language (word-boundary match, case-insensitive, anywhere in the file --
front matter and fenced code included, since a ```python block is itself
a signal the skill targets Python). A skill can reference several
languages, so columns don't sum to 100%.

Deliberate measurement choices:
- bare "go" is unmeasurable noise in English prose -> Go is measured via
  toolchain signals (golang, go get/build/test/run/mod/install/fmt/vet);
- plain "c" is excluded for the same reason -> C/C++ uses c++/gcc/clang;
- \b makes java vs javascript safe without lookahead (RE2 has none).
"""

import os
from pathlib import Path

import duckdb

DB = os.environ.get(
    "GITSKILLS_DB",
    str(Path(__file__).resolve().parent.parent / "data" / "agent_skills_sample.db"),
)
# Full dataset on a Colab VM: GITSKILLS_DB=/content/agent_skills_release.db

PATTERNS = {
    "Python":     r"\bpython\b",
    "JavaScript": r"\bjavascript\b|\bnode\.?js\b|\bjs\b",
    "TypeScript": r"\btypescript\b|\bts\b",
    "Java":       r"\bjava\b",
    "Shell/Bash": r"\bbash\b|\bzsh\b|shell script",
    "Rust":       r"\brust\b|\bcargo\b",
    "SQL":        r"\bsql\b",
    "HTML/CSS":   r"\bhtml\b|\bcss\b",
    "C/C++":      r"\bc\+\+|\bgcc\b|\bclang\b",
    "Go":         r"\bgolang\b|\bgo (get|build|test|run|mod|install|fmt|vet)\b",
    "PHP":        r"\bphp\b",
    "Ruby":       r"\bruby\b|\bgemfile\b",
    "Swift":      r"\bswift\b",
    "Kotlin":     r"\bkotlin\b",
    "Scala":      r"\bscala\b",
    "Perl":       r"\bperl\b",
    "Haskell":    r"\bhaskell\b",
}

con = duckdb.connect()
con.execute("INSTALL sqlite")
con.execute("LOAD sqlite")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE docs AS
    SELECT lower(content) AS text
    FROM sqlite_scan('{DB}', 'artifacts')
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")

cols = ",\n       ".join(
    f"COUNT(*) FILTER (WHERE regexp_matches(text, '{p}')) AS \"{n}\""
    for n, p in PATTERNS.items()
)
row = con.execute(f"SELECT {cols}, COUNT(*) AS total FROM docs").fetchone()
total = row[-1]

ranked = sorted(zip(PATTERNS, row[:-1]), key=lambda kv: -kv[1])
print(f"{total} distinct skills\n")
print("== MENTIONS: the language name appears somewhere in the file ==")
print(f"{'language':<14}{'skills':>8}{'%':>7}")
for name, n in ranked:
    print(f"{name:<14}{n:>8}{100 * n / total:>6.1f}%")

# Mentioning a language and writing one are different questions, and
# conflating them is easy: a skill that pastes a shell command mentions
# bash without targeting it. Authoring is measured from the files actually
# bundled in the skill folder, which is a far stricter signal.
EXTENSIONS = {
    "Shell/Bash": ["%.sh", "%.bash", "%.zsh"],
    "Python":     ["%.py"],
    "JavaScript": ["%.js", "%.mjs", "%.cjs"],
    "TypeScript": ["%.ts", "%.tsx"],
    "Ruby":       ["%.rb"],
    "Go":         ["%.go"],
    "Rust":       ["%.rs"],
}
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim AS
    SELECT repo_full_name, path FROM sqlite_scan('{DB}', 'artifacts')
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE sib AS
    SELECT repo_full_name, artifact_path, lower(entry_name) AS nm
    FROM sqlite_scan('{DB}', 'artifact_siblings')
    WHERE entry_type = 'file'
""")

print("\n== AUTHORING: the skill folder ships a file in that language ==")
print(f"{'language':<14}{'skills':>8}{'%':>7}")
authored = []
for name, globs in EXTENSIONS.items():
    where = " OR ".join(f"s.nm LIKE '{g}'" for g in globs)
    n = con.execute(f"""
        SELECT count(DISTINCT p.repo_full_name || '/' || p.path)
        FROM prim p JOIN sib s
          ON p.repo_full_name = s.repo_full_name AND p.path = s.artifact_path
        WHERE {where}
    """).fetchone()[0]
    authored.append((name, n))
for name, n in sorted(authored, key=lambda kv: -kv[1]):
    print(f"{name:<14}{n:>8}{100 * n / total:>6.1f}%")
print("\nMentions and authoring rank differently: Shell leads on mentions"
      "\nbecause skills paste commands, Python leads on authoring.")
