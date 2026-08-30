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

Both articles' exports are covered. Article 02's pins deliberately leave out
`by_written_language`, which needs the language cache built by
classify_languages.py, and `over_time`, which the sample has too few dated
skills to populate. Pinning either would make the test pass or fail on what
happens to be in data/ rather than on the code.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "agent_skills_sample.db"
SAMPLE_PARQUET = ROOT / "data" / "parquet"


def sample_env():
    """Point the run at the sample, in whichever form this machine can read.

    Both forms hold the same 13,000 rows, so the pinned values below must
    hold for either, and that equivalence is part of what this test checks.
    SQLite is preferred because it is what fetch_sample.py downloads, but
    reading it needs DuckDB's `sqlite` extension fetched from DuckDB's
    extension repository at runtime. Where egress policy blocks that
    repository the SQLite sample is present and unreadable, so the choice is
    made by probing rather than by looking for the file.
    """
    if SAMPLE.exists() and _can_read_sqlite():
        return dict(os.environ, GITSKILLS_DB=str(SAMPLE)), f"sqlite {SAMPLE}"
    if (SAMPLE_PARQUET / "artifacts").is_dir():
        env = {k: v for k, v in os.environ.items() if k != "GITSKILLS_DB"}
        return dict(env, GITSKILLS_PARQUET=str(SAMPLE_PARQUET)), f"parquet {SAMPLE_PARQUET}"
    if SAMPLE.exists():
        raise SystemExit(
            "the sqlite sample is present but DuckDB cannot load its sqlite "
            "extension here; run scripts/sample_to_parquet.py once and retry")
    raise SystemExit(
        f"sample not found at {SAMPLE}; run scripts/fetch_sample.py")


def _can_read_sqlite() -> bool:
    import duckdb
    try:
        con = duckdb.connect()
        con.execute("INSTALL sqlite")
        con.execute("LOAD sqlite")
        return True
    except Exception:
        return False

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

# Article 02, same sample. Three of these pin a definition rather than a
# measurement, and each moved once during development: "ships code" excluding
# root-level skills, the extension map that silently zeroed C# and PowerShell,
# and the composition split between docs and code.
EXPECTED_02 = {
    "corpus.skills": 13000,
    "corpus.repos": 11841,
    "ships_code.nonroot.pct": 10.45,
    "ships_code.nonroot.k": 1342,
    "ships_code.all.pct": 11.27,
    "bundles_nothing.pct": 65.69,
    "composition_files.total": 39034,
    "composition_files.kinds.docs.pct": 52.9,
    "composition_files.kinds.code.pct": 26.2,
    "mention_vs_ship.Python.ratio": 2.9,
    "mention_vs_ship.Shell/Bash.ratio": 15.9,
    "reuse.1.ships.pct": 10.68,
    "reuse.6+.ships.pct": 17.21,
    "spec_layout.rows.references/.pct": 25.6,
    "spec_layout.rows.scripts/.pct": 11.2,
    "spec_layout.rows.assets/.pct": 3.6,
}

# (label, export script, results file, pins, extra argv)
EXPORTS = [
    ("article 01", "1_natural_language", "figures.json", EXPECTED, ["--force"]),
    ("article 02", "2_programming_languages", "figures_02.json", EXPECTED_02, []),
]


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
                         or item.get("kind") or item.get("place")
                         or item.get("lang") or item.get("group")
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


def run_export(env, pkg, results_name, argv):
    """Run one export against the sample and return what it wrote.

    The live results file is stashed and restored, so running the test never
    clobbers a full-corpus export. That mattered the first time this ran on a
    machine that had one: the sample values overwrote it and the article was
    rebuilt from them before anyone noticed.
    """
    live = ROOT / "results" / results_name
    with tempfile.TemporaryDirectory() as tmp:
        backup = Path(tmp) / results_name
        had = live.exists()
        if had:
            backup.write_bytes(live.read_bytes())
        try:
            r = subprocess.run(
                [sys.executable,
                 str(ROOT / "scripts" / pkg / "export_figures.py"), *argv],
                env=env, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout[-2000:], r.stderr[-2000:])
                raise SystemExit(f"{pkg} export failed")
            return json.loads(live.read_text())
        finally:
            if had:
                live.write_bytes(backup.read_bytes())


def compare(fig, expected):
    failures = []
    for key, want in expected.items():
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
    return failures


def main():
    env, form = sample_env()
    print(f"sample form: {form}\n")

    failures, pinned = [], 0
    for label, pkg, results_name, expected, argv in EXPORTS:
        # --force on article 01 because its export refuses to shrink
        # figures.json, and this test deliberately writes sample values over
        # it. Safe only because run_export stashes and restores the live file.
        fig = run_export(env, pkg, results_name, argv)
        bad = compare(fig, expected)
        pinned += len(expected)
        failures += [(label, *f) for f in bad]
        print(f"  {label}: {len(expected) - len(bad)}/{len(expected)} pinned "
              f"values match")

    if not failures:
        print(f"\nregression ok: {pinned} pinned values match the sample")
        return 0

    print(f"\n{len(failures)} of {pinned} pinned values moved:\n")
    for label, key, want, got in failures:
        print(f"  {label}  {key}")
        print(f"    expected {want}   got {got}")
    print("\nIf a change was intended, update EXPECTED in the same commit and")
    print("say in the message why the number moved.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
