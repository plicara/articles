# Ground truth — matrix fixtures

Answer key for scoring. **Do not let an audited session read this file.** The fixtures live in `fixtures/<name>/`; a session's cwd is the fixture root and its scope is `src, tests`, so this file is outside its reach — but if a run's transcript shows it reading this, mark the run invalid.

---

## A-bug — one planted defect

File: `fixtures/A-bug/src/pricing.py`

```python
rate = discount if discount else DEFAULT_DISCOUNT
```

**Defect (correctness):** truthiness test on a `float` argument. `discount=0.0` is falsy, so it silently falls through to `DEFAULT_DISCOUNT` instead of meaning "no discount", contradicting the docstring.

- Observable: `order_total(100.0, 0.0)` returns `90.0`; it should return `100.0`.
- Fix: `rate = discount if discount is not None else DEFAULT_DISCOUNT`.
- **The test suite passes both before and after** — the bug is invisible to it. A reviewer has to read the code.

This is the same defect class that a real review of the StrategyTracker engine surfaced (`if invest_amount:`), which is deliberate: it tests whether the loop recognises the pattern.

**Success on A:** some `audit_review` names this defect (as a finding). The loop then cannot fix it behavior-preservingly, so it should end `budget_exhausted` or `nothing_left` with the finding **still open**. Ending `review_clean` = **miss**.

**Not counted as a finding:** style preferences, "add more tests for `discount=0.0`" (a reasonable *suggestion*, but it is not the defect), type-annotation nits. Any finding other than the truthiness/zero-discount defect counts against precision.

---

## B-simplify — one planted simplification

File: `fixtures/B-simplify/src/report.py`

`summarize_daily`, `summarize_monthly`, and `summarize_quarterly` are three copies of the same groupby-aggregate body; only the `key=` lambda differs.

**Ground-truth simplification:** extract one private helper, e.g.

```python
def _summarize(records, key):
    return [
        {"period": k, "total": round(sum(a for _, a in g), 2), "count": len(list(g))}
        for k, g in groupby(records, key=key)
    ]
```

and reduce the three public functions to one line each. Tests must still pass unchanged.

**Success on B:** the loop makes a behavior-preserving dedup of this shape and the full suite stays green after the change. Converging via `review_clean` or `nothing_left` both count.

**Failure modes:** finds the duplication but changes behaviour (tests break) — that is a **hard fail**; or reports it but makes no change and ends `nothing_left` — partial credit.

---

## C-clean — no planted issue

File: `fixtures/C-clean/src/stats.py`

Deliberately tidy: short functions, empty-input guards, no duplication, tests cover the guards.

**Ground truth: nothing.** A correct run returns `verdict=clean` with `findings=0` on the **first** review and ends `review_clean`.

Every finding filed here is a false positive. This is the fixture where weak or over-eager drivers fail loudly.
