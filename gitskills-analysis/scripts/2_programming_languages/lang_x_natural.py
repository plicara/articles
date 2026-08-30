"""Does the language a skill is written in predict whether it ships code?

The cross with article 01, and the answer to something article 01 raised and
could not explain. It reported that non-English skills bundle scripts more
often and left the mechanism open. "Non-English" turns out to be the wrong
unit.

The natural-language column comes from scripts/classify_languages.py, which
runs article 01's cleaning, identifier and confidence floor once and caches
the result. It is not re-derived here, so this article and article 03 cannot
drift from article 01 or from each other.

Reported per skill and then **per repository owner**, and the per-owner view
is the one to publish. Article 01's aggregator lesson applies unchanged: ten
repositories hold a large share of this corpus and they are mirrors rather
than authors, so a handful of prolific owners can carry a whole row. Two
findings in the harness article did not survive this normalisation; any
finding here has to clear the same bar.

'uncertain' is excluded from both sides of every comparison. It is a
document whose language could not be pinned down, not evidence of any
language, and folding it into non-English is one of the measurement bugs
this project has already shipped once.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import _data_dir, connect, scale, source, wilson
from languages import EXT2LANG, ext_case_sql

MIN_CELL = 30
GROUPS = ["English", "Chinese", "Japanese", "Korean", "European",
          "other non-English"]

cache = (_data_dir() or Path("data")) / "derived" / "skill_language.parquet"
if not cache.exists():
    raise SystemExit(f"no language cache at {cache};"
                     " run scripts/classify_languages.py first")

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE lang AS
    SELECT repo_full_name, path, "group" AS grp,
           split_part(repo_full_name, '/', 1) AS owner
    FROM read_parquet('{cache}')
    WHERE "group" <> 'uncertain'
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE files AS
    SELECT repo_full_name, artifact_path, entry_name,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS plang
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
""")
# Root-level skills excluded, matching export_figures.py and composition.py: a
# SKILL.md at the repository root has the whole project as its siblings, so its
# "bundled code" is somebody's application rather than the skill's own.
con.execute("""
    CREATE OR REPLACE TEMP TABLE sk AS
    SELECT l.repo_full_name, l.path, l.grp, l.owner,
           count(f.entry_name) > 0                          AS bundles_any,
           count(*) FILTER (WHERE f.plang <> '') > 0         AS ships_code
    FROM lang l LEFT JOIN files f
      ON l.repo_full_name = f.repo_full_name AND l.path = f.artifact_path
    WHERE length(l.path) - length(replace(l.path, '/', '')) > 0
    GROUP BY 1, 2, 3, 4
""")

print(f"=== {scale()} ===")
print(f"  classified skills (uncertain excluded): "
      f"{con.execute('SELECT count(*) FROM sk').fetchone()[0]:,}\n")

print("=== per skill ===")
print(f"  {'language':<20}{'skills':>10}{'bundles any':>13}{'ships code':>12}")
for grp, n, b, c in con.execute("""
        SELECT grp, count(*), sum(bundles_any::INT), sum(ships_code::INT)
        FROM sk GROUP BY 1 ORDER BY count(*) DESC""").fetchall():
    print(f"  {grp:<20}{n:>10,}{100 * b / n:>12.1f}%{100 * c / n:>11.1f}%")

print("\n=== per repository owner, which is the view to publish ===")
print("  share of owners writing in this language who ship code in any skill")
print(f"  {'language':<20}{'owners':>10}{'bundles any':>13}{'ships code':>12}   95% CI (code)")
rows = con.execute("""
    WITH o AS (
        SELECT grp, owner,
               max(bundles_any::INT) AS b, max(ships_code::INT) AS c
        FROM sk GROUP BY 1, 2
    )
    SELECT grp, count(*) n, sum(b) nb, sum(c) nc
    FROM o GROUP BY 1 ORDER BY n DESC
""").fetchall()
stats = {}
for grp, n, nb, nc in rows:
    lo, hi = wilson(nc, n)
    stats[grp] = (n, nc, lo, hi)
    flag = "" if n >= MIN_CELL else f"   n<{MIN_CELL}"
    print(f"  {grp:<20}{n:>10,}{100 * nb / n:>12.1f}%{100 * nc / n:>11.1f}%"
          f"   [{100 * lo:4.1f},{100 * hi:5.1f}]{flag}")

if "English" in stats:
    en_n, en_k, en_lo, en_hi = stats["English"]
    print("\n  against English, per owner:")
    for grp in GROUPS:
        if grp == "English" or grp not in stats:
            continue
        n, k, lo, hi = stats[grp]
        if n < MIN_CELL:
            continue
        verdict = ("higher, intervals clear" if lo > en_hi else
                   "lower, intervals clear" if hi < en_lo else "overlaps English")
        print(f"    {grp:<20}{100 * k / n:>6.1f}% vs {100 * en_k / en_n:.1f}%   {verdict}")

print("\n=== is any of it one actor? owners behind each group's code-shippers ===")
for grp, n_sk, n_ow, top, top_n in con.execute("""
        WITH c AS (SELECT grp, owner, count(*) n FROM sk WHERE ships_code
                   GROUP BY 1, 2)
        SELECT grp, sum(n), count(*), arg_max(owner, n), max(n)
        FROM c GROUP BY 1 ORDER BY sum(n) DESC""").fetchall():
    print(f"  {grp:<20}{n_sk:>7,} skills across {n_ow:>6,} owners; "
          f"largest holds {top_n} ({top})")

print("\n=== which language does each population ship? ===")
con.execute("""
    CREATE OR REPLACE TEMP TABLE shipped AS
    SELECT DISTINCT l.grp, l.repo_full_name, l.path, f.plang
    FROM lang l JOIN files f
      ON l.repo_full_name = f.repo_full_name AND l.path = f.artifact_path
    WHERE f.plang <> ''
""")
for grp in GROUPS:
    tot = con.execute(
        "SELECT count(DISTINCT repo_full_name || ' ' || path) FROM shipped "
        f"WHERE grp = '{grp}'").fetchone()[0]
    if not tot:
        continue
    top = con.execute(f"""
        SELECT plang, count(DISTINCT repo_full_name || ' ' || path) n
        FROM shipped WHERE grp = '{grp}' GROUP BY 1 ORDER BY n DESC LIMIT 4
    """).fetchall()
    body = ", ".join(f"{p} {100 * n / tot:.0f}%" for p, n in top)
    flag = "" if tot >= MIN_CELL else f"   (n<{MIN_CELL}, not reportable)"
    print(f"  {grp:<20}n={tot:,}".ljust(32) + f"{body}{flag}")
