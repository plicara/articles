"""Does the natural-language mix of skills shift over time?

The dataset carries per-skill commit history, so each skill has a creation
date (first_commit_at). That turns the language distribution into a time
series and lets us ask whether skills are getting less English as the
format spreads -- the trend arXiv:2602.19446 (ICSE '26) reports for GitHub
artifacts at large, where non-English content grew 4.2% -> 11.3% over a
decade.

Three limits are reported inline rather than buried, because they bound
every claim below:

1. Coverage. Commit history was fetched for a minority of skills, and only
   for deduplication representatives -- never for copies. So this is a
   subsample, and "creation" means the first commit touching THIS copy, not
   the first appearance of the content anywhere.
2. Selection. The dated subsample is not random: it carries systematically
   MORE verbatim copies than the undated remainder (printed below), and
   copy count predicts language -- widely copied skills are far more
   English. So the dated subsample skews English, and trend claims need
   the copy-controlled replication in trend_robustness.py.
3. Truncation. Collection ran in July 2026, so the final period is censored
   and is excluded from trend comparisons.

Cell counts get small once split by period and language, so every share is
printed with a 95% Wilson interval. Non-overlapping intervals are the only
differences worth talking about.
"""

from collections import defaultdict

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, NAMES, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

DB = db_path()
MIN_CELL = 30  # below this a period's share is printed but not compared

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE dated AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           CAST(first_commit_at AS TIMESTAMP) AS created,
           nullif(trim(coalesce(first_commit_author_type, '')), '') AS author_type
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
      AND first_commit_at IS NOT NULL
""")

# A "copy" is another repository holding byte-identical SKILL.md content.
# This is NOT sibling_count, which counts files bundled alongside SKILL.md
# (references/, scripts/) and is uncorrelated with copying.
cov = con.execute(f"""
    WITH copies AS (
        SELECT file_sha, count(*) AS n_copies
        FROM {source('artifacts')} GROUP BY file_sha
    ),
    prim AS (
        SELECT a.first_commit_at, a.discovered_at, c.n_copies
        FROM {source('artifacts')} a JOIN copies c USING (file_sha)
        WHERE a.dedup_primary = 1
    )
    SELECT count(*) AS contents,
           count(first_commit_at) AS dated,
           round(avg(n_copies) FILTER (WHERE first_commit_at IS NOT NULL), 2),
           round(avg(n_copies) FILTER (WHERE first_commit_at IS NULL), 2),
           max(discovered_at)
    FROM prim
""").fetchone()
contents, dated, cop_d, cop_u, collected = cov

print("=== coverage and selection ===")
print(f"  distinct contents                : {contents}")
print(f"  with commit history (dated)      : {dated} ({100 * dated / contents:.1f}%)")
print(f"  mean verbatim copies, dated/undated: {cop_d} vs {cop_u}")
print(f"  collected through                : {collected[:10]}")
if cop_d and cop_u and cop_d > cop_u:
    print("  -> dated skills are more copied, and copied skills skew English,")
    print("     so this subsample under-represents non-English skills")

ident = identifier()
rows = con.execute("SELECT prose, created, author_type FROM dated").fetchall()

by_month = defaultdict(lambda: defaultdict(int))
by_quarter = defaultdict(lambda: defaultdict(int))
authors = defaultdict(lambda: defaultdict(int))

for prose, created, author_type in rows:
    code = classify(ident, prose)
    if code is None:
        continue
    month = f"{created.year}-{created.month:02d}"
    quarter = f"{created.year}-Q{(created.month - 1) // 3 + 1}"
    for bucket, key in ((by_month, month), (by_quarter, quarter)):
        bucket[key]["n"] += 1
        bucket[key]["en" if code == "en" else "other"] += 1
        if is_non_english(code):
            bucket[key]["non_en"] += 1
        if code == "zh":
            bucket[key]["zh"] += 1
        if code == "uncertain":
            bucket[key]["uncertain"] += 1
    authors[quarter][author_type or "(unknown)"] += 1

months = sorted(by_month)
quarters = sorted(by_quarter)
last_month, last_quarter = months[-1], quarters[-1]

print("\n=== skills created per month ===")
print("  Reported monthly as well as quarterly so the aggregation is not")
print("  doing the work: monthly cells are noisier but show the same rise.")
print(f"  {'month':<10}{'skills':>8}{'English':>9}{'non-Eng':>9}   non-English share")
for m in months:
    c = by_month[m]
    n = c["n"]
    if n >= MIN_CELL:
        lo, hi = wilson(c["non_en"], n)
        share = (f"{100 * c['non_en'] / n:>5.1f}%  "
                 f"[{100*lo:>4.1f}, {100*hi:>5.1f}]")
    else:
        share = f"n<{MIN_CELL}"
    flag = "  partial" if m == last_month else ""
    print(f"  {m:<10}{n:>8}{c['en']:>9}{c['non_en']:>9}   {share}{flag}")

print("\n=== language share by quarter, 95% Wilson interval ===")
print(f"  {'quarter':<9}{'n':>6}   {'non-English':<22}{'Chinese':<22}")
for q in quarters:
    c = by_quarter[q]
    n = c["n"]
    lo_ne, hi_ne = wilson(c["non_en"], n)
    lo_zh, hi_zh = wilson(c["zh"], n)
    ne = f"{100 * c['non_en'] / n:>5.1f}%  [{100*lo_ne:>4.1f},{100*hi_ne:>5.1f}]"
    zh = f"{100 * c['zh'] / n:>5.1f}%  [{100*lo_zh:>4.1f},{100*hi_zh:>5.1f}]"
    note = ""
    if q == last_quarter:
        note = "  partial"
    elif n < MIN_CELL:
        note = f"  n<{MIN_CELL}"
    print(f"  {q:<9}{n:>6}   {ne:<22}{zh:<22}{note}")

# Compare the two most recent complete quarters that clear MIN_CELL.
usable = [q for q in quarters
          if q != last_quarter and by_quarter[q]["n"] >= MIN_CELL]
print("\n=== trend test ===")
if len(usable) < 2:
    print("  fewer than two complete quarters clear the cell-size floor;"
          " no trend claim supported")
else:
    a, b = usable[-2], usable[-1]
    ca, cb = by_quarter[a], by_quarter[b]
    lo_a, hi_a = wilson(ca["non_en"], ca["n"])
    lo_b, hi_b = wilson(cb["non_en"], cb["n"])
    print(f"  non-English {a}: {100*ca['non_en']/ca['n']:.1f}% "
          f"[{100*lo_a:.1f}, {100*hi_a:.1f}]  (n={ca['n']})")
    print(f"  non-English {b}: {100*cb['non_en']/cb['n']:.1f}% "
          f"[{100*lo_b:.1f}, {100*hi_b:.1f}]  (n={cb['n']})")
    if hi_a < lo_b:
        print("  -> non-English share rose; intervals do not overlap")
    elif hi_b < lo_a:
        print("  -> non-English share fell; intervals do not overlap")
    else:
        print("  -> intervals overlap; no significant change at this sample size")

print("\n=== first-commit author type by quarter (RQ 1d, machine authorship) ===")
kinds = sorted({k for q in authors.values() for k in q})
print("  " + f"{'quarter':<9}" + "".join(f"{k:>14}" for k in kinds))
for q in quarters:
    print(f"  {q:<9}" + "".join(f"{authors[q].get(k, 0):>14}" for k in kinds))
print("\n  note: a Bot-attributed first commit is a weak proxy for machine")
print("  authorship -- agent-written skills are usually committed by a human.")
