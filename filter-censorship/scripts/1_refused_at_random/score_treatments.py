"""What the blanked calls did to the benchmark result.

A harness that meets a filtered call has three options and no guidance:
drop the row, score it wrong, or correct for it. This scores the
StructuredRegex corpus all three ways and reports where claude-opus-5
lands on the leaderboard under each, which is the cost of leaving the
choice undocumented.

Also computes how often k samples would have caught the filter at all,
at the rate we measured during the study and at the rate it runs today.

    python3 score_treatments.py \
        --predictions ../../../regexeval-2026/predictions/structuredregex \
        --bias ../../results/1_refused_at_random/blocked_subset_bias.json \
        --out ../../results/1_refused_at_random/score_treatments.json

No API calls: everything comes from files already committed in the study.
"""
from __future__ import annotations

import argparse
import json
import re
import signal
from pathlib import Path


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def full_match(pattern, text):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, 2)
    try:
        return re.fullmatch(pattern, text) is not None
    except (_Timeout, re.error, RecursionError, OverflowError):
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def passes(pattern, pos, neg):
    return (all(full_match(pattern, s) is True for s in pos)
            and all(full_match(pattern, s) is False for s in neg))


def filter_blanked(row):
    """The filter's signature: an upstream content_filter stop, no text."""
    return "finish_reason='content_filter'" in (row.get("error") or "")


def scorable(row):
    return row.get("status") == "ok" and bool(row.get("pattern"))


def load(label, pred_dir):
    rows = [json.loads(l) for l in
            (pred_dir / f"{label}.jsonl").read_text().splitlines() if l.strip()]
    return [r for r in rows if not r["task_name"].startswith("control/")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", type=Path, required=True)
    ap.add_argument("--bias", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--subject", default="claude-opus-5")
    args = ap.parse_args()

    delta = json.loads(args.bias.read_text())["mean_diff_points"]

    board = {}
    for path in sorted(args.predictions.glob("*.jsonl")):
        rows = load(path.stem, args.predictions)
        scored = [r for r in rows if scorable(r)]
        board[path.stem] = {
            "passes": sum(passes(r["pattern"], r["pos"], r["neg"]) for r in scored),
            "scored": len(scored),
            "instances": len(rows),
            "blanked": sum(1 for r in rows if filter_blanked(r)),
        }

    me = board[args.subject]
    kept, blanked = me["scored"], me["blanked"]
    pass_kept = 100 * me["passes"] / kept
    # Denominator for every treatment: the rows the filter either let
    # through or blanked. Rows unscorable for unrelated reasons are a
    # different problem and are excluded from all three alike.
    n = kept + blanked

    treatments = {
        # What most harnesses do by default: the row never reaches scoring.
        "drop": pass_kept,
        # What a harness that marks filtered calls non-retriable does.
        "count_wrong": 100 * me["passes"] / n,
        # Impute the blanked rows at the difficulty the other models found
        # them to have, rather than assuming they were average.
        "corrected": (kept * pass_kept + blanked * (pass_kept + delta)) / n,
    }

    others = sorted(((m, 100 * v["passes"] / v["scored"])
                     for m, v in board.items() if m != args.subject),
                    key=lambda x: -x[1])
    ranks = {}
    for name, score in treatments.items():
        ordered = sorted(others + [(args.subject, score)], key=lambda x: -x[1])
        ranks[name] = 1 + [m for m, _ in ordered].index(args.subject)

    # Detection: chance that k samples of one affected task show the filter
    # at least once, at the study-window rate and at today's rate.
    def curve(rate):
        return [round(100 * (1 - (1 - rate) ** k), 1) for k in range(1, 11)]

    out = {
        "generated": "2026-08-26",
        "source": "regexeval-2026 predictions/structuredregex (committed)",
        "subject": args.subject,
        "denominator": n,
        "kept": kept,
        "blanked": blanked,
        "bias_delta_points": delta,
        "scores": {k: round(v, 1) for k, v in treatments.items()},
        "ranks": ranks,
        "field_size": len(board),
        "spread_points": round(max(treatments.values()) - min(treatments.values()), 1),
        "rank_spread": max(ranks.values()) - min(ranks.values()),
        "board": [{"model": m, "score": round(s, 1)} for m, s in others],
        "detection": {
            "k": list(range(1, 11)),
            "study_rate_pct": 64.4,
            "today_rate_pct": 1.8,
            "study": curve(0.644),
            "today": curve(0.018),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for name in ("drop", "count_wrong", "corrected"):
        print(f"{name:12} {treatments[name]:5.1f}  rank {ranks[name]} of {len(board)}")
    print(f"spread {out['spread_points']} points, {out['rank_spread']} places")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
