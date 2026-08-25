"""Is the non-English rise real, or an artifact of how the subsample was built?

language_over_time.py finds non-English share rising between 2026-Q1 and
2026-Q2. Two things could manufacture that without any real change:

1. Copy-count selection. Commit history was fetched for skills carrying
   systematically MORE verbatim copies, and copy count turns out to predict
   language strongly -- widely copied skills are far more English. That is a
   real confound, so the trend has to be reproduced with it held fixed.
2. Repo concentration. A single author bulk-committing many same-language
   skills in one quarter would move a share that is counted per skill.

Note on terminology, because getting this wrong once already cost us a
round of analysis: a *copy* is another repository holding byte-identical
SKILL.md content, counted by grouping on file_sha. That is NOT
sibling_count, which counts files bundled alongside SKILL.md in its folder
(references/, scripts/). The two are uncorrelated (r = -0.003).
"""

from collections import defaultdict

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

MIN_CELL = 30

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE d AS
    WITH copies AS (
        SELECT file_sha, count(*) AS n_copies FROM {source('artifacts')} GROUP BY file_sha
    )
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           CAST(a.first_commit_at AS TIMESTAMP) AS created,
           c.n_copies,
           a.repo_full_name
    FROM {source('artifacts')} a JOIN copies c USING (file_sha)
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
      AND a.first_commit_at IS NOT NULL
""")

ident = identifier()
recs = []
for prose, created, copies, repo in con.execute(
        "SELECT prose, created, n_copies, repo_full_name FROM d").fetchall():
    code = classify(ident, prose)
    if code is None:
        continue
    recs.append({
        "q": f"{created.year}-Q{(created.month - 1) // 3 + 1}",
        "non_en": is_non_english(code),
        "copies": copies,
        "repo": repo,
    })

by_q = defaultdict(list)
for r in recs:
    by_q[r["q"]].append(r)
quarters = sorted(by_q)


def share(rows):
    ne = sum(r["non_en"] for r in rows)
    lo, hi = wilson(ne, len(rows))
    return f"{100 * ne / len(rows):>5.1f}%  [{100*lo:>4.1f}, {100*hi:>5.1f}]  n={len(rows)}"


print("=== 1. does verbatim copying predict language? ===")
print(f"  {'copies':<12}non-English")
for lo, hi, label in [(1, 1, "1 (unique)"), (2, 2, "2"), (3, 5, "3-5"),
                      (6, 10**9, "6+")]:
    sel = [r for r in recs if lo <= r["copies"] <= hi]
    if len(sel) >= MIN_CELL:
        print(f"  {label:<12}{share(sel)}")
print("  -> English skills are copied far more, so any subsample weighted")
print("     toward copied skills under-counts non-English. This is a real")
print("     confound and the trend must be reproduced without it.")

print("\n=== 2. trend among never-copied skills (confound held fixed) ===")
print(f"  {'quarter':<9}non-English")
for q in quarters:
    sel = [r for r in by_q[q] if r["copies"] == 1]
    if len(sel) >= MIN_CELL:
        print(f"  {q:<9}{share(sel)}")

print("\n=== 3. trend counting each repository once ===")
print(f"  {'quarter':<9}non-English")
for q in quarters:
    seen, sel = set(), []
    for r in by_q[q]:
        if r["repo"] not in seen:
            seen.add(r["repo"])
            sel.append(r)
    if len(sel) >= MIN_CELL:
        print(f"  {q:<9}{share(sel)}")

print("\n=== 4. uncontrolled trend, for comparison ===")
print(f"  {'quarter':<9}non-English")
for q in quarters:
    if len(by_q[q]) >= MIN_CELL:
        print(f"  {q:<9}{share(by_q[q])}")

print("\n=== 5. how concentrated is the dated subsample? ===")
per_repo = defaultdict(int)
for r in recs:
    per_repo[r["repo"]] += 1
print(f"  {len(recs)} dated skills across {len(per_repo)} repositories")
for repo, n in sorted(per_repo.items(), key=lambda kv: -kv[1])[:5]:
    print(f"  {n:>5}  {repo}")
