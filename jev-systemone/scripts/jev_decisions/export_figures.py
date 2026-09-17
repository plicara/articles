"""Export every number the Jev article uses. No published figure is typed by hand.

Reads audited benchmark artifacts only (the frozen chat release and the Jev
v2 release) and writes results/jev_decisions/figures.json.

  python3 scripts/jev_decisions/export_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
OUT = PROJ / "results" / "jev_decisions" / "figures.json"
WB = HERE.parents[3] / "benchmarks" / "adventurebench"


def median_latency(run_id: str, slug: str) -> float:
    manifest = json.loads((WB / "runs" / run_id / "manifest.json").read_text())
    responses = WB / "runs" / run_id / manifest["models"][slug]["responses_file"]
    vals = sorted(json.loads(line)["latency_ms"] for line in responses.read_text().splitlines())
    count = len(vals)
    return round(vals[count // 2] if count % 2 else (vals[count // 2 - 1] + vals[count // 2]) / 2, 1)


def main() -> None:
    release = json.loads((WB / "releases/20260903-plicara-v1-expanded/release.json").read_text())
    intervals = {s["model_slug"]: s["interval"] for s in release["bootstrap"]["score_intervals"]}
    chat_models = []
    for model in release["models"]:
        chat_models.append({
            "slug": model["model_slug"],
            "name": model["provenance"]["resolved"]["model"],
            "score": model["overall"]["score"],
            "passed": model["overall"]["passed"],
            "total": model["overall"]["total"],
            "cost": model["evidence"]["recorded_cost_usd"],
            "run_id": model["run_id"],
            "latency_ms": median_latency(model["run_id"], model["model_slug"]),
            "ci": [round(v, 3) for v in intervals[model["model_slug"]]],
        })
    jev_run_id, pinned_run_id = "20260917-jev-v2-full", "20260917-jev-v2-pinned-full"
    jev_records = [json.loads(line) for line in
                   (WB / f"runs/{jev_run_id}/responses/jev-latest.jsonl").read_text().splitlines()]
    said_unclear = [r for r in jev_records if r["outcome"] == {"action": "unclear", "target": None}]
    unclear_precision = round(sum(1 for r in said_unclear if ["unclear", None] in r["expected_outcomes"]) / len(said_unclear), 3)
    gold_unclear = [r for r in jev_records if r["expected_outcomes"] == [["unclear", None]]]
    unclear_recall = round(sum(1 for r in gold_unclear if r["outcome"] == {"action": "unclear", "target": None}) / len(gold_unclear), 3)
    jev_release = json.loads((WB / "releases/20260917-plicara-jev-v2/release.json").read_text())
    jev_model = next(m for m in jev_release["models"] if m["model_slug"] == "jev-latest")
    jev_interval = next(s["interval"] for s in jev_release["bootstrap"]["score_intervals"]
                        if s["model_slug"] == "jev-latest")
    jev_derived = json.loads((WB / f"results/{jev_run_id}/jev-latest.json").read_text())
    pinned_model = next(m for m in jev_release["models"] if m["model_slug"] == "jev-1-13-0")
    jev = {
        "slug": "jev-latest",
        "resolved": jev_model["provenance"]["resolved"]["model"],
        "score": jev_model["overall"]["score"],
        "passed": jev_model["overall"]["passed"],
        "total": jev_model["overall"]["total"],
        "cost": jev_model["evidence"]["recorded_cost_usd"],
        "latency_ms": median_latency(jev_run_id, "jev-latest"),
        "threshold": 0.9,
        "mapping_threshold": 0.75,
        "repetitions": 3,
        "ci": [round(v, 3) for v in jev_interval],
        "by_tag": jev_derived["by_tag"],
    }
    eval_fails = [r for r in jev_records if not r["passed"]]
    eval_refusals = sum(1 for r in eval_fails if r["outcome"] == {"action": "unclear", "target": None})
    pinned_records = [json.loads(line) for line in
                      (WB / f"runs/{pinned_run_id}/responses/jev-1-13-0.jsonl").read_text().splitlines()]
    pinned = {(r["case_id"], r["repetition"]): (r["outcome"]["action"], r["outcome"]["target"])
              for r in pinned_records}
    alias_agree = sum(1 for r in jev_records
                      if (r["outcome"]["action"], r["outcome"]["target"]) == pinned[(r["case_id"], r["repetition"])])
    ministral8b = next(c["score"] for c in chat_models if c["slug"] == "mistralai-ministral-8b-2512")
    OUT.write_text(json.dumps({
        "chat_models": chat_models,
        "jev": jev,
        "ci_lo": round(jev_interval[0], 3),
        "ci_hi": round(jev_interval[1], 3),
        "unclear_precision": unclear_precision,
        "unclear_recall": unclear_recall,
        "eval_fails": len(eval_fails),
        "eval_refusal_fails": eval_refusals,
        "alias_agree": alias_agree,
        "alias_total": len(jev_records),
        "pinned_score": pinned_model["overall"]["score"],
        "pinned_passed": pinned_model["overall"]["passed"],
        "pinned_total": pinned_model["overall"]["total"],
        "ministral8b_score": ministral8b,
        "jev_by_tag": jev_derived["by_tag"],
    }, indent=1) + "\n")
    print(f"wrote {OUT} (jev {jev['score']:.3f}, {len(chat_models)} chat models)")


if __name__ == "__main__":
    main()
