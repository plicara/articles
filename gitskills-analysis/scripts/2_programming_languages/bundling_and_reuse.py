"""Do skills that ship code get copied more than skills that are only prose?

The second half of a question the GitSkills authors pose and defer: "How
often do skills bundle executable files, and how widely are these skills
copied?" composition.py answers the first half. This is the second.

It did not resolve at sample scale, where two reasonable copy measures
disagreed on direction, so it was recorded as unresolved rather than written
up. This is the full-corpus run that decides it.

Copying is measured three ways, weakest assumption last, exactly as
reuse_by_language.py does it, and for the same reason: a great deal of what
looks like copying on GitHub is archiving. A handful of repositories vendor
thousands of skills wholesale, and counting their rows as reuse measures
mirroring instead.

  1. every occurrence, as stored
  2. excluding the top-N repositories by artifact count, the aggregators
  3. counting distinct repository OWNERS, so one actor vendoring a skill
     into ten of their own repos counts once

A finding that survives all three is about reuse. One that appears in only
the first is about mirrors.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import EXT2LANG, ext_case_sql

TOP_N = 10
MIN_CELL = 200
BUCKETS = [(1, 1, "1 (never copied)"), (2, 2, "2"), (3, 5, "3-5"),
           (6, 10 ** 9, "6+")]

con = connect(duckdb.connect)

aggregators = [r[0] for r in con.execute(f"""
    SELECT repo_full_name, count(*) n FROM {source('artifacts')}
    GROUP BY 1 ORDER BY n DESC LIMIT {TOP_N}
""").fetchall()]
agg_sql = ", ".join("'" + a.replace("'", "''") + "'" for a in aggregators)

con.execute(f"""
    CREATE OR REPLACE TEMP TABLE copies AS
    SELECT file_sha,
           count(*)                                        AS n_all,
           count(*) FILTER (WHERE repo_full_name NOT IN ({agg_sql})) AS n_noagg,
           count(DISTINCT split_part(repo_full_name, '/', 1))        AS n_owner
    FROM {source('artifacts')} GROUP BY 1
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE ships AS
    SELECT DISTINCT repo_full_name, artifact_path
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
      AND {ext_case_sql('entry_name', EXT2LANG, '')} <> ''
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim AS
    SELECT a.file_sha, c.n_all, c.n_noagg, c.n_owner,
           (s.repo_full_name IS NOT NULL) AS ships_code
    FROM {source('artifacts')} a
    JOIN copies c USING (file_sha)
    LEFT JOIN ships s
      ON a.repo_full_name = s.repo_full_name AND a.path = s.artifact_path
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")

print(f"=== {scale()} ===")
print(f"  aggregators excluded in measure 2: {', '.join(aggregators[:3])} ...\n")

for col, label in [("n_all", "every occurrence, as stored"),
                   ("n_noagg", f"excluding the top-{TOP_N} aggregator repositories"),
                   ("n_owner", "counting distinct repository OWNERS")]:
    print(f"  --- {label} ---")
    print(f"  {'copies':<20}{'skills':>12}{'ships code':>12}   95% CI")
    # Strict monotonicity is the wrong test. The 1-to-2 step is noisy because a
    # second occurrence is usually a fork or a mirror rather than reuse; what
    # the question asks is whether the widely-copied tail differs from the
    # never-copied head, so that is what gets tested.
    ends = []
    for lo, hi, name in BUCKETS:
        n, k = con.execute(f"""
            SELECT count(*), count(*) FILTER (WHERE ships_code)
            FROM prim WHERE {col} BETWEEN {lo} AND {hi}
        """).fetchone()
        if n < MIN_CELL:
            print(f"  {name:<20}{n:>12,}   below n={MIN_CELL}")
            continue
        pct = 100 * k / n
        lo_ci, hi_ci = wilson(k, n)
        print(f"  {name:<20}{n:>12,}{pct:>11.1f}%   [{100 * lo_ci:4.1f},{100 * hi_ci:5.1f}]")
        ends.append((name, pct, lo_ci, hi_ci))
    if len(ends) >= 2:
        (n0, p0, l0, h0), (n1, p1, l1, h1) = ends[0], ends[-1]
        if l1 > h0:
            print(f"  -> most-copied above never-copied, intervals clear: "
                  f"{p1:.1f}% vs {p0:.1f}%\n")
        elif h1 < l0:
            print(f"  -> most-copied BELOW never-copied, intervals clear: "
                  f"{p1:.1f}% vs {p0:.1f}%\n")
        else:
            print(f"  -> ends overlap: {p1:.1f}% vs {p0:.1f}%\n")

print("=== the same, for bundling anything at all rather than code ===")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE anyfile AS
    SELECT DISTINCT repo_full_name, artifact_path
    FROM {source('artifact_siblings')} WHERE entry_type = 'file'
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim2 AS
    SELECT c.n_owner, (f.repo_full_name IS NOT NULL) AS bundles
    FROM {source('artifacts')} a
    JOIN copies c USING (file_sha)
    LEFT JOIN anyfile f
      ON a.repo_full_name = f.repo_full_name AND a.path = f.artifact_path
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")
print(f"  {'distinct owners':<20}{'skills':>12}{'bundles any':>13}   95% CI")
for lo, hi, name in BUCKETS:
    n, k = con.execute(
        f"SELECT count(*), count(*) FILTER (WHERE bundles) FROM prim2 "
        f"WHERE n_owner BETWEEN {lo} AND {hi}").fetchone()
    if n < MIN_CELL:
        continue
    lo_ci, hi_ci = wilson(k, n)
    print(f"  {name:<20}{n:>12,}{100 * k / n:>12.1f}%   [{100 * lo_ci:4.1f},{100 * hi_ci:5.1f}]")
