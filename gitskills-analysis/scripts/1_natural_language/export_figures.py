"""Emit every number the article uses, as JSON, so nothing is transcribed.

Four figures in an earlier draft went stale because they were copied by
hand out of terminal output and then the analysis moved. This computes the
article's numbers in one pass and writes results/figures.json; the charts
and tables are built from that file, never from a person reading a table.

    uv run scripts/1_natural_language/export_figures.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, NAMES, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

MIN_CELL = 30
OUT = Path(__file__).resolve().parents[2] / "results" / "figures.json"

TRAILER = re.compile(r"co-authored-by:\s*([^<\n]+)", re.I)
GENERATED = re.compile(r"generated with\s*\[?([^\]\n(]+)", re.I)
AGENT = re.compile(
    r"claude|cursor|copilot|codex|devin|aider|windsurf|gemini|gpt|openai|cline",
    re.I)

# Simplified vs traditional Chinese, by characters that differ between the
# scripts. A crude but serviceable split; skills using neither set, or both,
# are reported separately rather than forced into one.
TRAD = re.compile("[體謝灣團機說與實數應點統監轉發後畫當時開關們個學經濟麼]")
SIMP = re.compile("[体谢湾团机说与实数应点统监转发后画当时开关们个学经济么]")

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE base AS
    WITH agg AS (
        SELECT repo_full_name FROM {source('artifacts')}
        GROUP BY 1 ORDER BY count(*) DESC LIMIT 10
    ),
    copies AS (
        SELECT file_sha, count(*) AS n_all,
               count(DISTINCT split_part(repo_full_name, '/', 1)) AS n_owner,
               count(*) FILTER (
                   WHERE repo_full_name NOT IN (SELECT repo_full_name FROM agg)
               ) AS n_noagg
        FROM {source('artifacts')} GROUP BY file_sha
    )
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           lower(a.content) AS raw,
           a.frontmatter_valid,
           a.repo_full_name,
           a.first_commit_at IS NOT NULL AS dated,
           CAST(a.first_commit_at AS TIMESTAMP) AS created,
           CAST(a.last_commit_at AS TIMESTAMP) AS last_touch,
           coalesce(a.commit_count, 1) AS commit_count,
           coalesce(a.first_commit_message, '') AS msg,
           coalesce(a.first_commit_author_type, '') AS author_type,
           c.n_all, c.n_owner, c.n_noagg,
           CAST((SELECT max(discovered_at) FROM {source('artifacts')}) AS TIMESTAMP) AS crawl
    FROM {source('artifacts')} a JOIN copies c USING (file_sha)
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")

ident = identifier()
# Streamed in batches rather than fetched at once: the prose column alone is
# about 6 GB at full scale, and it is only needed long enough to classify a
# document. What survives per record is small and fixed size, and agent names
# accumulate in one counter instead of a set on every row.
BATCH = 50_000
tool_names = Counter()
cur = con.execute(f"""SELECT prose, dated, created, last_touch, commit_count,
                             msg, author_type, n_all, n_owner, n_noagg, crawl,
                             frontmatter_valid, repo_full_name FROM base""")

recs = []
while True:
    rows = cur.fetchmany(BATCH)
    if not rows:
        break
    for (prose, dated, created, last, cc, msg, atype, n_all, n_owner, n_noagg,
         crawl, fmv, repo) in rows:
        code = classify(ident, prose)
        if code is None:
            continue
        found = {m.strip() for pat in (TRAILER, GENERATED) for m in pat.findall(msg)
                 if m.strip() and AGENT.search(m)}
        tool_names.update(found)
        recs.append({
            "lang": sys.intern(code), "dated": bool(dated), "created": created,
            "age": (crawl - created).days if created else None,
            "lag": (last - created).days if created and last else None,
            "cc": cc, "agents": bool(found), "copies": n_all, "owners": n_owner,
            "copies_noagg": max(1, n_noagg), "bot": atype == "Bot",
            "zh_trad": bool(TRAD.search(prose)), "zh_simp": bool(SIMP.search(prose)),
            "fm_valid": fmv == 1, "repo": sys.intern(repo or ""),
        })
    del rows


def share(sel, pred):
    k = sum(1 for r in sel if pred(r))
    lo, hi = wilson(k, len(sel))
    return {"n": len(sel), "k": k, "pct": round(100 * k / len(sel), 1),
            "lo": round(100 * lo, 1), "hi": round(100 * hi, 1)}


fig = {"corpus": {"classified": len(recs),
                  "dated": sum(r["dated"] for r in recs)}}

# --- distribution -----------------------------------------------------
counts = Counter(r["lang"] for r in recs)
total = len(recs)
# Sort by count, then by code, so languages with equal counts do not swap
# places between runs. Counter.most_common breaks ties by insertion order,
# which follows DuckDB row order, which is not guaranteed without ORDER BY.
ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
fig["distribution"] = [
    {"code": c, "name": NAMES.get(c, c), "n": n,
     "pct": round(100 * n / total, 1)}
    for c, n in ordered]
fig["non_english_overall"] = share(recs, lambda r: is_non_english(r["lang"]))

zh = [r for r in recs if r["lang"] == "zh"]
fig["chinese_script"] = {
    "simplified": sum(1 for r in zh if r["zh_simp"] and not r["zh_trad"]),
    "traditional": sum(1 for r in zh if r["zh_trad"] and not r["zh_simp"]),
    "mixed_or_neither": sum(1 for r in zh if r["zh_trad"] == r["zh_simp"]),
    "total": len(zh)}

# --- trend ------------------------------------------------------------
dated = [r for r in recs if r["dated"]]
by_m, by_q = defaultdict(list), defaultdict(list)
for r in dated:
    by_m[f"{r['created'].year}-{r['created'].month:02d}"].append(r)
    by_q[f"{r['created'].year}-Q{(r['created'].month - 1) // 3 + 1}"].append(r)
last_m, last_q = max(by_m), max(by_q)

fig["trend_monthly"] = [
    dict(period=m, partial=(m == last_m),
         **share(v, lambda r: is_non_english(r["lang"])))
    for m, v in sorted(by_m.items()) if len(v) >= MIN_CELL]
fig["trend_quarterly"] = [
    dict(period=q, partial=(q == last_q),
         **share(v, lambda r: is_non_english(r["lang"])))
    for q, v in sorted(by_q.items()) if len(v) >= MIN_CELL]

EURO = {"de", "fr", "es", "pt", "it", "ru", "nl"}
# Per-language cells get small fast: a language at 2% of a 900-skill quarter
# is 18 skills. Carry n and the interval so the chart can show how little
# some of these points are worth.
fig["trend_by_language"] = {
    name: [dict(period=q, partial=(q == last_q), **share(v, pred))
           for q, v in sorted(by_q.items()) if len(v) >= MIN_CELL]
    for name, pred in (("Chinese", lambda r: r["lang"] == "zh"),
                       ("Japanese", lambda r: r["lang"] == "ja"),
                       ("Korean", lambda r: r["lang"] == "ko"),
                       ("European", lambda r: r["lang"] in EURO))}

# --- robustness -------------------------------------------------------
def _one_vote_per_repo(rows):
    seen, out = set(), []
    for r in rows:
        if r["repo"] in seen:
            continue
        seen.add(r["repo"])
        out.append(r)
    return out


fig["robustness"] = {
    "never_copied": [dict(period=q, **share([r for r in v if r["copies"] == 1],
                                            lambda r: is_non_english(r["lang"])))
                     for q, v in sorted(by_q.items())
                     if len([r for r in v if r["copies"] == 1]) >= MIN_CELL],
    "repo_once": [dict(period=q, **share(_one_vote_per_repo(v),
                                         lambda r: is_non_english(r["lang"])))
                  for q, v in sorted(by_q.items())
                  if len(_one_vote_per_repo(v)) >= MIN_CELL],
}

# --- copying ----------------------------------------------------------
BUCKETS = [(1, 1, "1"), (2, 2, "2"), (3, 5, "3-5"), (6, 10**9, "6+")]
for key, field in (("copies_all", "copies"), ("copies_owner", "owners"),
                   ("copies_noagg", "copies_noagg")):
    fig[key] = [dict(bucket=lab,
                     **share([r for r in recs if lo <= r[field] <= hi],
                             lambda r: is_non_english(r["lang"])))
                for lo, hi, lab in BUCKETS
                if len([r for r in recs if lo <= r[field] <= hi]) >= MIN_CELL]

# --- maintenance ------------------------------------------------------
fig["maintenance"] = [
    {"window": w,
     "english": share([r for r in dated if r["lang"] == "en" and r["age"] >= w],
                      lambda r: r["cc"] > 1 and r["lag"] <= w),
     "non_english": share([r for r in dated if is_non_english(r["lang"])
                           and r["age"] >= w],
                          lambda r: r["cc"] > 1 and r["lag"] <= w)}
    for w in (7, 30, 90)]

# --- clock ------------------------------------------------------------
CLOCK = [("English", {"en"}), ("Chinese", {"zh"}), ("Japanese", {"ja"}),
         ("Korean", {"ko"}), ("Spanish/Portuguese", {"es", "pt"})]
fig["clock"] = []
for label, codes in CLOCK:
    sel = [r for r in dated if r["lang"] in codes]
    if len(sel) < MIN_CELL:
        continue
    hours = Counter(r["created"].hour for r in sel)
    fig["clock"].append({
        "language": label, "n": len(sel),
        "hours": [hours.get(h, 0) for h in range(24)],
        "night_pct": round(100 * sum(hours.get(h, 0) for h in range(16, 24))
                           / len(sel), 1)})

# --- authorship -------------------------------------------------------
msg = dated  # every dated skill has a first-commit message
# Trailers name specific model versions ("Claude Opus 4.6"), so collapse them
# to the tool. Summing, not assigning: many distinct trailer strings map onto
# the same tool and a dict comprehension would keep only the last.
_grouped_tools = Counter()
for _name, _n in tool_names.items():
    _grouped_tools[
        "Claude" if re.search("claude", _name, re.I) else _name.split()[0]] += _n

fig["authorship"] = {
    "overall": share(msg, lambda r: r["agents"]),
    "platform_bot": share(msg, lambda r: r["bot"]),
    "by_language": {
        lab: share([r for r in msg if pred(r)], lambda r: r["agents"])
        for lab, pred in (("English", lambda r: r["lang"] == "en"),
                          ("Chinese", lambda r: r["lang"] == "zh"),
                          ("Japanese", lambda r: r["lang"] == "ja"),
                          ("European", lambda r: r["lang"] in EURO))
        if len([r for r in msg if pred(r)]) >= MIN_CELL},
    "tools": _grouped_tools.most_common(6),
}

# --- front-matter validity by language --------------------------------
# Cited in the article as the explanation we tested and discarded for why
# published English shares disagree, so it belongs in the export too.
fig["validity"] = {
    "english": share([r for r in recs if r["lang"] == "en"],
                     lambda r: r["fm_valid"]),
    "non_english": share([r for r in recs if is_non_english(r["lang"])],
                         lambda r: r["fm_valid"]),
    "english_share_unfiltered": share(
        [r for r in recs if r["lang"] != "uncertain"], lambda r: r["lang"] == "en"),
    "english_share_valid_only": share(
        [r for r in recs if r["lang"] != "uncertain" and r["fm_valid"]],
        lambda r: r["lang"] == "en"),
}

# --- corpus concentration ---------------------------------------------
repo_counts = con.execute(f"""
    SELECT repo_full_name, count(*) AS n FROM {source('artifacts')} GROUP BY 1 ORDER BY n DESC
""").fetchall()
tot_rows = sum(n for _, n in repo_counts)
hhi = sum((n / tot_rows) ** 2 for _, n in repo_counts)
agg = {name for name, _ in repo_counts[:10]}
fig["concentration"] = {
    "repos": len(repo_counts),
    "top10_pct": round(100 * sum(n for _, n in repo_counts[:10]) / tot_rows, 1),
    "effective_repos": round(1 / hhi, 1),
    "aggregator": share([r for r in recs if r["repo"] in agg],
                        lambda r: is_non_english(r["lang"])),
    "ordinary": share([r for r in recs if r["repo"] not in agg],
                      lambda r: is_non_english(r["lang"])),
}

# --- programming languages: mention vs authoring ----------------------
# Teased at the end of article 01, so it is reproducible from here rather
# than from a separate script's terminal output.
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE sib AS
    SELECT repo_full_name, artifact_path, lower(entry_name) AS nm
    FROM {source('artifact_siblings')} WHERE entry_type = 'file'
""")
total_c = con.execute(
    f"SELECT count(*) FROM {source('artifacts')} WHERE dedup_primary = 1 AND content IS NOT NULL"
).fetchone()[0]
fig["prog_languages"] = {}
for label, pattern, globs in (
        ("Shell/Bash", r"\bbash\b|\bzsh\b|shell script", ("%.sh", "%.bash", "%.zsh")),
        ("Python", r"\bpython\b", ("%.py",))):
    mention = con.execute(f"""
        SELECT count(*) FROM {source('artifacts')}
        WHERE dedup_primary = 1 AND content IS NOT NULL
          AND regexp_matches(lower(content), '{pattern}')
    """).fetchone()[0]
    where = " OR ".join(f"s.nm LIKE '{g}'" for g in globs)
    authored = con.execute(f"""
        SELECT count(DISTINCT a.repo_full_name || '/' || a.path)
        FROM {source('artifacts')} a JOIN sib s
          ON a.repo_full_name = s.repo_full_name AND a.path = s.artifact_path
        WHERE a.dedup_primary = 1 AND ({where})
    """).fetchone()[0]
    fig["prog_languages"][label] = {
        "mention_pct": round(100 * mention / total_c, 1),
        "authoring_pct": round(100 * authored / total_c, 1),
    }

# --- language-ID cross-check -------------------------------------------
# Recomputing this here would double the export's runtime for a number that
# barely moves, so crosscheck_langid.py writes it and we carry it forward.
_xc = OUT.parent / "crosscheck.json"
if _xc.exists():
    fig["crosscheck"] = json.loads(_xc.read_text())

OUT.parent.mkdir(exist_ok=True)
# Guard: this file holds the numbers article 01 published. Running the
# export against the sample writes 13,000-row figures over 3.8M-row ones and
# says nothing, which has happened. Refuse to shrink the export unless asked.
if OUT.exists() and "--force" not in sys.argv:
    try:
        prev = json.loads(OUT.read_text())["corpus"]["classified"]
    except (KeyError, ValueError):
        prev = 0
    if fig["corpus"]["classified"] < prev:
        raise SystemExit(
            f"refusing to overwrite {OUT.name}: it holds {prev:,} classified "
            f"skills and this run has {fig['corpus']['classified']:,}. "
            f"Point GITSKILLS_DB or GITSKILLS_PARQUET at the full corpus, or "
            f"pass --force if shrinking it is what you meant.")

OUT.write_text(json.dumps(fig, indent=2, default=str))
print(f"wrote {OUT}")
print(f"  {fig['corpus']['classified']} classified, "
      f"{fig['corpus']['dated']} dated")
print(f"  non-English overall: {fig['non_english_overall']['pct']}%")
print(f"  agent-authored: {fig['authorship']['overall']['pct']}%")
