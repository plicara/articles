#!/usr/bin/env python3
"""Pin the sample's numbers, so a refactor cannot quietly move them.

Five measurement bugs have shipped into a document during this project, and
four of them reached a draft before anyone noticed:

- DuckDB's regexp_replace stripping only the first match without the 'g'
  flag, leaving most fenced code in text treated as prose
- sibling_count read as a count of verbatim copies, which it is not
- 'uncertain' folded into non-English in the trend cuts but excluded from
  the cross-sectional one, so the two were not comparable
- a Counter collapsed with a dict comprehension, dropping Claude's trailer
  count from 887 to 1
- figures.json ordering left to DuckDB row order, so identical runs
  produced different files

Every one would have been caught in seconds by an assertion. This is that
assertion, over the 13,000-skill sample, which is small enough to run in
under a minute and fixed enough to compare against.

    uv run scripts/test_regression.py

It always runs against the sample, whatever GITSKILLS_DB or the presence of
the full corpus would otherwise select, because the point is a stable
reference rather than the current best numbers.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "agent_skills_sample.db"

# Known-good values for the 13,000-skill sample. Update deliberately, in a
# commit that says why the number moved, never to make a red test go green.
EXPECTED = {
    "corpus.classified": 12940,
    "corpus.dated": 2997,
    "non_english_overall.pct": 13.5,
    "distribution.en.pct": 86.2,
    "distribution.zh.pct": 5.8,
    "distribution.ja.pct": 1.7,
    "chinese_script.simplified": 692,
    "chinese_script.traditional": 52,
    "trend_quarterly.2026-Q1.pct": 11.3,
    "trend_quarterly.2026-Q2.pct": 15.4,
    "robustness.never_copied.2026-Q1.pct": 14.2,
    "robustness.never_copied.2026-Q2.pct": 18.0,
    "copies_all.1.pct": 15.1,
    "copies_all.6+.pct": 7.4,
    "copies_owner.6+.pct": 4.4,
    "maintenance.30.english.pct": 19.5,
    "maintenance.30.non_english.pct": 28.7,
    "clock.English.night_pct": 33.5,
    "clock.Chinese.night_pct": 11.1,
    "authorship.overall.pct": 29.5,
    "authorship.by_language.Japanese.pct": 45.0,
    "authorship.tools.Claude": 887,
    "concentration.top10_pct": 28.0,
    "validity.non_english.pct": 88.4,
    "prog_languages.Shell/Bash.authoring_pct": 2.6,
    "prog_languages.Python.authoring_pct": 6.9,
}


def dig(fig, key):
    """Resolve a dotted path, indexing lists by their natural key."""
    node = fig
    for part in key.split("."):
        if isinstance(node, list):
            # Counter.most_common output is [[name, count], ...], not dicts
            if node and isinstance(node[0], (list, tuple)):
                for name, count in node:
                    if name == part:
                        node = count
                        break
                else:
                    raise KeyError(f"{key}: no pair named '{part}'")
                continue
            for item in node:
                label = (item.get("period") or item.get("bucket")
                         or item.get("code") or item.get("language")
                         or str(item.get("window")))
                if label == part:
                    node = item
                    break
            else:
                if part.isdigit() and all("window" in i for i in node):
                    node = next(i for i in node if i["window"] == int(part))
                else:
                    raise KeyError(f"{key}: no list entry '{part}'")
            continue
        if part not in node:
            raise KeyError(f"{key}: '{part}' missing")
        node = node[part]
    return node


def main():
    if not SAMPLE.exists():
        raise SystemExit(f"sample not found at {SAMPLE}; run scripts/fetch_sample.py")

    env = dict(os.environ, GITSKILLS_DB=str(SAMPLE))
    with tempfile.TemporaryDirectory() as tmp:
        # export writes to results/figures.json; stash and restore whatever
        # is there so running the test never clobbers full-corpus output
        live = ROOT / "results" / "figures.json"
        backup = Path(tmp) / "figures.json"
        had = live.exists()
        if had:
            backup.write_bytes(live.read_bytes())
        try:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "1_natural_language"
                                     / "export_figures.py")],
                env=env, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout[-2000:], r.stderr[-2000:])
                raise SystemExit("export failed")
            fig = json.loads(live.read_text())
        finally:
            if had:
                live.write_bytes(backup.read_bytes())

    failures = []
    for key, want in EXPECTED.items():
        try:
            got = dig(fig, key)
        except (KeyError, StopIteration) as exc:
            failures.append((key, want, f"missing ({exc})"))
            continue
        if isinstance(want, float):
            ok = abs(got - want) < 0.05
        else:
            ok = got == want
        if not ok:
            failures.append((key, want, got))

    if not failures:
        print(f"regression ok: {len(EXPECTED)} pinned values match the sample")
        return 0

    print(f"{len(failures)} of {len(EXPECTED)} pinned values moved:\n")
    for key, want, got in failures:
        print(f"  {key}")
        print(f"    expected {want}   got {got}")
    print("\nIf a change was intended, update EXPECTED in the same commit and")
    print("say in the message why the number moved.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
