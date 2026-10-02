# Dogfooding — the audit loop on two real projects

Run as a user would: no `-nc`, real test commands, real scopes. **A fresh copy of each project is made per run**, so the originals were never touched and runs cannot contaminate each other.

Model: `opencode-go/deepseek-v4.1-flash` (the most reliable of the three tested so far).

| Target | Source | Scope | Test command |
|---|---|---|---|
| Loadstar | [AdrianTJ/Loadstar](https://github.com/AdrianTJ/Loadstar) (Go) | `internal/job, internal/store` | `go test ./internal/job/... ./internal/store/...` |
| sqlite-utils | `github.com/simonw/sqlite-utils` (Python) | `sqlite_utils` | `PYTHONPATH=. .venv/bin/python -m pytest -q` |

---

## Loadstar — 6 findings, all fixed (which is the problem)

**Findings**, all real and one serious:

1. **`:memory:` store unusable under concurrency** (`internal/store/store.go`) — the WAL/FK pragmas are appended but the pool is never pinned, so each pooled connection gets its own empty database. Proven with a throwaway program: **197 of 200 concurrent `ListJobs` calls failed** with `no such table: jobs`. This is the repo's own documented test DSN, and the daemon runs workers + scheduler + retention concurrently.
2. **Failed `CancelJob` stranded the job forever** (`internal/job/manager.go`) — `pendingJobs` was deleted *before* the fallible `store.DeleteJob`; on failure the row stayed `PENDING` but workers skip untracked ids, so nothing would ever process it.
3. **`rows.Err()` swallowed** in `GetResultsByJobID` and `GetPendingWebhooks`, while every sibling read loop checks it — mid-iteration failures silently returned truncated results.
4. **One failed jobs purge blocked RUM retention**, letting the fastest-growing table grow unbounded.
5. Webhook retry comment advertised backoff the code never produced.
6. Webhook response body never drained, so every retry paid a fresh TCP+TLS handshake.

**Changes:** 5 files, +111 lines, 2 regression tests added red-first.

**Independently verified:** `go test ./internal/job/... ./internal/store/...` green; `gofmt -l` and `go vet` clean; and the claim that the removed `timeoutS <= 0` fallback was dead is **correct** — `SetDefaultTimeout` guards `seconds > 0` and the field initialises to 60.

**The problem:** every one of those 6 findings is a behaviour change, and every one was applied **in the simplify phase** — the phase defined as behaviour-preserving. The loop then reported `review_clean`. The fixes are good and the tests pass, but nothing reviewed them *as changes*; the guarantee the tool advertises did not hold.

---

## sqlite-utils — 3 findings left open, 3 real simplifications

**Findings (correctly left open, with reproductions):**

1. `rows_from_file(format=Format.TSV, ignore_extras=…)` raises instead of honouring the option — the TSV branch recurses into the CSV branch without forwarding `ignore_extras`/`extras_key` and applies the strategy twice.
2. **`cli.py:2488` — `rows --limit 0` returns every row.** `if limit:` treats `0` as unset; `docs/cli.rst` says "first N rows".
3. `insert_all()`/`upsert_all()` list-mode with `hash_id` writes shifted values and never computes the hash — silent data corruption.

**Changes (behaviour-preserving):**

- `db.py`: extracted `_pk_columns()`, replacing three copies of the pk-declaration-order sort.
- `cli.py`: extracted `_print_rows()`, replacing the duplicated table/CSV/TSV/JSON output block.
- `db.py`: extracted `Database._set_journal_mode()`, collapsing the byte-identical bodies of `enable_wal()`/`disable_wal()`.

**Independently verified:** 1485 passed, 19 skipped after the changes; diff confined to `db.py` and `cli.py`.

**Finding 2 reproduced by hand:** `--limit 1` → 1 row, `--limit 0` → **3 rows**. It is the same truthiness-on-zero defect class as the `A-bug` fixture and the original `invest_amount` bug — the loop rediscovered it unaided in unfamiliar production code.

Here the model **respected the behaviour-preservation rule**, ended `nothing_left`, and left the findings open for a human to fix.

---

## The dogfood conclusion

**The tool is genuinely useful on real code.** Two runs, nine real findings — a concurrency bug proven with a 200-goroutine probe, silent data corruption, an observable CLI defect — plus clean, test-verified simplifications. It also rediscovered a defect class it had seen only in fixtures.

**But the contrast between the two runs is the finding.** Same model, same loop, same instructions:

- Loadstar → used the simplify phase to fix 6 bugs, then reported clean.
- sqlite-utils → refused to change behaviour, left findings open, reported `nothing_left`.

The behaviour-preservation rule is **on the honour system**, and the same model obeyed it in one run and broke it in the next. This is the D-failing result reproduced on real code, at scale, on a repository someone actually depends on.

Practically: run the loop for its findings and its simplifications, but **never treat `review_clean` as "nothing changed". Diff the result before you keep it.**
