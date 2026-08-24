"""Are non-English skills maintained differently? Compared at equal age.

The naive comparison -- "what share of each language's skills were ever
revised?" -- is confounded by age. Non-English share is rising, so
non-English skills are younger on average, and a younger skill has had
less calendar time in which to be revised. Any raw comparison partly
measures birth date.

So this uses fixed-age windows, the standard cohort correction: among
skills old enough to have had the opportunity (age >= W at crawl time),
what fraction were revised within W days of creation? Every group is then
compared over the same stretch of life.

Two limits inherited from the data, both of which bias toward
under-counting maintenance:

- Left truncation. A crawl sees only files that still exist. Skills
  created and deleted before July 2026 are invisible, so these are
  survivors, and survivor maintenance rates run high.
- Censoring. "Never revised" means never revised *as of the crawl*, not
  abandoned. Dormancy is not absorbing: Avelino et al. (ESEM 2019) found
  41% of abandoned OSS projects were later revived. For a format ~18
  months old, treating a quiet skill as dead is the likeliest error.
"""

from collections import defaultdict

import duckdb

from common import (MAX_CHARS, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

WINDOWS = (7, 30, 90)
MIN_CELL = 30

GROUPS = [("English", {"en"}), ("Chinese", {"zh"}), ("Japanese", {"ja"}),
          ("Korean", {"ko"}),
          ("European", {"de", "fr", "es", "pt", "it", "ru", "nl"})]

con = connect(duckdb.connect)
con.execute(f"ATTACH '{db_path()}' AS db (TYPE sqlite)")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE d AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           CAST(first_commit_at AS TIMESTAMP) AS created,
           CAST(last_commit_at AS TIMESTAMP) AS last_touch,
           coalesce(commit_count, 1) AS commit_count,
           CAST((SELECT max(discovered_at) FROM db.artifacts) AS TIMESTAMP) AS crawl
    FROM db.artifacts
    WHERE dedup_primary = 1 AND content IS NOT NULL
      AND first_commit_at IS NOT NULL AND last_commit_at IS NOT NULL
""")

ident = identifier()
recs = []
for prose, created, last, cc, crawl in con.execute(
        "SELECT prose, created, last_touch, commit_count, crawl FROM d").fetchall():
    code = classify(ident, prose)
    if code is None or code == "uncertain":
        continue
    recs.append({"lang": code, "age": (crawl - created).days,
                 "lag": (last - created).days, "cc": cc})

print(f"{len(recs)} dated + classified skills\n")

print("=== the confound: median age at crawl, in days ===")
for label, codes in GROUPS:
    sel = [r for r in recs if r["lang"] in codes]
    if len(sel) >= MIN_CELL:
        ages = sorted(r["age"] for r in sel)
        print(f"  {label:<11}{len(sel):>6}{ages[len(ages) // 2]:>8}")
print("  -> non-English skills are younger, so an uncorrected maintenance")
print("     comparison would understate them\n")


def revised(sel, w):
    return sum(1 for r in sel if r["cc"] > 1 and r["lag"] <= w)


for w in WINDOWS:
    print(f"=== revised within {w}d, among skills at least {w}d old ===")
    print(f"  {'language':<11}{'eligible':>9}   revised")
    for label, codes in GROUPS:
        sel = [r for r in recs if r["lang"] in codes and r["age"] >= w]
        if len(sel) < MIN_CELL:
            continue
        k = revised(sel, w)
        lo, hi = wilson(k, len(sel))
        print(f"  {label:<11}{len(sel):>9}   {100 * k / len(sel):>5.1f}%  "
              f"[{100*lo:>4.1f}, {100*hi:>5.1f}]")
    print()

print("=== English vs non-English, pooled, at equal age ===")
for w in WINDOWS:
    print(f"  window {w}d")
    for label, pred in (("English", lambda r: r["lang"] == "en"),
                        ("non-English", lambda r: is_non_english(r["lang"]))):
        sel = [r for r in recs if pred(r) and r["age"] >= w]
        if len(sel) < MIN_CELL:
            continue
        k = revised(sel, w)
        lo, hi = wilson(k, len(sel))
        print(f"    {label:<12}{len(sel):>6}   {100 * k / len(sel):>5.1f}%  "
              f"[{100*lo:>4.1f}, {100*hi:>5.1f}]")

print("\n=== never revised as of the crawl (censored, not abandoned) ===")
print(f"  {'language':<11}{'n':>6}   single-commit share")
for label, codes in GROUPS:
    sel = [r for r in recs if r["lang"] in codes]
    if len(sel) < MIN_CELL:
        continue
    k = sum(1 for r in sel if r["cc"] == 1)
    lo, hi = wilson(k, len(sel))
    print(f"  {label:<11}{len(sel):>6}   {100 * k / len(sel):>5.1f}%  "
          f"[{100*lo:>4.1f}, {100*hi:>5.1f}]")

print("\n=== sensitivity: does the gap hold at every window? ===")
gaps = defaultdict(dict)
for w in WINDOWS:
    for label, pred in (("en", lambda r: r["lang"] == "en"),
                        ("non", lambda r: is_non_english(r["lang"]))):
        sel = [r for r in recs if pred(r) and r["age"] >= w]
        gaps[w][label] = revised(sel, w) / len(sel) if sel else 0
for w in WINDOWS:
    d = 100 * (gaps[w]["non"] - gaps[w]["en"])
    print(f"  {w:>3}d window: non-English leads by {d:+.1f} points")
