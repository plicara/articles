"""Which skills get copied, and does language predict it?

Copying needs no commit history, so unlike the temporal cuts this runs on
100% of distinct contents rather than the dated 23%.

The threat to this measurement is mirroring. A handful of repositories in
this corpus are registries and mirrors that vendor thousands of skills
wholesale; counting their rows as "copies" would measure archiving rather
than reuse. Lopes et al. (DejaVu, OOPSLA 2017) hit the same problem at
GitHub scale, where 70% of code is duplicated largely through forks and
vendored dependencies.

So the copy count is reported three ways, weakest assumption last:
  1. every occurrence, as stored;
  2. excluding the top-N repositories by artifact count (the aggregators);
  3. counting distinct repository OWNERS, so one actor vendoring a skill
     into ten of their own repos counts once.

A finding that survives all three is about reuse, not about mirroring.
"""

from collections import defaultdict

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

TOP_N = 10
MIN_CELL = 30
BUCKETS = [(1, 1, "1 (unique)"), (2, 2, "2"), (3, 5, "3-5"), (6, 10**9, "6+")]

con = connect(duckdb.connect)

repos = con.execute(f"""
    SELECT repo_full_name, count(*) AS n
    FROM {source('artifacts')} GROUP BY 1 ORDER BY n DESC
""").fetchall()
total_rows = sum(n for _, n in repos)
hhi = sum((n / total_rows) ** 2 for _, n in repos)
top = repos[:TOP_N]

print("=== how concentrated is the corpus? ===")
print(f"  repositories                  : {len(repos)}")
print(f"  top-{TOP_N} share of all artifacts : "
      f"{100 * sum(n for _, n in top) / total_rows:.1f}%")
print(f"  HHI                           : {hhi:.5f}")
print(f"  effective repositories (1/HHI): {1 / hhi:.1f}")
print("  -> the corpus has the concentration of a corpus this much smaller;")
print("     the largest holders are registries and mirrors, not authors")
for name, n in top[:5]:
    print(f"    {n:>6}  {name}")

agg_list = ",".join("'" + name.replace("'", "''") + "'" for name, _ in top)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE copies AS
    SELECT file_sha,
           count(*)                                            AS copies_all,
           count(*) FILTER (WHERE repo_full_name NOT IN ({agg_list}))
                                                               AS copies_noagg,
           count(DISTINCT split_part(repo_full_name, '/', 1))  AS copies_owner
    FROM {source('artifacts')}
    GROUP BY file_sha
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE d AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           c.copies_all, c.copies_noagg, c.copies_owner,
           a.repo_full_name IN ({agg_list}) AS in_aggregator
    FROM {source('artifacts')} a JOIN copies c USING (file_sha)
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")

ident = identifier()
recs = []
for prose, ca, cn, co, in_agg in con.execute(f"""
        SELECT prose, copies_all, copies_noagg, copies_owner, in_aggregator
        FROM d""").fetchall():
    code = classify(ident, prose)
    if code and code != "uncertain":
        recs.append({"non_en": is_non_english(code), "all": ca,
                     "noagg": cn, "owner": co})

print(f"\n{len(recs)} classified distinct contents")

for field, label in (("all", "1. every occurrence, as stored"),
                     ("noagg", f"2. excluding the top-{TOP_N} aggregator repos"),
                     ("owner", "3. counting distinct repository owners")):
    print(f"\n=== {label} ===")
    print(f"  {'copies':<12}{'n':>7}   non-English")
    for lo, hi, blabel in BUCKETS:
        sel = [r for r in recs if lo <= r[field] <= hi]
        if len(sel) < MIN_CELL:
            continue
        k = sum(r["non_en"] for r in sel)
        l, h = wilson(k, len(sel))
        print(f"  {blabel:<12}{len(sel):>7}   {100 * k / len(sel):>5.1f}%  "
              f"[{100*l:>4.1f}, {100*h:>5.1f}]")

print("\n=== are the aggregators themselves English-skewed? ===")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE allrows AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           repo_full_name IN ({agg_list}) AS in_aggregator
    FROM {source('artifacts')} WHERE content IS NOT NULL
""")
tally = defaultdict(lambda: [0, 0])
for prose, in_agg in con.execute(
        "SELECT prose, in_aggregator FROM allrows").fetchall():
    code = classify(ident, prose)
    if code and code != "uncertain":
        tally[bool(in_agg)][0] += 1
        tally[bool(in_agg)][1] += code != "en"
for in_agg, (n, ne) in sorted(tally.items()):
    l, h = wilson(ne, n)
    name = "aggregator repos" if in_agg else "ordinary repos"
    print(f"  {name:<20}{n:>7}   non-English {100 * ne / n:>5.1f}%  "
          f"[{100*l:.1f}, {100*h:.1f}]")
print("  -> aggregators are more English than the corpus, which is exactly")
print("     why the copy result is reported with them removed as well")
