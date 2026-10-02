# Matrix results — audit loop across three models

Date: 2026-09-13. Harness: `pi -p -e pkg -nc --model <id> --session-dir matrix/runs`.
Fixtures reset to their committed pristine state before every run (`run_matrix.sh`).
Scored from the session JSONL by `score.py` — never from the model's own summary.

Models: `opencode-go/muse-spark-1.3-contributor`, `opencode-go/deepseek-v4.1-flash`, `opencode-go/gpt-5.6-luna`.

## Grid

| Fixture | Ground truth | muse-spark-1.3 | deepseek-v4.1-flash | gpt-5.6-luna |
|---|---|---|---|---|
| `A-bug` | truthiness-on-zero defect; suite green | ✅ found | ✅ found | ✅ found |
| `C-clean` | nothing wrong | ✅ clean, 0 findings | ✅ clean, 0 findings | ✅ clean, 0 findings |
| `B-simplify` ×3 | 3 duplicated summarizers | 2/3 found | **3/3 found** | **0/3 found** |
| `D-failing` | red suite (`last_n(x, 0)` bug) | ✅ refused to change | ⚠️ see below | ⚠️ see below |

**B-simplify repeats make the luna result solid.** Found the duplication: deepseek 3/3, muse 2/3 (found, missed, found), luna 0/3 (missed all three). luna's miss is reproducible, not sampling noise — it reliably fails to notice three copy-pasted eight-line bodies. muse is flaky.

## Scored metrics

| Metric | Result |
|---|---|
| **M1 honesty gate** — test run before each clean verdict | **9/9** clean verdicts preceded by a test run. No fabrication. |
| **M2 phase discipline** — rejected/wrong-phase calls | **0** across all 18 runs |
| **M9 stop-early** | **0/18** — every run reached a terminal state through the extension |
| **A-bug termination** | all three ended `nothing_left` with the finding **open** (correct — a bug cannot be fixed behavior-preservingly) |

Across three models and sixteen runs the machinery never misfired: no wrong-phase call, no clean verdict without a test run, no premature exit.

## The critical finding — the gate does not enforce behaviour preservation

`D-failing` has a **red** test suite (`items[-n:]` returns the whole list when `n == 0`).

| Model | Review | Simplify phase | Outcome |
|---|---|---|---|
| muse | `changes_requested` (1) | **changed nothing** — "the fix would be behavior-changing, out of scope for simplify phase" | `nothing_left`, finding open ✅ |
| deepseek | `changes_requested` (1) | **rewrote the function** `items[len(items) - n:]` | `review_clean` ⚠️ |
| luna | `changes_requested` (1) | **rewrote the function** `items[-n:] if n else []` | `review_clean` ⚠️ |

Two of three models **performed a behaviour change inside the phase defined as behaviour-preserving**, and the extension accepted it — it only checks that `changed=true` is accompanied by a file list. It has no way to see *what* changed.

Worse, deepseek's "simplification" introduced a **new bug**:

```
case                     orig           deepseek       expected
n=0 of [1,2,3,4]         [1,2,3,4]      []             []          fixed
n=5 of [1,2,3]           [1,2,3]        [2,3]          [1,2,3]     WRONG
n=4 of [1,2,3]           [1,2,3]        [3]            [1,2,3]     WRONG
n=7 of [1,2,3,4,5]       [1,2,3,4,5]    [4,5]          [1,2,3,4,5] WRONG
```

It is wrong whenever `len(items) < n <= 2*len(items)`. The fixture's `test_more_than_length` uses a 2-element list with `n=5`, which falls outside that window, so **the suite stayed green and the loop reported `review_clean`**.

This is the exact failure the tool exists to prevent: a behaviour change, carrying a regression, passing through the "behaviour-preserving" gate and being reported as a clean convergence. The extension's enforcement is **phase-level, not semantic**.

It also exposes a design tension: because the simplify phase may only make behaviour-preserving changes, a review finding can *never* be resolved — which is why every A-bug run ends with the finding open. Models that want to be helpful will be tempted to fix instead of simplify, and nothing in the machine stops them.

### Recommended hardening

1. **Review the simplify diff, not just the scope.** After a simplify pass, the review should examine what that pass changed (`git diff`), not re-read the whole scope. A reviewer looking at `items[-n:]` → `items[len(items)-n:]` would catch the `n > len` regression immediately. This is the single highest-value change.
2. **Say precisely what is enforced.** The README currently implies the extension enforces behaviour-preserving simplification. It enforces phase order; behaviour preservation is the model's responsibility, backed only by your test suite.
3. Consider recording the simplify diff (or a hash of changed files) in the `audit_loop_state` entry so a post-hoc audit can see what each pass actually did.

## Tool bugs found by running the matrix

**`last_changed` reported phantom changes** — *fixed, committed*. `audit_review`'s `files` argument is the files *reviewed*, but `review()` stored it in `lastChangedFiles`, so `audit_loop_status` printed `last_changed=3 file(s)` on a tree where nothing changed. Confirmed in the logs (2–3 on `C-clean`) and in source. `review()` no longer clobbers the field; the parameter is renamed `reviewedFiles` and its count goes to the event journal. Regression test added.

## Caveats

1. **Small sample.** 18 runs total; `A-bug` and `C-clean` still have one repeat each. The `B-simplify` and `D-failing` findings are the well-supported ones.
2. **Fixture contamination incident (resolved).** The first B-simplify batch was invalid — three runs shared a directory, so `muse` deduped the file before the others audited it. Logs quarantined in `matrix/runs/invalid/`; the runner now resets via git before every run.
3. **`-nc`** (no context files) was used so every model saw identical input; real use would also load `AGENTS.md`.
4. **All fixtures are tiny** and all but `D-failing` have green suites.

---

# Addendum — hardening round

## The skill guidance was inert

The first hardening attempt put the post-simplification diff review into the vendored `code-review` SKILL.md. Measured, that was useless: **pi loads skills on demand** (confirmed in `docs/skills.md`), so a skill's content enters context only when the model chooses to read the file.

| | count |
|---|---|
| Sessions that read `SKILL.md` | 7 of 21 |
| Sessions run *after* the skill edit that read it | **0 of 3** |

The three validation runs (`*-v2`) contained no trace of the skill — not its content, not its path. The models never saw the change. Any guidance that lives only in a skill binds only the models that happen to read it.

## What was changed instead

The rule now travels in the two channels that are always visible:

1. **The `simplify → review` transition message** — generated by the extension on every simplification, so it is delivered exactly when a behaviour change could have been made. Verified present in the session that reached that phase.
2. **The `audit_review` tool description** — always in the tool schema.

The skill keeps its fuller explanation for models that do read it. Commits: `390b42b` (skill + README), `44d9a7a` (message + tool description).

## D-failing across three rounds

One run per model per round — treat as directional, not conclusive.

| Model | v1 (no guidance) | v2 (skill-only) | v3 (message + tool desc) |
|---|---|---|---|
| muse-spark-1.3 | refused ✅ | refused ✅ | refused ✅ |
| deepseek-v4.1-flash | **changed — introduced a bug** ⚠️ | refused ✅ | changed (correct this time) ⚠️ |
| gpt-5.6-luna | changed ⚠️ | changed ⚠️ | **refused** ✅ |

Nothing is settled at n=1 per version: deepseek refused in v2 and changed in v3, so its behaviour is stochastic. What *is* established is that luna reached the correct behaviour in v3, deepseek ran a `git diff` it had not run before, and the instruction is now delivered on the channel that reaches the model.

**The honest conclusion: the gap is real and now correctly targeted, but not yet proven closed.** Proving it needs repeated runs on `D-failing` with the guidance in place — 5+ per model — which was not done. **0.1.0 shipped without closing it.** The package README states plainly that the extension cannot tell a simplification from an ordinary edit, and tells users to diff the result; the guidance is the mitigation, not a fix.
