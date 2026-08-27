"""Are the tasks the filter blocked unrepresentative? Ported and hardened.

Re-run of regexeval-2026's runner/filter_bias_check.py against its committed
predictions, with uncertainty added: a two-sided sign-flip permutation test
over the ten per-model difficulty differences, leave-one-model-out
jackknife, and exact counts so every number can be re-derived.

claude-opus-5 lost 84 of 622 StructuredRegex instances to content-filter
blankings that five retry rounds could not clear. If those instances are
systematically harder or easier than the rest for the other ten models,
naive failure-dropping flatters opus while counting failures punishes it.

The blocked set is selected on the filter's own signature, an upstream
finish_reason of content_filter, and not on "row we could not score". The
looser test also sweeps in 25 rows that came back status=ok holding an
empty code fence, which the filter never touched; mixing the two
populations is the exact error this article asks other harnesses not to
make.

    python3 blocked_subset_bias.py \
        --predictions ../../../regexeval-2026/predictions/structuredregex \
        --out ../../results/1_refused_at_random/blocked_subset_bias.json

No API calls: everything comes from files already committed in the study.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import signal
import sys
from pathlib import Path


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


# See the note in score_treatments.py: Python 3.14 accepts `\z`, every
# earlier version rejects it, and the study's scorer ran on the earlier
# reading. No pattern in the blocked subset uses it today, so this changes
# nothing here; it is present so that the two scorers cannot disagree, and
# so that a future interpreter cannot move this number either.
_PCRE_END_ANCHOR = re.compile(r"(?<!\\)\\(?:\\\\)*z")


def full_match(pattern, text):
    if _PCRE_END_ANCHOR.search(pattern):
        return None
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, 2)
    try:
        return re.fullmatch(pattern, text) is not None
    except (_Timeout, re.error, RecursionError, OverflowError):
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def passes(pattern, pos, neg):
    return (all(full_match(pattern, s) is True for s in pos)
            and all(full_match(pattern, s) is False for s in neg))


def filter_blanked(row):
    """True iff the safety filter deleted this answer.

    The upstream stop reason is the discriminator. Empty content alone is
    not enough: in the sweep corpus, transport failures (HTTP 403) and
    routing failures also arrive with no content and must not be counted
    as censorship.
    """
    return "finish_reason='content_filter'" in (row.get("error") or "")


def load(label, pred_dir):
    rows = [json.loads(l) for l in (pred_dir / f"{label}.jsonl").read_text().splitlines() if l.strip()]
    return [r for r in rows if not r["task_name"].startswith("control/")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--perms", type=int, default=100_000)
    args = ap.parse_args()

    opus_rows = load("claude-opus-5", args.predictions)
    # The filter's signature is the upstream stop reason, not "unscorable":
    # a blanked row carries finish_reason='content_filter' and no content.
    blocked = {r["task_name"] for r in opus_rows if filter_blanked(r)}
    # Rows we could not score for any other reason are counted and reported
    # separately, never folded into the blocked set.
    other_unscored = {r["task_name"] for r in opus_rows
                      if not filter_blanked(r)
                      and (r.get("status") != "ok" or not r.get("pattern"))}
    kept = {r["task_name"] for r in opus_rows} - blocked - other_unscored
    print(f"opus blanked by the filter on {len(blocked)} instances, "
          f"unscored for other reasons on {len(other_unscored)}, "
          f"answered {len(kept)}")

    labels = sorted(p.stem for p in args.predictions.glob("*.jsonl")
                    if p.stem != "claude-opus-5")

    diffs, detail = [], []
    rng = random.Random(20260826)  # fixed seed: the permutation test replays
    for label in labels:
        b = k = bn = kn = 0
        for r in load(label, args.predictions):
            if r.get("status") != "ok" or not r.get("pattern"):
                continue
            good = passes(r["pattern"], r["pos"], r["neg"])
            if r["task_name"] in blocked:
                bn += 1
                b += good
            else:
                kn += 1
                k += good
        pb, pk = 100 * b / bn, 100 * k / kn
        diffs.append(pb - pk)
        detail.append({"model": label, "n_blocked": bn, "n_kept": kn,
                       "pass_on_blocked": round(pb, 2),
                       "pass_on_kept": round(pk, 2),
                       "diff": round(pb - pk, 2)})
        print(f"{label:32s} {pb:15.1f}% {pk:13.1f}% {pb - pk:+7.1f}")

    n = len(diffs)
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    sd = var ** 0.5

    # Sign-flip permutation: H0 = blocked and kept sets are equally hard,
    # i.e. each model's diff is symmetric about zero.
    extreme = sum(1 for signs in itertools.product((1, -1), repeat=n)
                  if abs(sum(s * d for s, d in zip(signs, diffs))) >= abs(sum(diffs)) - 1e-9)
    if 2 ** n <= args.perms:
        p_exact = extreme / 2 ** n
        p_value, method = p_exact, f"exact sign-flip (2^{n}={2 ** n})"
    else:
        hits = sum(1 for _ in range(args.perms)
                   if abs(sum(rng.choice((1, -1)) * d for d in diffs)) >= abs(sum(diffs)) - 1e-9)
        p_value, method = (hits + 1) / (args.perms + 1), f"sampled sign-flip ({args.perms})"

    # Jackknife over models: how much does the mean depend on any one?
    jk = []
    for i in range(n):
        rest = diffs[:i] + diffs[i + 1:]
        jk.append(sum(rest) / len(rest))
    jk_se = (((n - 1) / n * sum((m - sum(jk) / n) ** 2 for m in jk)) ** 0.5) if n > 1 else None

    out = {
        "generated": "2026-08-26",
        "source": "regexeval-2026 predictions/structuredregex (committed)",
        "opus_blocked_tasks": len(blocked),
        "opus_other_unscored": len(other_unscored),
        "opus_answered_tasks": len(kept),
        "blocked_selector": "upstream finish_reason='content_filter'",
        "mean_diff_points": round(mean, 2),
        "sd_points": round(sd, 2),
        "p_value": round(p_value, 6),
        "test": method,
        "jackknife_se_points": round(jk_se, 2) if jk_se is not None else None,
        "per_model": detail,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nmean {mean:+.1f} pts (sd {sd:.1f}), {method}: p={p_value:.4g}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
