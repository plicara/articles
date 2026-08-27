# filter-censorship

Analysis code behind Plicara's articles on provider-side content filtering:
how a filter sitting between a harness and a model corrupts a benchmark
result, and what k-sample evaluation reveals about it.

The evidence base is the
[regexeval-2026](https://github.com/plicara/regexeval-2026) prediction data,
which recorded `finish_reason='content_filter'` blankings that hit
`claude-opus-5` exclusively, stochastically, on benign prompts.

Published so the numbers in those articles can be rerun and checked rather
than taken on trust.

## Article 01: a safety filter moved our benchmark by seven places

[Read it](https://plicara.ai/research/refused-at-random/) ·
`scripts/1_refused_at_random/`

| Script | Question |
|---|---|
| `blocked_subset_bias.py` | Are the tasks the filter blocked unrepresentative of the rest? |
| `score_treatments.py` | What did the blanked calls do to the benchmark result, and would k samples have caught them? |
| `collect.py` | Does the filter still fire today, and on which hosting platforms? |
| `summarize_freshness.py` | Reduces the freshness arms to a committed export |
| `export_figures.py` | Computes every published number into `results/1_refused_at_random/figures.json` |
| `build_article.py` | Renders the article and its charts from that file |

The `manifest_*.json` files are the collection manifests: the exact prompts,
models and repeat counts each `collect.py` arm ran, committed so a fresh
probe reruns the same requests rather than a paraphrase of them.

## Running it

Everything here is Python 3 standard library, so there is nothing to
install. The two analyses that produce published numbers are pure local
computation over the study's committed predictions, with no API calls:

```sh
cd scripts/1_refused_at_random
REGEXEVAL=<path to a clone of plicara/regexeval-2026>

python3 blocked_subset_bias.py \
    --predictions $REGEXEVAL/predictions/structuredregex \
    --out ../../results/1_refused_at_random/blocked_subset_bias.json

python3 score_treatments.py \
    --predictions $REGEXEVAL/predictions/structuredregex \
    --bias ../../results/1_refused_at_random/blocked_subset_bias.json \
    --out ../../results/1_refused_at_random/score_treatments.json

REGEXEVAL_REPO=$REGEXEVAL python3 export_figures.py
```

`export_figures.py` consolidates every number the article cites into one
file, and the article is rendered only from that file, so nothing in the
prose is typed by hand.

Fresh probes cost money and are the one thing here that reaches a provider:

```sh
python3 collect.py --manifest manifest_upstream.json --dry-run    # plan, no spend
python3 collect.py --manifest manifest_upstream.json --max-spend 8.00
```

It reads `OPENROUTER_KEY` from a `.env` file in the project root, which is
gitignored and not published. Raw response envelopes land in `data/`, which
is also gitignored: the committed summaries under `results/` are what the
article cites.

## One trap, before you compare numbers

Both scorers pin one piece of regex dialect on purpose, and it is worth
knowing why before you compare a rerun against the published numbers.

Python 3.14 added `\z` as an alias for `\Z`. Every earlier version rejects it
as a bad escape, and the parent study's own StructuredRegex scorer ran on
that earlier reading: `runner/dialect.py` there lists `\z` -> `\Z` among the
rewrites it knows how to make, and the scorer deliberately does not apply
them, so a pattern using `\z` failed to compile and was scored wrong.

Three of the 6,842 predictions across the eleven models use `\z`, two of them
claude-opus-5's. Left to the interpreter, those two compile on 3.14 and not
on earlier versions, which moves claude-opus-5's score by 0.4 points and
every treatment with it. A number in a published article should not change because the
machine running it was upgraded, so `full_match` rejects `\z` itself rather
than asking the interpreter.

Verified: `blocked_subset_bias.json` and `score_treatments.json` are
byte-identical on Python 3.9.6 and 3.14.7, and both match what the article
cites. If your rerun disagrees with the published numbers, it is a real
finding and worth an issue.

## What is not here

Two things a reader chasing a number will notice, said plainly rather than
found the hard way.

- **`build_article.py` cannot run in this repo.** It reads
  `article.md.tmpl`, and the prose lives in the site repo rather than here.
  It is published because it is the thing that turned the numbers into the
  charts, not as a working entry point.
- **`blocked_resend_summary.json` and `upstream_discriminator.json` have no
  generator here.** `export_figures.py` reads both, but neither has a
  committed script that writes it; they were derived from raw collection
  envelopes under `data/`, which never ships. The figures resting on them
  are the resend-recovery counts and the per-platform blank counts. Every
  other export in `results/` can be regenerated from the commands above.

## Source of record

The study repo owns the numbers this project analyses. Nothing here
rewrites or re-scores it; the article cites it. Two figures cannot be
derived from the committed predictions, which record only the post-retry
state: the 182 instances blocked on the first pass and the 98 that retrying
recovered are carried from the parent study, and `export_figures.py`
asserts they still reconcile with what the corpus can prove, 182 minus 98
leaving the 84 blanks the predictions contain, failing the build if they
ever disagree.

Found something wrong? Open an issue. The analysis is public precisely so it
can be checked.
