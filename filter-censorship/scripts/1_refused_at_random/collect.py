"""Collect fresh filter-behavior evidence through OpenRouter.

Manifest-driven and resumable. Every response's FULL raw envelope is
persisted to data/raw/<arm>.jsonl, including native_finish_reason wherever
the aggregator exposes it -- the field the study's collector forgot.

Request config mirrors regexeval-2026 exactly: max_tokens 400, temperature
unset (provider default), provider pinned to Anthropic with fallbacks
disabled, require_parameters on. The only new discipline is that nothing is
discarded: blanked answers are the datum here.

    # plan without spending:
    python3 collect.py --manifest manifest.json --dry-run

    # spend, capped:
    python3 collect.py --manifest manifest.json --max-spend 8.00
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent / "data" / "raw"

# Study-faithful request body. temperature stays unset on purpose.
BASE_BODY = {
    "max_tokens": 400,
    "provider": {
        "order": ["Anthropic"],
        "allow_fallbacks": False,
        "require_parameters": True,
    },
}


def load_key():
    for line in (HERE.parents[1] / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.partition("=")[2].strip()
    sys.exit("OPENROUTER_KEY not found in filter-censorship/.env")


def call_once(key, model, prompt, provider_order):
    body = dict(BASE_BODY, model=model,
                messages=[{"role": "user", "content": prompt}])
    if provider_order:
        body["provider"] = dict(BASE_BODY["provider"],
                                order=provider_order)
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
            http_status = resp.status
    except urllib.error.HTTPError as e:
        payload = {"http_error_body": e.read().decode()[:2000]}
        http_status = e.code
    except Exception as e:  # transport-level: record, do not retry here
        payload = {"transport_error": repr(e)}
        http_status = None
    rec = {"ts": round(t0), "latency_s": round(time.time() - t0, 2),
           "model": model, "http_status": http_status, "raw": payload}
    ch = (payload.get("choices") or [{}])[0]
    rec["finish_reason"] = ch.get("finish_reason")
    rec["native_finish_reason"] = (ch.get("native_finish_reason")
                                   or payload.get("native_finish_reason"))
    usage = payload.get("usage") or {}
    rec["cost"] = usage.get("cost") or 0.0
    rec["completion_tokens"] = usage.get("completion_tokens")
    rec["cached_tokens"] = ((usage.get("prompt_tokens_details") or {})
                            .get("cached_tokens", 0))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--max-spend", type=float, required=True,
                    help="hard USD ceiling; the run aborts above it")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--worst-case-per-call", type=float, default=0.0027,
                    help="ceiling price used for planning estimates")
    ap.add_argument("--throttle-s", type=float, default=0.4)
    args = ap.parse_args()
    man = json.loads(args.manifest.read_text())

    RAW.mkdir(parents=True, exist_ok=True)
    remaining = 0
    total_calls = 0
    for arm in man["arms"]:
        out = RAW / f"{arm['name']}.jsonl"
        seen = set()
        if out.exists():
            for l in out.read_text().splitlines():
                if l.strip():
                    r = json.loads(l)
                    seen.add((r["prompt_id"], r.get("resend_index")))
        planned = [(p["id"], i) for p in arm["prompts"]
                   for i in range(arm["resends"])]
        total_calls += len(planned)
        remaining += sum(1 for k in planned if k not in seen)

    worst = remaining * args.worst_case_per_call
    print(f"{remaining} of {total_calls} calls remain across "
          f"{len(man['arms'])} arm(s); worst-case ${worst:.2f} vs cap "
          f"${args.max_spend:.2f}")
    if worst > args.max_spend:
        sys.exit("refusing: worst case exceeds cap; raise --max-spend or trim")

    if args.dry_run:
        for arm in man["arms"]:
            n = len(arm["prompts"]) * arm["resends"]
            print(f"  arm {arm['name']:24s} {arm['model']:28s} "
                  f"{len(arm['prompts']):4d} prompts x{arm['resends']} = {n}")
        print("dry run: no network, no spend")
        return

    key = load_key()
    RAW.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    done = 0
    for arm in man["arms"]:
        out = RAW / f"{arm['name']}.jsonl"
        seen = set()
        if out.exists():
            for l in out.read_text().splitlines():
                if l.strip():
                    r = json.loads(l)
                    seen.add((r["prompt_id"], r.get("resend_index")))
        with out.open("a") as fh:
            for p in arm["prompts"]:
                for i in range(arm["resends"]):
                    if (p["id"], i) in seen:
                        continue  # resume where we left off
                    rec = call_once(key, arm["model"], p["prompt"],
                                    arm.get("provider_order"))
                    rec.update(arm=arm["name"], prompt_id=p["id"],
                               resend_index=i)
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    spent += rec["cost"] or 0.0
                    done += 1
                    if done % 25 == 0:
                        print(f"  {done} calls, ${spent:.4f} spent")
                    if spent > args.max_spend:
                        sys.exit(f"SPEND CAP HIT at ${spent:.4f}; partial "
                                 f"data safe in {out}; rerun to resume")
                    time.sleep(args.throttle_s)
    print(f"done: {done} calls, ${spent:.4f}")


if __name__ == "__main__":
    main()
