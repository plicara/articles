"""Summarize freshness arms into a committed export.

Reads data/raw/freshness_*.jsonl (gitignored raw envelopes), derives the
numbers the article may cite, and writes
results/1_refused_at_random/freshness_summary.json. No judgment here beyond
naming: every count is derivable from the raw file.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent / "data" / "raw"
OUT = HERE.parent.parent / "results" / "1_refused_at_random" / "freshness_summary.json"

# Historical baseline from the study window, for the same 15 tasks:
# 29 refusals out of 45 calls (15 tasks x 3 samples), all opus-5.
HISTORICAL = {"opus_refused_calls": 29, "opus_total_calls": 45}


def blanked(rec):
    """A blanking: filter-shaped finish reason or an empty body."""
    fr = rec.get("finish_reason")
    if fr == "content_filter":
        return True
    ch = ((rec.get("raw") or {}).get("choices") or [{}])[0]
    body = ch.get("message", {}).get("content")
    return rec.get("completion_tokens") in (0, 1) and not body


def main():
    if not list(RAW.glob("freshness_*.jsonl")):
        sys.exit("no freshness raw files found; run collect.py first")
    out = {"generated": __import__("datetime").date.today().isoformat(),
           "arms": {}, "historical_baseline": HISTORICAL}
    for f in sorted(RAW.glob("freshness_*.jsonl")):
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        per_prompt = collections.defaultdict(lambda: [0, 0])
        fin = collections.Counter()
        native = collections.Counter()
        cost = 0.0
        cached = 0
        for r in rows:
            fin[repr(r.get("finish_reason"))] += 1
            native[repr(r.get("native_finish_reason"))] += 1
            cost += r.get("cost") or 0.0
            cached += 1 if r.get("cached_tokens") else 0
            per_prompt[r["prompt_id"]][0] += 1
            if blanked(r):
                per_prompt[r["prompt_id"]][1] += 1
        blanks = sum(v[1] for v in per_prompt.values())
        touched = {p: v for p, v in per_prompt.items() if v[1]}
        out["arms"][f.stem] = {
            "calls": len(rows),
            "finish_reasons": dict(fin),
            "native_finish_reasons": dict(native),
            "blankings": blanks,
            "blank_rate": round(blanks / len(rows), 4),
            "prompts_touched": len(touched),
            "prompts_total": len(per_prompt),
            "fully_silenced_prompts": sorted(p for p, v in touched.items()
                                             if v[1] == v[0]),
            "per_prompt_failed_of_total": {p: v for p, v in sorted(
                touched.items())},
            "spend_usd": round(cost, 4),
            "calls_with_cached_tokens": cached,
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
