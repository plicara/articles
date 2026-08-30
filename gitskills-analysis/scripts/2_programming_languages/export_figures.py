#!/usr/bin/env python3
"""Every number article 02 publishes, in one export.

The rule this file exists to enforce: no figure in the article exists
outside this export, and no number is typed into the prose by hand. Four
figures went stale in an article 01 draft precisely because they were typed,
which is why article 01 has export_figures.py and why article 02 has this.

    uv run scripts/2_programming_languages/export_figures.py

Writes results/figures_02.json. content.py reads it, and build_article.py
reads content.py; nothing else may.

The queries here duplicate the analysis scripts on purpose. Those scripts
print for a human reading a terminal and are free to change their layout;
this one produces a stable machine-readable contract. What must NOT diverge
is the definitions, which is why both sides import the extension map and the
mention patterns from scripts/languages.py rather than restating them.

Guards this export applies, all documented in the plan:

- **Root-level skills are excluded from every "ships code" figure.** A
  SKILL.md at the repository root has the whole project as its siblings, so
  its bundled code is somebody's application. They are 1.4% of the corpus
  and 70.5% of them "ship code". Both figures are exported so the article
  can state the conservative one and name the other.
- **Counts are of skills or owners, never files**, except where a file count
  is the explicit subject (the composition bar).
"""

import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import connect, scale, source, wilson
from languages import (ASSETS, DATA, DOCS, EXT2LANG, MENTIONS, ext_case_sql)

OUT = Path(__file__).resolve().parents[2] / "results" / "figures_02.json"

ALIAS = {"Shell": "Shell/Bash", "HTML": "HTML/CSS", "CSS": "HTML/CSS",
         "SCSS": "HTML/CSS", "Less": "HTML/CSS", "C++": "C/C++", "C": "C/C++",
         "Jupyter Notebook": "Python"}
KIND = {**{e: "code" for e in EXT2LANG}, **{e: "docs" for e in DOCS},
        **{e: "data/config" for e in DATA}, **{e: "asset" for e in ASSETS}}
NONROOT = "length(a.path) - length(replace(a.path, '/', '')) > 0"

con = connect(duckdb.connect)
fig = {"provenance": {"corpus": scale()}}


def ci(k, n):
    lo, hi = wilson(k, n)
    return {"n": n, "k": k, "pct": round(100 * k / n, 2) if n else 0.0,
            "lo": round(100 * lo, 2), "hi": round(100 * hi, 2)}


con.execute(f"""
    CREATE OR REPLACE TEMP TABLE prim AS
    SELECT a.repo_full_name, a.path, a.body_chars,
           split_part(a.repo_full_name, '/', 1) AS owner,
           a.composition_truncated,
           length(a.path) - length(replace(a.path, '/', '')) AS depth
    FROM {source('artifacts')} a
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE files AS
    SELECT repo_full_name, artifact_path, entry_name,
           {ext_case_sql('entry_name', KIND, 'other')} AS kind,
           {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
    FROM {source('artifact_siblings')} WHERE entry_type = 'file'
""")
con.execute("""
    CREATE OR REPLACE TEMP TABLE sk AS
    SELECT p.repo_full_name, p.path, p.owner, p.depth, p.body_chars,
           count(f.entry_name) > 0                       AS bundles,
           count(*) FILTER (WHERE f.lang <> '') > 0      AS ships
    FROM prim p LEFT JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1, 2, 3, 4, 5
""")

N = con.execute("SELECT count(*) FROM prim").fetchone()[0]
NR = con.execute("SELECT count(*) FROM sk WHERE depth > 0").fetchone()[0]
fig["corpus"] = {
    "artifact_rows": con.execute(
        f"SELECT count(*) FROM {source('artifacts')}").fetchone()[0],
    "repos": con.execute(f"SELECT count(*) FROM {source('repos')}").fetchone()[0],
    "skills": N,
    "skills_nonroot": NR,
    "owners": con.execute("SELECT count(DISTINCT owner) FROM prim").fetchone()[0],
    "truncated": ci(con.execute(
        "SELECT count(*) FROM prim WHERE composition_truncated = 1").fetchone()[0], N),
}

# ---- FIG-1: composition ---------------------------------------------------
rows = con.execute("""
    SELECT f.kind, count(*) FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1 ORDER BY 2 DESC""").fetchall()
tot_files = sum(r[1] for r in rows)
fig["composition_files"] = {
    "total": tot_files,
    "kinds": [{"kind": k, "n": n, "pct": round(100 * n / tot_files, 1)}
              for k, n in rows]}

kinds = con.execute("""
    SELECT f.kind, count(DISTINCT p.repo_full_name || ' ' || p.path)
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1 ORDER BY 2 DESC""").fetchall()
fig["composition_skills"] = [dict(kind=k, **ci(n, N)) for k, n in kinds]

fig["bundles_any"] = ci(
    con.execute("SELECT count(*) FROM sk WHERE bundles").fetchone()[0], N)
fig["bundles_nothing"] = ci(
    con.execute("SELECT count(*) FROM sk WHERE NOT bundles").fetchone()[0], N)

# The headline, both ways. The article states the conservative one.
fig["ships_code"] = {
    "all": ci(con.execute("SELECT count(*) FROM sk WHERE ships").fetchone()[0], N),
    "nonroot": ci(con.execute(
        "SELECT count(*) FROM sk WHERE ships AND depth > 0").fetchone()[0], NR),
    "depth": [{"depth": d, **ci(k, n)} for d, n, k in con.execute("""
        SELECT least(depth, 5), count(*), count(*) FILTER (WHERE ships)
        FROM sk GROUP BY 1 ORDER BY 1""").fetchall()],
}

q = con.execute("""
    WITH c AS (SELECT p.repo_full_name, p.path, count(*) n
               FROM prim p JOIN files f
                 ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
               GROUP BY 1, 2)
    SELECT median(n), avg(n), quantile_cont(n, 0.9), max(n) FROM c""").fetchone()
fig["bundle_size"] = {"median": q[0], "mean": round(q[1], 1),
                      "p90": q[2], "max": q[3]}

# ---- languages shipped, among code-shipping skills ------------------------
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE shipped AS
    SELECT DISTINCT p.repo_full_name, p.path, f.lang
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    WHERE f.lang <> '' AND p.depth > 0
""")
coders = con.execute(
    "SELECT count(DISTINCT repo_full_name || ' ' || path) FROM shipped").fetchone()[0]
fig["shipped_languages"] = {
    "coders": coders,
    "rows": [{"lang": l, "n": n, "pct_of_coders": round(100 * n / coders, 1),
              "pct_of_all": round(100 * n / NR, 2)}
             for l, n in con.execute("""
                 SELECT lang, count(DISTINCT repo_full_name || ' ' || path) n
                 FROM shipped GROUP BY 1 ORDER BY n DESC LIMIT 14""").fetchall()],
    "only_python": con.execute("""
        WITH per AS (SELECT repo_full_name, path, count(*) n,
                            count(*) FILTER (WHERE lang = 'Python') py
                     FROM shipped GROUP BY 1, 2)
        SELECT count(*) FROM per WHERE n = 1 AND py = 1""").fetchone()[0],
}

# ---- FIG-2: the repository's own language ---------------------------------
alias_sql = ("CASE " + " ".join(f"WHEN r.language = '{k}' THEN '{v}'"
                                for k, v in ALIAS.items()) + " ELSE r.language END")
# Only languages this project can actually detect from a file extension. A repo
# labelled TeX or MDX can never "ship its own language" because nothing maps to
# it, so it would report a flat 0% that is a definition and not a finding. This
# is the same class of error as the GitHub-naming one the ALIAS map fixes.
detectable = ", ".join("'" + v.replace("'", "''") + "'"
                       for v in sorted(set(EXT2LANG.values())))
fig["repo_language"] = [
    {"lang": l, "n": n,
     "ships_own": round(100 * same / n, 1), "ships_python": round(100 * py / n, 1),
     "lo": round(100 * wilson(same, n)[0], 1), "hi": round(100 * wilson(same, n)[1], 1)}
    for l, n, same, py in con.execute(f"""
        WITH coded AS (
            SELECT {alias_sql} AS rl, a.repo_full_name, a.path,
                   list(DISTINCT s.lang) AS langs
            FROM {source('artifacts')} a
            JOIN {source('repos')} r ON r.full_name = a.repo_full_name
            JOIN (SELECT repo_full_name, artifact_path,
                         {ext_case_sql('entry_name', EXT2LANG, '')} AS lang
                  FROM {source('artifact_siblings')}
                  WHERE entry_type = 'file'
                    AND {ext_case_sql('entry_name', EXT2LANG, '')} <> '') s
              ON a.repo_full_name = s.repo_full_name AND a.path = s.artifact_path
            WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
              AND r.language IS NOT NULL AND r.language <> '' AND {NONROOT}
            GROUP BY 1, 2, 3)
        SELECT rl, count(*) n,
               count(*) FILTER (WHERE list_contains(langs, rl)) same,
               count(*) FILTER (WHERE list_contains(langs, 'Python')) py
        FROM coded
        WHERE rl IN ({detectable})
        GROUP BY 1 HAVING count(*) >= 300
        ORDER BY same::DOUBLE / count(*) DESC""").fetchall()]

# ---- FIG-3 / FIG-4: over time ---------------------------------------------
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE dated AS
    SELECT a.repo_full_name, a.path, lower(a.content) AS text,
           strftime(CAST(a.first_commit_at AS TIMESTAMP), '%Y-Q')
             || CAST(quarter(CAST(a.first_commit_at AS TIMESTAMP)) AS VARCHAR) AS q
    FROM {source('artifacts')} a
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
      AND a.first_commit_at IS NOT NULL AND {NONROOT}
""")
tot_q = dict(con.execute("SELECT q, count(*) FROM dated GROUP BY 1").fetchall())
qs = [q for q in sorted(tot_q) if tot_q[q] >= 5000]
ship_q = {}
for q, lang, k in con.execute("""
        SELECT d.q, s.lang, count(DISTINCT d.repo_full_name || ' ' || d.path)
        FROM dated d JOIN shipped s
          ON d.repo_full_name = s.repo_full_name AND d.path = s.path
        GROUP BY 1, 2""").fetchall():
    ship_q[(q, lang)] = k

fig["over_time"] = {"quarters": qs, "censored": qs[-1] if qs else None,
                    "series": {}}
for lang in ["Python", "Shell/Bash", "JavaScript", "TypeScript", "HTML/CSS"]:
    pat = MENTIONS[lang]
    out = []
    for q in qs:
        n = tot_q[q]
        m = con.execute(f"SELECT count(*) FROM dated WHERE q = '{q}' "
                        f"AND regexp_matches(text, '{pat}')").fetchone()[0]
        s = ship_q.get((q, lang), 0)
        out.append({"q": q, "n": n,
                    "mention_pct": round(100 * m / n, 2),
                    **{k: v for k, v in ci(s, n).items() if k in ("pct", "lo", "hi")},
                    "ratio": round(m / s, 1) if s else None})
    fig["over_time"]["series"][lang] = out

# ---- FIG-5: mention against shipping, all languages -----------------------
# One pass with a FILTER per pattern rather than a query per language: 22
# separate scans of 1.9M documents is minutes, this is seconds.
mention_counts = dict(zip(
    MENTIONS,
    con.execute(f"""
        SELECT {', '.join(f"count(*) FILTER (WHERE regexp_matches(t, '{p}'))"
                          for p in MENTIONS.values())}
        FROM (SELECT lower(a.content) AS t FROM {source('artifacts')} a
              WHERE a.dedup_primary = 1 AND a.content IS NOT NULL AND {NONROOT})
    """).fetchone()))
ship_counts = dict(con.execute("""
    SELECT lang, count(DISTINCT repo_full_name || ' ' || path) FROM shipped
    GROUP BY 1""").fetchall())
fig["mention_vs_ship"] = sorted(
    [{"lang": l, "mentions": mention_counts[l],
      "mention_pct": round(100 * mention_counts[l] / NR, 2),
      "ships": ship_counts.get(l, 0),
      "ship_pct": round(100 * ship_counts.get(l, 0) / NR, 3),
      "ratio": round(mention_counts[l] / ship_counts[l], 1)
                if ship_counts.get(l) else None}
     for l in MENTIONS
     if mention_counts[l] >= 1000 and ship_counts.get(l, 0) >= 100],
    key=lambda r: -(r["ratio"] or 0))

# ---- FIG-6: by the language the skill is written in ------------------------
cache = Path(__file__).resolve().parents[2] / "data" / "derived" / "skill_language.parquet"
if cache.exists():
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE byl AS
        SELECT l."group" AS grp, split_part(l.repo_full_name, '/', 1) AS owner,
               max(s.ships::INT) AS ships
        FROM read_parquet('{cache}') l
        JOIN sk s ON s.repo_full_name = l.repo_full_name AND s.path = l.path
        WHERE l."group" <> 'uncertain' AND s.depth > 0
        GROUP BY 1, 2
    """)
    fig["by_written_language"] = [
        {"group": g, **ci(k, n)} for g, n, k in con.execute("""
            SELECT grp, count(*), sum(ships) FROM byl GROUP BY 1
            ORDER BY sum(ships)::DOUBLE / count(*) DESC""").fetchall()]

# ---- FIG-7: bundling against reuse ----------------------------------------
# Owners per content first, then join. A correlated subquery per skill would
# be 1.9M scans of the artifact table.
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE owners_per AS
    SELECT file_sha, count(DISTINCT split_part(repo_full_name, '/', 1)) AS owners
    FROM {source('artifacts')} GROUP BY 1
""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE reuse AS
    SELECT s.ships, s.bundles, o.owners
    FROM sk s
    JOIN {source('artifacts')} a
      ON a.repo_full_name = s.repo_full_name AND a.path = s.path
     AND a.dedup_primary = 1
    JOIN owners_per o USING (file_sha)
    WHERE s.depth > 0
""")
fig["reuse"] = [
    {"bucket": name,
     "ships": ci(k, n), "bundles": ci(b, n)}
    for name, n, k, b in con.execute("""
        SELECT CASE WHEN owners = 1 THEN '1' WHEN owners = 2 THEN '2'
                    WHEN owners <= 5 THEN '3-5' ELSE '6+' END AS bucket,
               count(*), count(*) FILTER (WHERE ships),
               count(*) FILTER (WHERE bundles)
        FROM reuse GROUP BY 1
        ORDER BY min(owners)""").fetchall()]

# ---- FIG-8: the spec's directories ----------------------------------------
rows = con.execute("""
    SELECT CASE
             WHEN lower(f.entry_name) LIKE 'scripts/%'    THEN 'scripts/'
             WHEN lower(f.entry_name) LIKE 'references/%' THEN 'references/'
             WHEN lower(f.entry_name) LIKE 'assets/%'     THEN 'assets/'
             WHEN f.entry_name LIKE '%/%'                 THEN 'other subdirectory'
             ELSE 'loose beside SKILL.md' END AS place,
           count(*) n
    FROM prim p JOIN files f
      ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
    GROUP BY 1 ORDER BY n DESC""").fetchall()
tot_p = sum(r[1] for r in rows)
fig["spec_layout"] = {"total": tot_p,
                      "rows": [{"place": p, "n": n, "pct": round(100 * n / tot_p, 1)}
                               for p, n in rows]}

# ---- supporting numbers the prose uses ------------------------------------
body = con.execute("""
    SELECT ships, count(*), median(body_chars) FROM sk WHERE depth > 0
    GROUP BY 1 ORDER BY 1""").fetchall()
fig["body_chars"] = {("ships" if s else "prose_only"): {"n": n, "median": m}
                     for s, n, m in body}
fig["scripts_dir"] = [
    {"lang": (l or "(not code)"), "n": n} for l, n in con.execute("""
        SELECT CASE WHEN f.lang = '' THEN NULL ELSE f.lang END, count(*)
        FROM prim p JOIN files f
          ON p.repo_full_name = f.repo_full_name AND p.path = f.artifact_path
        WHERE lower(f.entry_name) LIKE 'scripts/%'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 8""").fetchall()]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(fig, indent=2, default=str, sort_keys=True))
print(f"wrote {OUT}")
print(f"  corpus     : {fig['corpus']['skills']:,} skills, "
      f"{fig['corpus']['owners']:,} owners")
print(f"  ships code : {fig['ships_code']['nonroot']['pct']}% (non-root), "
      f"{fig['ships_code']['all']['pct']}% (all)")
print(f"  figures    : {len([k for k in fig if not k.startswith('provenance')])} keys")
