"""What is actually inside a skill folder?

The spec names three optional companions to SKILL.md: scripts/, references/
and assets/. This asks what people actually put there, and the answer
reframes the whole article: skills are prose, and what they bundle is mostly
more prose.

Counting rules that matter here:

**Count skills and owners, not files.** File histograms are dominated by
single actors vendoring a codebase into one skill folder. Both views are
printed and the skill-level one is the finding.

**Bundle figures are a floor.** The crawler truncated the folder listing for
a share of skills, printed below, so every "bundles X" number understates by
an amount nobody can estimate from inside the data.

**And a ceiling, from the other direction.** artifact_siblings lists whatever
sits alongside SKILL.md in its directory. For .claude/skills/foo/SKILL.md
that is the skill's own companions; for a SKILL.md at the repository root it
is the entire project, so its "bundled code" is somebody's application. Those
skills are 1.4% of the corpus and 70.5% of them "ship code" against 12.6%
overall. The depth table below reports the headline with them excluded, and
that conservative figure is the one to publish.

Composition was fetched for very nearly every representative, so unlike the
temporal cuts this is not working from a minority subsample.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import ASSETS, DATA, DOCS, EXT2LANG, ext_case_sql

con = connect(duckdb.connect)

KIND = {**{e: "code" for e in EXT2LANG},
        **{e: "docs" for e in DOCS},
        **{e: "data/config" for e in DATA},
        **{e: "asset" for e in ASSETS}}

con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim AS
    SELECT repo_full_name, path,
           split_part(repo_full_name, '/', 1) AS owner,
           composition_truncated
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE files AS
    SELECT repo_full_name, artifact_path, entry_name,
           {ext_case_sql('entry_name', KIND, 'other')} AS kind,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
    FROM {source('artifact_siblings')}
    WHERE entry_type = 'file'
""")

N = con.execute("SELECT count(*) FROM prim").fetchone()[0]
owners_all = con.execute("SELECT count(DISTINCT owner) FROM prim").fetchone()[0]
print(f"=== {scale()} ===")
print(f"  skills (representatives with content): {N:,}")
print(f"  distinct owners                      : {owners_all:,}\n")

trunc = con.execute(
    "SELECT count(*) FROM prim WHERE composition_truncated = 1").fetchone()[0]
print(f"  folder listing truncated by the crawler: {trunc:,} ({100 * trunc / N:.1f}%)")
print("  -> every figure below is a floor\n")

print("=== every bundled file, by what it is ===")
rows = con.execute("""
    SELECT f.kind, count(*) n
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1 ORDER BY n DESC
""").fetchall()
tot = sum(r[1] for r in rows)
for kind, n in rows:
    print(f"  {kind:<14}{n:>11,}{100 * n / tot:>7.1f}%")
print(f"  {'total':<14}{tot:>11,}")

print("\n=== share of ALL skills bundling at least one file of each kind ===")
rows = con.execute("""
    SELECT f.kind,
           count(DISTINCT p.repo_full_name || ' ' || p.path) skills,
           count(DISTINCT p.owner) owners
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1 ORDER BY skills DESC
""").fetchall()
print(f"  {'kind':<14}{'skills':>11}{'% skills':>10}{'owners':>10}{'% owners':>10}   95% CI (skills)")
for kind, skills, owners in rows:
    lo, hi = wilson(skills, N)
    print(f"  {kind:<14}{skills:>11,}{100 * skills / N:>9.1f}%{owners:>10,}"
          f"{100 * owners / owners_all:>9.1f}%   [{100 * lo:4.1f},{100 * hi:5.1f}]")

any_b, any_o = con.execute("""
    SELECT count(DISTINCT p.repo_full_name || ' ' || p.path),
           count(DISTINCT p.owner)
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
""").fetchone()
print(f"  {'ANY file':<14}{any_b:>11,}{100 * any_b / N:>9.1f}%{any_o:>10,}"
      f"{100 * any_o / owners_all:>9.1f}%")
print(f"\n  bundles nothing at all: {N - any_b:,} ({100 * (N - any_b) / N:.1f}%)")

print("\n=== how big is a bundle, among skills that bundle anything ===")
q = con.execute("""
    WITH c AS (
        SELECT p.repo_full_name, p.path, count(*) n
        FROM prim p JOIN files f
          ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
        GROUP BY 1, 2
    )
    SELECT count(*), median(n), avg(n), quantile_cont(n, 0.9), max(n) FROM c
""").fetchone()
print(f"  n={q[0]:,}  median={q[1]:.0f}  mean={q[2]:.1f}  p90={q[3]:.0f}  max={q[4]:,}")

print("\n=== robustness: how deep does SKILL.md sit? ===")
print("  depth 0 is the repository root, where a skill's siblings are the")
print("  whole project rather than its own files")
con.execute("""
    CREATE OR REPLACE TEMP TABLE depth AS
    SELECT p.repo_full_name, p.path,
           length(p.path) - length(replace(p.path, '/', '')) AS d,
           (f.repo_full_name IS NOT NULL) AS ships
    FROM prim p
    LEFT JOIN (SELECT DISTINCT repo_full_name, artifact_path FROM files
               WHERE lang <> '') f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
""")
print(f"  {'depth':<10}{'skills':>12}{'% of all':>10}{'ships code':>12}   95% CI")
for d, n, k in con.execute("""
        SELECT least(d, 5), count(*), count(*) FILTER (WHERE ships)
        FROM depth GROUP BY 1 ORDER BY 1""").fetchall():
    lo, hi = wilson(k, n)
    label = "0 (root)" if d == 0 else ("5+" if d == 5 else str(d))
    print(f"  {label:<10}{n:>12,}{100 * n / N:>9.1f}%{100 * k / n:>11.1f}%"
          f"   [{100 * lo:4.1f},{100 * hi:5.1f}]")

print("\n  the headline under three exclusions:")
for label, where in [("all skills", "1=1"),
                     ("excluding depth 0 (root)", "d > 0"),
                     ("excluding depth 0 and 1", "d > 1")]:
    n, k = con.execute(
        f"SELECT count(*), count(*) FILTER (WHERE ships) FROM depth WHERE {where}"
    ).fetchone()
    lo, hi = wilson(k, n)
    star = "   <- publish this one" if where == "d > 0" else ""
    print(f"    {label:<28}n={n:>10,}  {100 * k / n:>5.1f}%  "
          f"[{100 * lo:4.1f},{100 * hi:5.1f}]{star}")

print("\n=== among code-shipping skills, which languages ===")
con.execute("""
    CREATE OR REPLACE TEMP TABLE shipped AS
    SELECT DISTINCT p.repo_full_name, p.path, p.owner, f.lang
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    WHERE f.lang <> ''
""")
coders = con.execute(
    "SELECT count(DISTINCT repo_full_name || ' ' || path) FROM shipped").fetchone()[0]
print(f"  skills shipping any code: {coders:,} ({100 * coders / N:.1f}% of all skills)")
print(f"  {'language':<14}{'skills':>10}{'% of coders':>13}{'% of all':>10}{'owners':>9}")
for lang, skills, owners in con.execute("""
        SELECT lang, count(DISTINCT repo_full_name || ' ' || path) s,
               count(DISTINCT owner) o
        FROM shipped GROUP BY 1 ORDER BY s DESC LIMIT 18""").fetchall():
    print(f"  {lang:<14}{skills:>10,}{100 * skills / coders:>12.1f}%"
          f"{100 * skills / N:>9.1f}%{owners:>9,}")

only_py, = con.execute("""
    WITH per AS (SELECT repo_full_name, path, count(*) n,
                        count(*) FILTER (WHERE lang = 'Python') py
                 FROM shipped GROUP BY 1, 2)
    SELECT count(*) FROM per WHERE n = 1 AND py = 1
""").fetchone()
print(f"\n  ship ONLY Python: {only_py:,} "
      f"({100 * only_py / coders:.1f}% of code-shipping skills)")
