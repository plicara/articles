# Adventure evidence reanalysis — 26 September 2026

This release recomputes selected article numbers from the saved adventure campaign. It contains 57 transcript-derived runs and 13,620 recorded decisions. It makes no new Jev or proposer calls and is not an independent replication of model behavior.

## Replay

```sh
python3 replay.py --check
python3 replay.py > recomputed.json
```

Python 3.10 or newer, standard library only. `--check` recomputes the results from `observations.jsonl` and compares them with `results.json`; it does not merely check file hashes.

## What the records contain

`observations.jsonl` contains one record per original transcript: command, confidence, option count, latency and a per-run response identifier for each logged decision, plus observed scores and end markers. Identifiers preserve the historical analyzer's equivalence classes without redistributing game prose. For Adventure they count recognized rooms; for the other games they count distinct responses and must not be interpreted as spatial progress. Scores that were not captured remain null. A death marker can occur after the last fully logged decision.

The export was checked against the original research analyzer for every run's decision count, response count and captured final score. `provenance.json` records the source revision and hashes of the exporter and original analysis files; each observation record includes its original transcript hash. The full transcripts are retained in the private research repository. These hashes document provenance but do not make the private originals publicly inspectable. The public replay starts from the exported observations, not from raw provider responses or a running game.

## Claim-to-source checks

All values below were recomputed with `python3 replay.py`.

| Article claim | Recomputed result | Source in `results.json` | Status |
| --- | --- | --- | --- |
| Paired r3/r4 comparisons | Deltas +16, +3, +11, +12, +4, +2, +4 | `comparisons` | Reproduced; only Adventure measures recognized rooms |
| Adventure baseline spends 58% on `look` | 174 of 300 decisions | `look_baselines.adventure-baseline` | Reproduced |
| Dreamhold baseline uses `look` 79 times | 79 of 300 decisions in round four | `look_baselines.dreamhold-baseline_r4` | Reproduced; round clarified in article |
| Adventure round-five proposer arms | 30/430, 32/430, 59/430 | `round5.gen_self_r5`, `gen_jev_r5`, `gen_jev_plus_r5` | Reproduced |
| Adventure alone dies at turn 91 | Marker 91; 90 complete decisions | `round5.r2_look_history_r5` | Reproduced; no final score captured |
| Combined Adventure arm spends 64 turns underground | 64 of 200 decisions | `round5.gen_jev_plus_r5` | Reproduced under original room classifier |
| Lost Pig round five | 1/7 alone; 2/7 in each proposer arm | `round5.lostpig-*` | Reproduced |
| Dreamhold round five | 1/7 for `gen_self` and `gen_jev`; other scores absent | `round5.dreamhold-*` | Partial capture; absent scores are not inferred |
| Curses round five | 0/550 in all four arms; alone ends at 1, combined at 2 | `round5.curses-*` | Reproduced |
| 9:05 alone stops at decision 176 | 176 decisions | `round5.905-r2_look_history_r5` | Reproduced; no game score |
| Doom survival, kill counts and extraction detection/calibration results | Not recomputed | Original run records unavailable locally | Unverified in this update |

The adventure scores come from one run per game/arm in round five. They do not estimate variability or establish a general improvement. The seven paired comparisons measure response variety except where specifically labelled otherwise. The article's other numerical and causal claims are outside this replay's coverage.

## Remaining work

Recover the original Doom event logs and extraction verdicts, or collect a separately dated new campaign with its own pinned models, configuration, retained requests/responses and spending limit. New results must be reported alongside the historical results, not represented as recovered originals. This release does not resolve those evidence gaps.
