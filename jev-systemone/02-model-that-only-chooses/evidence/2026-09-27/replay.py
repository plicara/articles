"""Replay the recovered extraction and Doom observations. No API calls.

python3 replay.py > results.json
python3 replay.py --check
"""

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rate(rows, label, flag):
    result = {}
    for name in ("WRONG", "OK"):
        group = [r for r in rows if r[label] == name]
        flagged = sum(flag(r) for r in group)
        result[name] = {"flagged": flagged, "total": len(group),
                        "rate": flagged / len(group) if group else None}
    return result


def compute():
    rows = [json.loads(line) for line in (HERE / "extraction.jsonl").read_text().splitlines()]
    assert len({r["task_id"] for r in rows}) == len(rows)
    paired = [r for r in rows if r["peers"] > 0]
    extraction = {"in_text_verdicts": len(rows), "peer_eligible": len(paired),
                  "label_transitions": dict(collections.Counter(r["label_v1"] + " -> " + r["label_v2"] for r in rows)),
                  "labels": {}}
    for label in ("label_v1", "label_v2"):
        # All comparison rows use the same eligible tasks. Pairwise is the
        # exact expected disagreement with a uniformly selected nonempty peer.
        table = {
            "jev_boolean": rate(paired, label, lambda r: r["boolean"] < 0.5),
            "peer_majority": rate(paired, label, lambda r: r["peer_disagree"] >= r["peers"] / 2),
            "uniform_peer": rate(paired, label, lambda r: r["peer_disagree"] / r["peers"]),
        }
        e4 = [r for r in rows if r["exact"] is not None and r["crossref"] is not None]
        e2 = [r for r in rows if r["focused"] is not None and r["enriched"] is not None]
        low = [r for r in rows if r["boolean"] < 0.05 and r[label] in ("OK", "WRONG")]
        calibration = []
        for bin_id in range(10):
            group = [r for r in rows if r[label] in ("OK", "WRONG") and min(9, int(r["boolean"] * 10)) == bin_id]
            if group:
                calibration.append({"bin": bin_id, "total": len(group),
                                    "mean_probability": sum(r["boolean"] for r in group) / len(group),
                                    "correct": sum(r[label] == "OK" for r in group)})
        bad = [r for r in paired if r[label] == "WRONG"]
        extraction["labels"][label] = {
            "comparison": table,
            "all_boolean": rate(rows, label, lambda r: r["boolean"] < 0.5),
            "e4_boolean": rate(e4, label, lambda r: r["boolean"] < 0.5),
            "e4_fused": rate(e4, label, lambda r: min(r["boolean"], r["exact"], r["crossref"]) < 0.5),
            "e2_baseline": rate(e2, label, lambda r: r["boolean"] < 0.5),
            "e2_focused": rate(e2, label, lambda r: r["focused"] < 0.5),
            "e2_enriched": rate(e2, label, lambda r: r["enriched"] < 0.5),
            "below_005": {"correct": sum(r[label] == "OK" for r in low), "total": len(low)},
            "exactly_zero_count": sum(r["boolean"] == 0 for r in rows),
            "calibration": calibration,
            "majority_only_catches": sum(r["peer_disagree"] >= r["peers"] / 2 and r["boolean"] >= 0.5 for r in bad),
            "jev_only_catches": sum(r["peer_disagree"] < r["peers"] / 2 and r["boolean"] < 0.5 for r in bad),
        }
    doom = []
    for line in (HERE / "doom.jsonl").read_text().splitlines():
        r = json.loads(line)
        episodes = collections.defaultdict(list)
        for tic in r["tics"]:
            episodes[tic["episode"]].append(tic)
        doom.append({"run": r["run"], "seed": r["seed"], "arm": r["arm"],
                     "seconds": len(r["tics"]) / r["tics_per_second"],
                     "kills": sum(max(t["kills"] for t in e) for e in episodes.values()),
                     "deaths": sum(e[-1]["finished"] and e[-1]["health"] <= 0 for e in episodes.values())})
    totals = {arm: {metric: sum(r[metric] for r in doom if r["arm"] == arm)
                    for metric in ("kills", "deaths", "seconds")}
              for arm in ("prose_v5", "grid_v3_control")}
    seeds = {r["seed"] for r in doom}
    assert all(sum(r["seed"] == s and r["arm"] == a for r in doom) == 1 for s in seeds for a in totals)
    return {"kind": "offline reanalysis of recovered records; no new inference",
            "extraction": extraction, "doom": {"runs": doom, "totals": totals,
            "kill_change_percent": 100 * (totals["prose_v5"]["kills"] / totals["grid_v3_control"]["kills"] - 1)}}


def figures(result):
    labels = result["extraction"]["labels"]["label_v2"]
    start = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 400" role="img"><style>.jv{font:18px Georgia,serif;fill:var(--pl-text,#05192B)}.jv .rule{stroke:var(--pl-rule,#C9C2B4)}.jv .bar{fill:var(--pl-series-1,#31606D)}.jv .false{fill:var(--pl-orange,#EE8B33)}</style><g class="jv">'
    bars = [start, '<title>Replayed question bank: detection and false alarms under revised labels</title><text x="24" y="34">Question bank, recovered records</text>']
    for i, (key, name) in enumerate((("e4_boolean", "Boolean"), ("e4_fused", "Boolean + exact + crossref"))):
        y = 100 + 140 * i
        bars.append(f'<text x="24" y="{y-18}">{name}</text>')
        for offset, label, css in ((0, "WRONG", "bar"), (46, "OK", "false")):
            value = labels[key][label]["rate"]
            bars.append(f'<rect class="{css}" x="24" y="{y+offset}" width="{value*600:.2f}" height="28"/><text x="{36+value*600:.2f}" y="{y+offset+21}">{value:.1%} {"caught" if label == "WRONG" else "false alarms"}</text>')
    bars.append('<text x="24" y="385">Same scored fields; threshold 0.5; percentages of each label class.</text></g></svg>')
    curve = [start, '<title>Observed correctness versus mean Jev probability, revised labels</title><text x="24" y="30">Does the reported probability track correctness?</text><path class="rule" fill="none" d="M80 335H760 M80 335V55 M80 335L760 55"/>']
    for b in labels["calibration"]:
        x = 80 + 680 * b["mean_probability"]
        y = 335 - 280 * b["correct"] / b["total"]
        curve.append(f'<circle class="bar" cx="{x:.2f}" cy="{y:.2f}" r="7"><title>{b["correct"]}/{b["total"]} correct; mean probability {b["mean_probability"]:.3f}</title></circle>')
    curve.append('<text x="80" y="365">0</text><text x="740" y="365">1</text><text x="45" y="65">1</text><text x="45" y="335">0</text><text x="270" y="390">Mean reported probability</text><text x="22" y="250" transform="rotate(-90 22 250)">Fraction correct</text></g></svg>')
    return {"fig-4-question-bank.svg": "".join(bars) + "\n", "fig-6-calibration.svg": "".join(curve) + "\n"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--figures", action="store_true")
    args = parser.parse_args()
    result = compute()
    if args.figures:
        for name, svg in figures(result).items():
            (HERE.parents[1] / name).write_text(svg)
    elif args.check:
        if result != json.loads((HERE / "results.json").read_text()):
            raise SystemExit("Results differ from the observation replay")
        print("Extraction and Doom results reproduced from the released observations.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
