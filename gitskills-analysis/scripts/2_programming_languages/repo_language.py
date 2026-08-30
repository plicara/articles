"""When a Rust project ships a skill, what language is the skill written in?

The strongest form of the article's central claim, because it involves no
text at all. GitHub labels each repository with a primary language. This asks
what language the code inside that repository's skills is written in, and
compares it to the repository's own.

Independent of topic_vs_shipped.py by construction. That one reads the
SKILL.md prose for a language name, so it inherits every collision the
mention patterns carry. This one uses only the repository's label and the
extensions on disk. If both say the same thing, the finding is not an
artifact of either.

Two measurement notes:

GitHub's language names are not this project's. It writes Shell where
languages.py writes Shell/Bash, C++ where we write C/C++, and Jupyter
Notebook for what is Python on disk. Comparing the raw strings silently
reported a flat 0% self-shipping for those repositories, which is a naming
artifact, so ALIAS normalises before comparing.

Root-level skills are excluded. A SKILL.md at the repository root has the
whole project as its siblings, so of course its "skill code" matches the
repository's language: it IS the repository. That inflates self-shipping for
exactly the rows this script is about. composition.py quantifies the effect.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import EXT2LANG, ext_case_sql

MIN_CELL = 300

ALIAS = {
    "Shell": "Shell/Bash", "HTML": "HTML/CSS", "CSS": "HTML/CSS",
    "SCSS": "HTML/CSS", "Less": "HTML/CSS", "C++": "C/C++", "C": "C/C++",
    "Jupyter Notebook": "Python",
}

con = connect(duckdb.connect)

alias_sql = ("CASE " + " ".join(f"WHEN r.language = '{k}' THEN '{v}'"
                                for k, v in ALIAS.items())
             + " ELSE r.language END")

con.execute(f"""
    CREATE OR REPLACE TEMP TABLE ships AS
    SELECT repo_full_name, artifact_path,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
      AND {ext_case_sql('entry_name', EXT2LANG, '')} <> ''
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE coded AS
    SELECT {alias_sql} AS repo_lang,
           a.repo_full_name, a.path,
           list(DISTINCT s.lang) AS langs
    FROM {source('artifacts')} a
    JOIN {source('repos')} r ON r.full_name = a.repo_full_name
    JOIN ships s ON a.repo_full_name = s.repo_full_name
                AND a.path = s.artifact_path
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
      AND r.language IS NOT NULL AND r.language <> ''
      AND length(a.path) - length(replace(a.path, '/', '')) > 0
    GROUP BY 1, 2, 3
""")

n_all = con.execute("SELECT count(*) FROM coded").fetchone()[0]
print(f"=== {scale()} ===")
print(f"  code-shipping skills in a language-labelled repository: {n_all:,}")
print("  (root-level skills excluded: their siblings are the whole project)\n")

print(f"  {'repo language':<16}{'skills':>9}{'ships own':>11}{'ships Python':>14}"
      f"{'Py:own':>9}   95% CI on ships own")
rows = con.execute(f"""
    SELECT repo_lang, count(*) n,
           count(*) FILTER (WHERE list_contains(langs, repo_lang)) same,
           count(*) FILTER (WHERE list_contains(langs, 'Python')) py
    FROM coded GROUP BY 1
    HAVING count(*) >= {MIN_CELL}
    ORDER BY same::DOUBLE / count(*) DESC
""").fetchall()
for lang, n, same, py in rows:
    lo, hi = wilson(same, n)
    ratio = f"{py / same:>8.1f}x" if same else "     inf"
    print(f"  {lang:<16}{n:>9,}{100 * same / n:>10.1f}%{100 * py / n:>13.1f}%"
          f"{ratio}   [{100 * lo:4.1f},{100 * hi:5.1f}]")

print("\n  Read top to bottom: the scripting languages are their own skills'")
print("  medium, the compiled ones are only their subject. A repository whose")
print("  own code is C or C++ is several times more likely to ship a skill")
print("  written in Python than one written in the language it is about.")
