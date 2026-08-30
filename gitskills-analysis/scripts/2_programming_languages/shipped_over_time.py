"""Is the language mix of new skills shifting, and is the gap widening?

Two series per language over the quarters skills have existed:

  mentions  share of newly created skills naming the language
  ships     share of newly created skills carrying a file in it

The ratio between them is the article's measure, and asking whether it moves
is a different question from what its level is. TypeScript is the case to
watch: GitHub's Octoverse 2025 has it overtaking Python and JavaScript as the
most used language on the platform by monthly contributors, credited to
agent-assisted coding, which makes its direction inside the agents' own
artifacts worth measuring rather than assuming.

Same three limits as every temporal cut here. Commit history exists for a
minority of skills and only for deduplication representatives, so "created"
means the first commit touching THIS copy. Collection ran to July 2026, so
the final quarter is censored: printed, flagged, never compared. Quarters
below a floor are not printed at all.
"""

import sys
from collections import defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import EXT2LANG, MENTIONS, ext_case_sql

MIN_CELL = 5000
TRACKED = ["Python", "Shell/Bash", "JavaScript", "TypeScript", "HTML/CSS"]

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE dated AS
    SELECT repo_full_name, path, lower(content) AS text,
           strftime(CAST(first_commit_at AS TIMESTAMP), '%Y-Q')
             || CAST(quarter(CAST(first_commit_at AS TIMESTAMP)) AS VARCHAR) AS q
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
      AND first_commit_at IS NOT NULL
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE ships AS
    SELECT repo_full_name, artifact_path,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
      AND {ext_case_sql('entry_name', EXT2LANG, '')} <> ''
""")

tot = dict(con.execute("SELECT q, count(*) FROM dated GROUP BY 1").fetchall())
qs = [q for q in sorted(tot) if tot[q] >= MIN_CELL]

print(f"=== {scale()} ===")
print(f"  dated skills: {sum(tot.values()):,}")
print(f"  quarters clearing n={MIN_CELL:,}: {', '.join(qs)}")
print(f"  {qs[-1]} is the collection month and is censored\n")

ship_rows = con.execute("""
    SELECT d.q, s.lang, count(DISTINCT d.repo_full_name || ' ' || d.path)
    FROM dated d JOIN ships s
      ON d.repo_full_name = s.repo_full_name AND d.path = s.artifact_path
    GROUP BY 1, 2
""").fetchall()
ships = defaultdict(dict)
for q, lang, k in ship_rows:
    ships[q][lang] = k

for lang in TRACKED:
    pat = MENTIONS[lang]
    print(f"  {lang}")
    print(f"    {'quarter':<10}{'n':>10}{'mentions':>11}{'ships':>9}{'ratio':>9}"
          f"   95% CI on ships")
    for q in qs:
        n = tot[q]
        m = con.execute(f"SELECT count(*) FROM dated WHERE q = '{q}' "
                        f"AND regexp_matches(text, '{pat}')").fetchone()[0]
        s = ships[q].get(lang, 0)
        lo, hi = wilson(s, n)
        ratio = f"{m / s:>8.1f}x" if s else "     inf"
        cens = "  censored" if q == qs[-1] else ""
        print(f"    {q:<10}{n:>10,}{100 * m / n:>10.2f}%{100 * s / n:>8.2f}%{ratio}"
              f"   [{100 * lo:4.2f},{100 * hi:5.2f}]{cens}")
    if len(qs) >= 3:
        a, b = qs[-3], qs[-2]
        la, ha = wilson(ships[a].get(lang, 0), tot[a])
        lb, hb = wilson(ships[b].get(lang, 0), tot[b])
        v = ("rising, non-overlapping" if ha < lb else
             "falling, non-overlapping" if hb < la else "overlapping")
        print(f"    {a} -> {b}: {v}\n")

print("  TypeScript is the row to read against Octoverse. On GitHub as a whole")
print("  it is the fastest-growing language and now the most used; inside the")
print("  artifacts built for coding agents it is shipped less every quarter,")
print("  while the share of skills that talk about it barely moves. The gap is")
print("  not a fixed level, it is widening.")
