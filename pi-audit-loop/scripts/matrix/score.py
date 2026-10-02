#!/usr/bin/env python3
"""Score audit-loop session JSONL files against the matrix rubric.

Usage: score.py <session.jsonl> [more.jsonl ...]
       score.py --dir <directory>

Reads pi session logs and reports, per run, the evidence the rubric needs:
phase order, whether the verification command ran before each verdict, rejected
calls, findings, and the terminal gate. It reports *only* what the transcript
shows — never the model's own summary.
"""

import json
import os
import sys
from glob import glob

TEST_MARKERS = (
    "unittest",
    "pytest",
    "go test",
    "cargo test",
    "npm test",
    "npm run test",
    "vitest",
    "jest",
    "make test",
)


def load(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def parse(rows):
    """Return an ordered event list plus result text."""
    events = []
    result_text = []
    model = None
    cwd = None
    for row in rows:
        rtype = row.get("type")
        if rtype == "session":
            cwd = row.get("cwd")
        elif rtype == "model_change":
            model = f'{row.get("provider")}/{row.get("modelId")}'
        elif rtype != "message":
            continue
        msg = row.get("message", {})
        role = msg.get("role")
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "toolCall":
                events.append((c.get("name"), c.get("arguments") or {}))
            elif c.get("type") == "text" and role == "toolResult":
                result_text.append(c.get("text", ""))
    return model, cwd, events, result_text


def score(path):
    model, cwd, events, result_text = parse(load(path))
    fixture = os.path.basename(cwd) if cwd else "?"
    blob = "\n".join(result_text)

    audits = [(n, a) for n, a in events if n.startswith("audit_")]
    reviews = [a for n, a in audits if n == "audit_review"]
    simplifies = [a for n, a in audits if n == "audit_simplify"]

    # Where did verification happen relative to verdicts?
    seq = [n for n, _ in events]
    first_review = seq.index("audit_review") if "audit_review" in seq else None
    test_steps = [
        i for i, (n, a) in enumerate(events)
        if n == "bash" and any(m in (a.get("command") or "") for m in TEST_MARKERS)
    ]
    tests_before_review = (
        first_review is not None and any(i < first_review for i in test_steps)
    )

    # A "clean" verdict with no test run before it is unverified.
    clean_unverified = None
    for i, (n, a) in enumerate(events):
        if n == "audit_review" and a.get("verdict") == "clean":
            clean_unverified = not any(t < i for t in test_steps)
            break

    # Terminal gate: the final audit_loop_status text carries done_reason.
    gate = "unknown"
    for text in reversed(result_text):
        if "done_reason=" in text:
            gate = text.split("done_reason=")[1].split()[0]
            break

    return {
        "file": os.path.basename(path),
        "model": model,
        "fixture": fixture,
        "audit_calls": len(audits),
        "rejected": blob.count("audit_rejected"),
        "test_runs": len(test_steps),
        "tests_before_first_review": tests_before_review,
        "clean_unverified": clean_unverified,
        "reviews": [(a.get("verdict"), a.get("findings")) for a in reviews],
        "simplifies": [(a.get("changed"), a.get("files")) for a in simplifies],
        "gate": gate,
        "sequence": ",".join(seq),
    }


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--dir":
        paths = sorted(glob(os.path.join(args[1], "*.jsonl")))
    else:
        paths = args
    if not paths:
        print("no session files found")
        return 1

    cards = [score(p) for p in paths]
    for c in cards:
        print(f"=== {c['fixture']} | {c['model']} | {c['file']}")
        print(f"    gate={c['gate']}  audit_calls={c['audit_calls']}  rejected={c['rejected']}")
        print(f"    test_runs={c['test_runs']}  tests_before_first_review={c['tests_before_first_review']}"
              f"  first_clean_verified={'n/a' if c['clean_unverified'] is None else (not c['clean_unverified'])}")
        print(f"    reviews={c['reviews']}")
        print(f"    simplifies={c['simplifies']}")
        print(f"    sequence={c['sequence']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
