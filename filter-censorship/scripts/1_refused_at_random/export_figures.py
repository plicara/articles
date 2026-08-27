"""Consolidate every number the article cites into one machine-readable export.

Reads the study's committed predictions (source of record) and this
project's fresh collection summaries, writes results/figures.json. The
article builder consumes only this file; nothing in the prose is typed by
hand.

    python3 export_figures.py
"""
from __future__ import annotations

import collections
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scripts/1_refused_at_random
PROJ = HERE.parents[1]                          # filter-censorship/
STUDY = Path(os.environ.get("REGEXEVAL_REPO",
                            PROJ.parent.parent / "regexeval-2026"))
FRESH = PROJ / "results" / "1_refused_at_random"

FIG: dict = {}


def filter_blanked(row) -> bool:
    """True iff the safety filter deleted this answer.

    The upstream stop reason is the discriminator, not "row we could not
    score". Empty content alone is not enough: transport failures (HTTP
    403) and routing failures arrive with no content too, and counting
    those as censorship is the error this article asks harnesses not to
    make.
    """
    return "finish_reason='content_filter'" in (row.get("error") or "")


# ---------------------------------------------------------------- historical
# Sweep corpus: eleven models x 451 tasks x 3 samples.
sweep = [json.loads(l) for l in
         (STUDY / "predictions/sweep/claude-opus-5.jsonl").read_text().splitlines()]
opus_blank = [r for r in sweep if filter_blanked(r)]
touched = {r["task_name"] for r in opus_blank}
hist_calls = sum(1 for r in sweep if r["task_name"] in touched)

# Every non-ok row in every sweep file, split by kind. The article cites
# this to show that "no other model lost anything" is true of the filter
# and false of failures in general.
sweep_fail_by_kind: collections.Counter = collections.Counter()
sweep_fail_by_model: collections.Counter = collections.Counter()
for path in sorted((STUDY / "predictions/sweep").glob("*.jsonl")):
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r.get("status") == "ok":
            continue
        sweep_fail_by_model[path.stem] += 1
        sweep_fail_by_kind["content filter" if filter_blanked(r)
                           else r.get("status", "unknown")] += 1

FIG["hist_sweep_calls"] = len(sweep)
FIG["hist_sweep_fail_total"] = sum(sweep_fail_by_kind.values())
FIG["hist_sweep_fail_by_kind"] = dict(sweep_fail_by_kind.most_common())
FIG["hist_sweep_fail_by_model"] = dict(sweep_fail_by_model.most_common())
FIG["hist_sweep_fail_other"] = (FIG["hist_sweep_fail_total"]
                                - sweep_fail_by_kind["content filter"])
FIG["hist_sweep_models_blanked"] = sum(
    1 for m in sweep_fail_by_model
    if any(filter_blanked(json.loads(l)) for l in
           (STUDY / f"predictions/sweep/{m}.jsonl").read_text().splitlines()))
FIG["hist_sweep_refusals"] = len(opus_blank)
FIG["hist_touched_tasks"] = len(touched)
FIG["hist_refused_on_touched"] = FIG["hist_sweep_refusals"]
FIG["hist_calls_on_touched"] = hist_calls
FIG["hist_rate_on_touched"] = round(100 * FIG["hist_sweep_refusals"] / hist_calls, 1)
partial = [t for t in touched
           if sum(1 for r in sweep if r["task_name"] == t and filter_blanked(r))
           < sum(1 for r in sweep if r["task_name"] == t)]
FIG["hist_sweep_partial"] = len(partial)
# Samples per task in the main sweep. This is the k that actually caught the
# filter, and is not the same number as the resend arms' k.
FIG["hist_samples_per_task"] = FIG["hist_calls_on_touched"] // FIG["hist_touched_tasks"]
FIG["hist_sweep_silenced"] = len(touched) - len(partial)

# StructuredRegex. The corpus is 332 descriptions expanded into 622
# scored instances (most descriptions carry two sampled attempts), so
# "description" and "instance" are different denominators and the article
# is careful to say which it means.
sr = [json.loads(l) for l in
      (STUDY / "predictions/structuredregex/claude-opus-5.jsonl").read_text().splitlines()]
real = [r for r in sr if not r["task_name"].startswith("control/")]
by_id = collections.defaultdict(lambda: [0, 0])
for r in real:
    pid = r["task_name"].split("#")[0]
    by_id[pid][0] += 1
    if filter_blanked(r):
        by_id[pid][1] += 1
touched_ids = {i for i, v in by_id.items() if v[1]}

FIG["sr_instances"] = len(real)
FIG["sr_descriptions"] = len(by_id)
FIG["sr_controls"] = len(sr) - len(real)

# Post-retry residue, split by kind rather than lumped into one count.
FIG["sr_filter_blanks"] = sum(1 for r in real if filter_blanked(r))
FIG["sr_other_unscored"] = sum(1 for r in real if not filter_blanked(r)
                               and (r.get("status") != "ok" or not r.get("pattern")))
FIG["sr_unscored_total"] = FIG["sr_filter_blanks"] + FIG["sr_other_unscored"]
FIG["sr_scored"] = len(real) - FIG["sr_unscored_total"]

# Pre-retry counts are not recoverable from the committed predictions,
# which record only the post-retry state. They are carried from the parent
# study (regexeval-2026 ARTICLE.md, written by runner/retry_failed.py) and
# asserted against what this corpus can still prove, so the two accountings
# cannot silently drift apart again.
FIG["sr_initial_refusals"] = 182
FIG["sr_recovered_by_retry"] = 98
FIG["sr_initial_source"] = "regexeval-2026 ARTICLE.md (pre-retry, not in predictions)"
assert FIG["sr_initial_refusals"] - FIG["sr_recovered_by_retry"] == FIG["sr_filter_blanks"], (
    f'pre-retry accounting broke: {FIG["sr_initial_refusals"]} blocked minus '
    f'{FIG["sr_recovered_by_retry"]} recovered should leave '
    f'{FIG["sr_filter_blanks"]} blanks in the committed predictions')
FIG["sr_initial_pct"] = round(100 * FIG["sr_initial_refusals"] / FIG["sr_instances"], 1)

# Descriptions the filter touched, and how completely.
FIG["sr_touched_desc"] = len(touched_ids)
FIG["sr_full_silence"] = sum(1 for i in touched_ids if by_id[i][1] == by_id[i][0])
FIG["sr_partial_desc"] = len(touched_ids) - FIG["sr_full_silence"]
# A one-sample description is "silenced every time" on a single attempt,
# which is not the same evidence as a description blanked on every one of
# several tries. Report the stronger subset separately.
FIG["sr_full_silence_multisample"] = sum(
    1 for i in touched_ids if by_id[i][1] == by_id[i][0] and by_id[i][0] > 1)

# Sonnet on the same corpus, counted on the same denominator as opus:
# real instances only, excluding the synthetic control rows.
sonnet = [json.loads(l) for l in
          (STUDY / "predictions/structuredregex/claude-sonnet-5.jsonl").read_text().splitlines()]
sonnet_real = [r for r in sonnet if not r["task_name"].startswith("control/")]
FIG["sonnet_sr_instances"] = len(sonnet_real)
FIG["sonnet_sr_clean"] = sum(1 for r in sonnet_real
                             if r.get("status") == "ok" and r.get("pattern"))
FIG["sonnet_sr_blanks"] = sum(1 for r in sonnet_real if filter_blanked(r))

# What the blanked calls did to the leaderboard.
tre = json.loads((FRESH / "score_treatments.json").read_text())
FIG["score_drop"] = tre["scores"]["drop"]
FIG["score_countwrong"] = tre["scores"]["count_wrong"]
FIG["score_corrected"] = tre["scores"]["corrected"]
FIG["score_spread"] = tre["spread_points"]
FIG["rank_drop"] = tre["ranks"]["drop"]
FIG["rank_countwrong"] = tre["ranks"]["count_wrong"]
FIG["rank_corrected"] = tre["ranks"]["corrected"]
FIG["rank_spread"] = tre["rank_spread"]
FIG["field_size"] = tre["field_size"]
FIG["score_denominator"] = tre["denominator"]
FIG["board"] = tre["board"]
FIG["detection"] = tre["detection"]
FIG["detect_k1_study"] = tre["detection"]["study"][0]
FIG["detect_k3_study"] = tre["detection"]["study"][2]
FIG["detect_k1_today"] = tre["detection"]["today"][0]
FIG["detect_k3_today"] = tre["detection"]["today"][2]
FIG["detect_k10_today"] = tre["detection"]["today"][9]
FIG["detect_k10_k"] = tre["detection"]["k"][9]

# Bias port result.
bias = json.loads((FRESH / "blocked_subset_bias.json").read_text())
FIG["bias_mean"] = bias["mean_diff_points"]
FIG["bias_sd"] = bias["sd_points"]
FIG["bias_p"] = bias["p_value"]
FIG["bias_models"] = bias["per_model"]
FIG["bias_jk_se"] = bias["jackknife_se_points"]
# Unsigned, for the sentences where the word "harder" already carries the sign.
FIG["bias_mean_abs"] = abs(FIG["bias_mean"])
FIG["bias_blocked_n"] = bias["opus_blocked_tasks"]
FIG["bias_kept_n"] = bias["opus_answered_tasks"]

# ------------------------------------------------------------------- fresh
fresh = json.loads((FRESH / "freshness_summary.json").read_text())
o = fresh["arms"]["freshness_opus"]
s = fresh["arms"]["freshness_sonnet"]
FIG["f1_opus_calls"] = o["calls"]
FIG["f1_opus_blanks"] = o["blankings"]
FIG["f1_opus_rate"] = round(100 * o["blankings"] / o["calls"], 1)
FIG["f1_sonnet_calls"] = s["calls"]
FIG["f1_sonnet_blanks"] = s["blankings"]
FIG["f1_opus_touched"] = o["prompts_touched"]
FIG["f1_prompts"] = o["prompts_total"]
FIG["f1_opus_per_prompt"] = o["calls"] // o["prompts_total"]
# Nearly every fresh call ended at the token ceiling rather than at a stop
# token. That does not affect blank detection (a blank carries
# content_filter and no text at all) but it does mean the resend arm is
# not byte-identical in request shape to the original sweep, so the
# article says so instead of claiming the shapes matched.
_strip = lambda d: {k.strip("'"): v for k, v in d.items()}
FIG["f1_opus_finish"] = _strip(o["finish_reasons"])
FIG["f1_sonnet_finish"] = _strip(s["finish_reasons"])
FIG["f1_opus_truncated"] = _strip(o["finish_reasons"]).get("length", 0)
up = json.loads((FRESH / "upstream_discriminator.json").read_text())["arms"]
platform_order = ["upstream_anthropic", "upstream_claude_platform_on_aws",
                  "upstream_azure", "upstream_google", "upstream_amazon_bedrock"]
FIG["platforms"] = [{"name": name.replace("upstream_", ""),
                     "label": {"anthropic": "Anthropic",
                               "claude_platform_on_aws": "Claude Platform on AWS",
                               "azure": "Azure", "google": "Google Vertex",
                               "amazon_bedrock": "Amazon Bedrock"}[name.replace("upstream_", "")],
                     "calls": up[name]["calls"],
                     "blanks": up[name]["blankings"],
                     "native": up[name]["native_finish_reason_on_blanks"]}
                    for name in platform_order]
FIG["upstream_blanks_total"] = sum(a["blanks"] for a in FIG["platforms"])
FIG["upstream_calls"] = sum(a["calls"] for a in FIG["platforms"])
FIG["upstream_platforms"] = len(FIG["platforms"])
FIG["upstream_platforms_with_blanks"] = sum(1 for a in FIG["platforms"] if a["blanks"])
FIG["upstream_calls_per_platform"] = FIG["platforms"][0]["calls"]
FIG["upstream_clean_arms"] = [a["label"] for a in FIG["platforms"] if not a["blanks"]]
# Power for the arm that came back clean: at the rate the other arms show,
# how often would this many calls return zero blanks by luck alone?
_others = [a for a in FIG["platforms"] if a["blanks"]]
_rate = (sum(a["blanks"] for a in _others) / sum(a["calls"] for a in _others)) if _others else 0.0
FIG["upstream_other_rate_pct"] = round(100 * _rate, 1)
FIG["upstream_clean_expected"] = round(FIG["upstream_calls_per_platform"] * _rate, 1)
FIG["upstream_clean_p_zero_pct"] = round(
    100 * (1 - _rate) ** FIG["upstream_calls_per_platform"])

br = json.loads((FRESH / "blocked_resend_summary.json").read_text())
bo, bs = br["opus"], br["sonnet"]
FIG["br_opus_calls"] = bo["calls"]
FIG["br_opus_blanks"] = bo["blankings"]
FIG["br_opus_rate"] = round(100 * bo["blankings"] / bo["calls"], 1)
FIG["br_touched"] = bo["descriptions_touched"]
FIG["br_full_silenced"] = len(bo["fully_silenced"])
FIG["br_fully_silenced_id"] = ", ".join(bo["fully_silenced"])
FIG["br_per_description"] = bo["per_description"]
FIG["br_sonnet_ok"] = bs["successful_calls"]
FIG["br_sonnet_blanks"] = bs["blankings"]
# The sonnet control arm did not complete: the account budget ran out
# mid-arm and the rest returned HTTP 403. Those are transport failures,
# not answers and not blanks, and they get their own row rather than
# vanishing from the denominator.
FIG["br_sonnet_attempted"] = bs["attempted"]
FIG["br_sonnet_transport_fail"] = bs["attempted"] - bs["successful_calls"]
FIG["br_sonnet_note"] = bs["note"]
FIG["br_opus_per_description"] = bo["calls"] // bo["descriptions_total"]
FIG["br_descriptions_total"] = bo["descriptions_total"]
FIG["br_hist_initial_pct"] = FIG["sr_initial_pct"]

# How far the dial moved, per corpus, so the article never has to round a
# collapse to a single made-up factor.
FIG["collapse_factor_sweep"] = round(FIG["hist_rate_on_touched"] / FIG["f1_opus_rate"])
FIG["collapse_factor_sr"] = round(FIG["sr_initial_pct"] / FIG["br_opus_rate"])

# Word forms for the handful of small counts the prose spells out. The
# number still comes from the data; only its spelling is house style, so a
# figure can never be spelled out by hand and drift from its digits.
_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve "
          "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
for _k in ("upstream_platforms", "upstream_platforms_with_blanks", "hist_touched_tasks",
           "hist_sweep_partial", "hist_sweep_silenced", "f1_prompts",
           "f1_opus_per_prompt", "br_opus_per_description", "br_touched"):
    _v = FIG[_k]
    FIG[_k + "_word"] = _WORDS[_v] if isinstance(_v, int) and _v < len(_WORDS) else str(_v)

out = PROJ / "results" / "1_refused_at_random" / "figures.json"
out.write_text(json.dumps(FIG, indent=1, sort_keys=True) + "\n")
print(f"wrote {out} ({len(FIG)} keys)")
