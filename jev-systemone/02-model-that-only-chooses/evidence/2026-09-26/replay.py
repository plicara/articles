"""Recompute the article's adventure tables from the released observations.

Python 3.10+, standard library only. No API calls or game installation.
Run from any directory; use --check to compare with committed results.json.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def compute():
    runs = {}
    for line in (HERE / "observations.jsonl").read_text().splitlines():
        row = json.loads(line)
        events = row["events"]
        commands = Counter(e["command"] for e in events)
        score = row["score_observations"][-1] if row["score_observations"] else None
        runs[row["run"]] = {
            "game": row["game"],
            "turns": len(events),
            "distinct_responses": len({e["response_id"] for e in events}),
            "score": score,
            "look_count": commands["look"],
            "look_percent": round(100 * commands["look"] / len(events), 2),
            "death_turn": row["death_turn"],
            "game_over_turn": row["game_over_turn"],
            "turns_underground": sum(e["underground"] is True for e in events),
        }
    comparisons = []
    for game in ("dreamhold", "905", "lostpig", "adventure"):
        for suffix, round_name in (("", "r3"), ("_r4", "r4")):
            if game == "adventure" and suffix:
                continue
            baseline = runs[f"{game}-baseline{suffix}"]
            configured = runs[f"{game}-r2_look_history{suffix}"]
            comparisons.append({
                "game": game, "round": round_name,
                "baseline": baseline["distinct_responses"],
                "configured": configured["distinct_responses"],
                "delta": configured["distinct_responses"] - baseline["distinct_responses"],
                "metric": "recognized rooms" if game == "adventure" else "distinct responses, not rooms",
            })
    return {
        "kind": "offline reanalysis of saved transcripts; not a new model run",
        "transcripts": len(runs), "decisions": sum(r["turns"] for r in runs.values()),
        "comparisons": comparisons,
        "round5": {k: v for k, v in runs.items() if k.endswith("_r5")},
        "look_baselines": {k: runs[k] for k in ("adventure-baseline", "dreamhold-baseline_r4")},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = compute()
    if args.check:
        expected = json.loads((HERE / "results.json").read_text())
        if result != expected:
            raise SystemExit("Recomputed results differ from results.json")
        print(f"Verified {result['transcripts']} transcripts and {result['decisions']} decisions.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
