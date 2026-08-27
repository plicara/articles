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

`score_treatments.py` scores a candidate regex by running it against the
instance's examples under a two second wall-clock timeout, and a pattern
that times out is scored as not passing. Thirty-six of the 513 scorable
instances are slow enough to be near that boundary, so a faster or idler
machine resolves a couple of them that the published run did not, and the
three scores move by about 0.4 points.

The published run scored 316 of 513; a 2026-era laptop scores 318. What that
moves is only the absolute scores. The ranks (3rd, 10th and 4th of 11), the
seven-place spread the article is named for, and the 8.7 point gap between
the best and worst handling are all differences between treatments over the
same instances, so they are unaffected and reproduce exactly. So does
`blocked_subset_bias.json`, which has no timeout in it.

If your rerun prints 62.0 rather than 61.6, this is why, and it is not a
discrepancy worth an issue.

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
