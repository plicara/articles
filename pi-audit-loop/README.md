# Pi Audit Loop

Evidence behind the article [What I learned rebuilding Pi Audit Loop](https://plicara.ai/research/pi-audit-loop/), on the [`@plicara/pi-audit-loop`](https://github.com/plicara/pi-audit-loop) package for the pi coding agent. It exists so a reader can check the numbers that can be checked, and can see which ones cannot.

## What is in here

| Path | What it is |
| --- | --- |
| `results/evidence.json` | Per-session counts for the original v0.1.0 runs: verdicts, findings, test results seen before each call, skill reads, terminal state, with the session hash, model and fixture. Session ids are renumbered `s01` to `s30`. |
| `results/matrix.md`, `results/dogfood.md` | Run summaries for the fixture matrix and the two real-repository runs. |
| `results/figures.json` | The numbers the article quotes for the original experiment. |
| `results/sweep-outcomes.json` | The 28 audit outcomes of the v0.4.0 cross-language sweep, by project. |
| `scripts/matrix/` | The protocol, the answer key, the four fixtures, the scorer (`score.py`) and the run script. |
| `scripts/dogfood/run.sh` | Runs the loop on a fresh copy of a real repository. |
| `scripts/verify_evidence.py` | Recomputes `evidence.json` from the original session logs. |
| `SOURCE-2026-10-02.json` | The workbench revision this snapshot was taken from, and a SHA-256 for every file. |

Both run scripts read their working directory from the `AUDIT_ROOT` environment variable.

## What can be checked

- The four fixtures are small Python projects that run with the standard library. Their baseline tests (three pass, one fails by design) run with `python -m unittest discover -s tests -q` inside each fixture.
- The slicing regression in the article can be replayed against fixture D.
- `scripts/matrix/score.py` re-scores any collected session logs against the rubric.

## What cannot be checked

- **The raw session logs are not published.** They are large, contain full transcripts and local paths, and are regenerated on every run. `evidence.json` holds the counts exported from them, and `verify_evidence.py` recomputes those counts when pointed at the original logs, which only the author has.
- **The v0.4.0 sweep counts are author-reported.** The package's [dated note](https://github.com/plicara/pi-audit-loop/blob/v0.4.0/.plicara/notes/2026-09-28-cross-language-dogfood.md) records each scenario and the independent test run that followed it. The split by project in `sweep-outcomes.json` is read from that note's prose and reconciles with its totals, but it was not recomputed from logs, and the order of audits inside a project is not recorded.
- No cost, latency or productivity comparison was collected.

## How it was sanitised

The snapshot was built from an explicit allowlist and then scanned for absolute user paths, usernames, home-directory references, temporary paths, email addresses, session ids, key-like strings, IP addresses and host names. The build failed on any match. Transcripts, the file names of the original logs, private notes and verification notes are not exported. Machine paths in recorded tool output were replaced with `<workbench>/`.
