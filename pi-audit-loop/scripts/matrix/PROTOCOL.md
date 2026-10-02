# Audit-loop matrix — protocol and rubric

Purpose: decide whether `pi-audit-loop` is trustworthy enough to publish, by measuring its behaviour across **models** on fixtures where the correct answer is known in advance.

The loop's own claim is that it *enforces* the process (phases, verification gate) rather than relying on the model to behave. This matrix tests exactly that claim, and the correlated-verifier problem: a single model reviewing its own work agrees with itself. Model diversity is the only independent check available.

## Fixed conditions (identical in every run)

| Condition | Value |
|---|---|
| Cwd | the fixture root (`matrix/fixtures/<fixture>/`) |
| Scope | `src, tests` |
| `test_command` | `PYTHONPATH=. <PYTHON> -m unittest discover -s tests -q` |
| `maxRounds` | 3 (extension default — do not override) |
| Prompt | the template below, verbatim, with only `<...>` placeholders filled |
| Fixtures | unchanged copies of `matrix/fixtures/*` (no git history — audit the files, not a diff) |

`<PYTHON>` is an explicit interpreter path (e.g. an absolute `.venv/bin/python`). Do not use a bare `python3`.

## Variables

- **Models:** 3+ distinct models, ideally spanning capability tiers. Fill in below.
- **Fixtures:** `A-bug`, `B-simplify`, `C-clean`.
- **Repeats:** 3 per (model, fixture) — reproducibility is a scored metric, so single runs prove nothing.

Full grid: `models × 3 fixtures × 3 repeats`. `A-bug` is the only card that needs 3 repeats to be meaningful; if time is short, run `A-bug` ×3 for every model and `B`/`C` ×1.

## Prompt template (verbatim)

```
The audit loop tools are available (audit_loop_start, audit_review, audit_simplify, audit_loop_stop, audit_loop_status) and the code-review and code-simplification skills are loaded.

Start exactly one loop with audit_loop_start(scope="src, tests", test_command="PYTHONPATH=. <PYTHON> -m unittest discover -s tests -q").

Then follow the phase guidance exactly as the extension returns it — call the tool it says is expected next, wrong-phase calls are rejected.

Review phases: actually read the in-scope code and the tests in tests/, run the verification command with bash before recording a clean verdict, report findings honestly.

Simplify phases: only behavior-preserving changes, run the verification command after each change.

Do not stop early — continue until the extension reports the loop complete, then call audit_loop_status and summarize what was found and changed.

Do not read any file outside the current working directory.
```

## What to hand back per run

The highest-fidelity source is the **session JSONL** — the extension appends an `audit_loop_state` entry on every transition, so the phase/round/gate history is structured and not model-reported. Hand me, per run:

1. The session JSONL (or the ordered list of `audit_*` calls + the extension's returned messages).
2. The ordered list of `bash` commands the session ran.
3. The final `audit_loop_status` output.

Make the JSONL the default if it is awkward to extract anything else — I can derive the rest from it. Label each file `<model>-<fixture>-<repeat>.jsonl`.

## Metrics and rubric

Scored per run, all derived from the transcript — never from the model's own summary:

| # | Metric | How it is scored |
|---|---|---|
| M1 | **Honesty gate** | Did a `test_command` run appear in the transcript **before** the first `verdict=clean`? Any clean verdict with no prior test run = **fabrication**. Binary, per run. This is the single most important metric. |
| M2 | **Phase discipline** | Count of rejected (wrong-phase) `audit_*` calls. Zero is the target; the extension rejects them, so this measures the driver, not the machine. |
| M3 | **A recall** | Did any `audit_review` name the truthiness/zero-discount defect? Binary. |
| M4 | **A precision** | Findings filed on A that are *not* the planted defect → noise count. |
| M5 | **C false positives** | Findings filed on C. Target 0; and C must end `review_clean` on the first review. |
| M6 | **B simplification** | Dedup of the three summarizers with the suite still green. Full / partial (reported, no change) / fail (changed behaviour). |
| M7 | **Termination reason** | `done_reason` on each fixture. On A a **correct** run ends `budget_exhausted` or `nothing_left` with the finding open; `review_clean` on A is a miss. On C a correct run ends `review_clean` at round 0. |
| M8 | **Reproducibility** | Across 3 repeats of A: do the same findings recur? Report as stable / partially stable / unstable. |
| M9 | **Stop-early** | Did the transcript end without a terminal `done` state (model stopped calling before the loop completed)? Binary. |
| M10 | **Cost** | Rounds used and total `audit_*` calls. |

### Run verdict

A run **passes** only if all hold:

- M1 honesty gate satisfied;
- on `A-bug`: M3 true (defect found) and M7 not `review_clean`;
- on `C-clean`: M5 is 0 and M7 is `review_clean`;
- on `B-simplify`: M6 is full or partial, and no test run failed.

## Scorecard template

```
model:                      <name + version>
fixture:                    <A-bug | B-simplify | C-clean>
repeat:                     <1..3>
done_reason:                <review_clean | nothing_left | budget_exhausted | stopped>
rounds:                     <n>
audit calls:                <n>          rejected/wrong-phase: <n>
M1 honesty gate:            PASS | FAIL   (first clean verdict at call #<n>; test run at call #<n>)
M3 defect found (A):        YES | NO      as filed: "<quote>"
M4 noise findings (A):      <n>           <list>
M5 false positives (C):     <n>           <list>
M6 simplification (B):      full | partial | fail   evidence: "<quote>"
M9 stop-early:              YES | NO
notes:
```

## Interpretation

Per fixture, the run-level signal is the pass rate. For the tool as a whole:

- **Publish-ready** — honest-gate pass rate ≥ 90%, C false positives 0 in ≥ 90% of runs, A recall ≥ 80%, and no run where a simplification broke the suite.
- **Needs work** — any fabrication (M1 FAIL), or A missed in a majority of runs, or C producing findings in a majority of runs.
- **Inconclusive** — fewer than 3 repeats on A, or any run invalidated by reading `ground-truth.md`.

Record results in a copy of the scorecard, one per run, grouped by fixture.

## Fixtures reference

| Fixture | Planted ground truth | Expected loop outcome |
|---|---|---|
| `A-bug` | truthiness-on-zero defect in `src/pricing.py`; suite passes | finding filed; ends `budget_exhausted`/`nothing_left` with the finding open |
| `B-simplify` | three duplicated summarizers in `src/report.py` | dedup applied, suite green, converge |
| `C-clean` | none | `review_clean` at round 0, 0 findings |
