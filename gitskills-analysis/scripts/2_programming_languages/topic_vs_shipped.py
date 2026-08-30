"""A skill about Rust is a Python program.

The article's central cut. For each language, take the skills that mention
it AND ship code at all, then ask what they actually ship. If a skill about
Rust shipped Rust, the two columns would match. They do not, and how badly
they fail to match depends on the language.

Restricting to code-shipping skills is what makes this a fair question. Most
skills ship nothing, and "skills about Rust mostly ship no code" is already
covered by composition.py. The question here is: given that this skill ships
code, is the code in the language the skill is about?

Two cautions on reading it:

- Mention patterns are loose by design (see languages.py). `ts` and `js`
  especially will pull in false positives, so TypeScript and JavaScript
  topic pools are ceilings.
- The small-language rows have tiny denominators even at full corpus,
  because both conditions have to hold at once. Every row prints its n and
  a Wilson interval on the ships-its-own-language share; do not quote a row
  whose interval spans a factor of two.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import EXT2LANG, MENTIONS, ext_case_sql

MIN_CELL = 20
# Ordered so the argument reads top to bottom: the languages people build
# software in, then the languages people build agent tooling in.
ORDER = ["Rust", "Java", "C/C++", "SQL", "Go", "C#", "Swift", "PHP", "Kotlin",
         "TypeScript", "JavaScript", "Shell/Bash", "Python"]

con = connect(duckdb.connect)

con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim AS
    SELECT repo_full_name, path, lower(content) AS text
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE shipped AS
    SELECT DISTINCT repo_full_name, artifact_path,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
      AND {ext_case_sql('entry_name', EXT2LANG, '')} <> ''
""")
con.execute("""
    CREATE OR REPLACE TEMP TABLE coders AS
    SELECT p.repo_full_name, p.path, p.text,
           list(s.lang) AS langs
    FROM prim p JOIN shipped s
      ON p.repo_full_name = s.repo_full_name AND p.path = s.artifact_path
    GROUP BY 1, 2, 3
""")

n_all = con.execute("SELECT count(*) FROM prim").fetchone()[0]
n_cod = con.execute("SELECT count(*) FROM coders").fetchone()[0]
print(f"=== {scale()} ===")
print(f"  skills: {n_all:,}   of which ship any code: {n_cod:,} "
      f"({100 * n_cod / n_all:.1f}%)\n")

print("=== skills that mention language X and ship code: what do they ship? ===")
print(f"  {'topic':<13}{'n':>7}{'ships X':>9}{'%':>8}{'ships Py':>10}{'%':>8}"
      f"{'Py:X':>8}   95% CI on ships X")
for lang in ORDER:
    pat = MENTIONS.get(lang)
    if not pat:
        continue
    row = con.execute(f"""
        SELECT count(*) n,
               count(*) FILTER (WHERE list_contains(langs, '{lang}')) ship_x,
               count(*) FILTER (WHERE list_contains(langs, 'Python')) ship_py
        FROM coders WHERE regexp_matches(text, '{pat}')
    """).fetchone()
    n, sx, sp = row
    if n < MIN_CELL:
        print(f"  {lang:<13}{n:>7}   below n={MIN_CELL}, not reported")
        continue
    lo, hi = wilson(sx, n)
    ratio = f"{sp / sx:>7.1f}x" if sx else "     inf"
    print(f"  {lang:<13}{n:>7}{sx:>9}{100 * sx / n:>7.1f}%{sp:>10}"
          f"{100 * sp / n:>7.1f}%{ratio}   [{100 * lo:4.1f},{100 * hi:5.1f}]")

print("\n  A row where 'ships Py' beats 'ships X' is a skill about one language")
print("  written in another. Python and the web languages ship themselves;")
print("  the systems and enterprise languages are subject matter, not medium.")

print("\n=== the same gap, over all skills rather than code-shippers ===")
print("  mention share against authoring share, which is what lang_refs.py reports")
print(f"  {'language':<13}{'mentions':>10}{'%':>8}{'ships':>8}{'%':>8}{'mention:ship':>14}")
for lang in sorted(MENTIONS):
    pat = MENTIONS[lang]
    m = con.execute(
        f"SELECT count(*) FROM prim WHERE regexp_matches(text, '{pat}')").fetchone()[0]
    a = con.execute(f"""
        SELECT count(*) FROM coders WHERE list_contains(langs, '{lang}')
    """).fetchone()[0]
    if not m:
        continue
    ratio = f"{m / a:>13.1f}x" if a else "          inf"
    print(f"  {lang:<13}{m:>10,}{100 * m / n_all:>7.1f}%{a:>8,}"
          f"{100 * a / n_all:>7.1f}%{ratio}")
