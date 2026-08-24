"""Emit every number the article uses, as JSON, so nothing is transcribed.

Four figures in an earlier draft went stale because they were copied by
hand out of terminal output and then the analysis moved. This computes the
article's numbers in one pass and writes results/figures.json; the charts
and tables are built from that file, never from a person reading a table.

    uv run scripts/1_natural_language/export_figures.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from common import (MAX_CHARS, NAMES, PROSE_SQL, classify, connect, db_path,
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
con.execute(f"ATTACH '{db_path()}' AS db (TYPE sqlite)")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE base AS
    WITH copies AS (
        SELECT file_sha, count(*) AS n_all,
               count(DISTINCT split_part(repo_full_name, '/', 1)) AS n_owner
        FROM db.artifacts GROUP BY file_sha
    )
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           a.first_commit_at IS NOT NULL AS dated,
           CAST(a.first_commit_at AS TIMESTAMP) AS created,
           CAST(a.last_commit_at AS TIMESTAMP) AS last_touch,
           coalesce(a.commit_count, 1) AS commit_count,
           coalesce(a.first_commit_message, '') AS msg,
           c.n_all, c.n_owner,
           CAST((SELECT max(discovered_at) FROM db.artifacts) AS TIMESTAMP) AS crawl
    FROM db.artifacts a JOIN copies c USING (file_sha)
    WHERE a.dedup_primary = 1 AND a.content IS NOT NULL
""")

ident = identifier()
rows = con.execute("""SELECT prose, dated, created, last_touch, commit_count,
                             msg, n_all, n_owner, crawl FROM base""").fetchall()

recs = []
for prose, dated, created, last, cc, msg, n_all, n_owner, crawl in rows:
    code = classify(ident, prose)
    if code is None:
        continue
    agents = {m.strip() for p in (TRAILER, GENERATED) for m in p.findall(msg)
              if m.strip() and AGENT.search(m)}
    recs.append({
        "lang": code, "dated": bool(dated), "created": created,
        "age": (crawl - created).days if created else None,
        "lag": (last - created).days if created and last else None,
        "cc": cc, "agents": agents, "copies": n_all, "owners": n_owner,
        "zh_trad": bool(TRAD.search(prose)), "zh_simp": bool(SIMP.search(prose)),
    })


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
fig["distribution"] = [
    {"code": c, "name": NAMES.get(c, c), "n": n,
     "pct": round(100 * n / total, 1)}
    for c, n in counts.most_common(12)]
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
fig["trend_by_language"] = {
    name: [{"period": q, "pct": round(100 * sum(1 for r in v if pred(r)) / len(v), 1)}
           for q, v in sorted(by_q.items()) if len(v) >= MIN_CELL]
    for name, pred in (("Chinese", lambda r: r["lang"] == "zh"),
                       ("Japanese", lambda r: r["lang"] == "ja"),
                       ("Korean", lambda r: r["lang"] == "ko"),
                       ("European", lambda r: r["lang"] in EURO))}

# --- robustness -------------------------------------------------------
fig["robustness"] = {
    "never_copied": [dict(period=q, **share([r for r in v if r["copies"] == 1],
                                            lambda r: is_non_english(r["lang"])))
                     for q, v in sorted(by_q.items())
                     if len([r for r in v if r["copies"] == 1]) >= MIN_CELL],
}

# --- copying ----------------------------------------------------------
BUCKETS = [(1, 1, "1"), (2, 2, "2"), (3, 5, "3-5"), (6, 10**9, "6+")]
for key, field in (("copies_all", "copies"), ("copies_owner", "owners")):
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
msg = [r for r in dated if r["agents"] or True]
fig["authorship"] = {
    "overall": share(msg, lambda r: bool(r["agents"])),
    "by_language": {
        lab: share([r for r in msg if pred(r)], lambda r: bool(r["agents"]))
        for lab, pred in (("English", lambda r: r["lang"] == "en"),
                          ("Chinese", lambda r: r["lang"] == "zh"),
                          ("Japanese", lambda r: r["lang"] == "ja"),
                          ("European", lambda r: r["lang"] in EURO))
        if len([r for r in msg if pred(r)]) >= MIN_CELL},
    "tools": Counter(
        "Claude" if re.search("claude", a, re.I) else a.split()[0]
        for r in msg for a in r["agents"]).most_common(6),
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(fig, indent=2, default=str))
print(f"wrote {OUT}")
print(f"  {fig['corpus']['classified']} classified, "
      f"{fig['corpus']['dated']} dated")
print(f"  non-English overall: {fig['non_english_overall']['pct']}%")
print(f"  agent-authored: {fig['authorship']['overall']['pct']}%")
