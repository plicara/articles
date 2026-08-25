# gitskills-analysis

Analysis code behind Plicara's articles on the
[GitSkills](https://arxiv.org/abs/2608.10906) dataset: 3,797,117 `SKILL.md`
agent-skill files collected from 282,200 public GitHub repositories in July
2026, grouped into 1,877,981 distinct contents.

Published so the numbers in those articles can be rerun and checked rather
than taken on trust.

## Article 01: what language are agent skills written in?

`scripts/1_natural_language/`

| Script | Question |
|---|---|
| `natural_lang.py` | What natural language is each skill written in? |
| `language_over_time.py` | Is that mix shifting as the format spreads? |
| `trend_robustness.py` | Is the shift real, or an artifact of the subsample? |
| `reuse_by_language.py` | Which skills get copied, and does language predict it? |
| `maintenance.py` | Which skills get revised, compared at equal age? |
| `commit_clock.py` | What do UTC commit hours say about where skills come from? |
| `authorship.py` | How many skills were written by an AI agent? |
| `crosscheck_langid.py` | Does a second identifier agree with ours? |
| `export_figures.py` | Computes every published number into `results/figures.json` |
| `build_article.py` | Renders the article and its charts from that file |

Also here: `lang_refs.py`, which separates the programming languages a skill
*mentions* from the ones it actually ships code in, and `word_freq.py` for
the vocabulary of skill bodies. Both belong to articles still being written.

## Running it

```sh
uv sync
uv run scripts/fetch_sample.py     # 13,000-skill sample, ~83 MB
uv run scripts/1_natural_language/natural_lang.py
```

The published figures come from the full corpus, not the sample. The Zenodo
release is a single 44 GB SQLite file; the HuggingFace mirror is the same
data as Parquet at 13.4 GB, columnar, so a query reads only the columns it
touches:

```sh
uv run scripts/fetch_full.py --all     # ~13.4 GB into data/
uv run scripts/1_natural_language/export_figures.py
uv run scripts/1_natural_language/build_article.py
```

Every script finds its tables through `common.source()`, which prefers the
Parquet corpus under `data/` and falls back to the sample. Set
`GITSKILLS_DB` to force the sample while iterating.

## Checking it

```sh
uv run scripts/test_regression.py
```

Twenty-six values pinned against the sample. It exists because five
measurement bugs reached a document during this work, and each would have
been caught in seconds by an assertion. `build_article.py` separately
refuses to write a page whose tags do not balance, whose placeholders did
not substitute, or whose chart text falls outside its own viewBox.

## Reading the code

The docstrings carry the reasoning, including the traps. Four are worth
knowing before trusting any similar analysis of this dataset:

- **DuckDB's `regexp_replace` replaces only the first match** without the
  `g` flag, which silently left most fenced code in text being treated as
  prose.
- **`sibling_count` counts bundled files, not copies.** Verbatim copies come
  from grouping on `file_sha`; the two are uncorrelated.
- **Mentioning a language is not writing in one.** Shell appears in 37.5% of
  skills but only 3.1% ship a shell script, because most matches are pasted
  commands.
- **A statistic that survives a change of corpus unchanged is probably not
  being recomputed.** Two sample-era numbers reached a draft that way.

Results carry 95% Wilson intervals, and differences are only claimed when
intervals do not overlap.

## Credit

The dataset is not ours. All credit for collecting, deduplicating and
documenting 3.8 million skill files belongs to its authors:

> Giuseppe Destefanis, Daniel Graziotin, Matteo Vaccargiu, and Marco Ortu.
> 2027. [GitSkills: A Dataset of Agent Skills on GitHub](https://arxiv.org/abs/2608.10906).
> In *Proceedings of the 24th International Conference on Mining Software
> Repositories (MSR '27)*.

Preprint [arXiv:2608.10906](https://arxiv.org/abs/2608.10906) ·
archive [10.5281/zenodo.21875637](https://doi.org/10.5281/zenodo.21875637) ·
Parquet mirror [`mvaccargiu/gitskills`](https://huggingface.co/datasets/mvaccargiu/gitskills) ·
sample [`giuseppedestefanis/gitskills-sample`](https://github.com/giuseppedestefanis/gitskills-sample) ·
licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

GitSkills is the dataset for the MSR '27 Mining Challenge. We are not
affiliated with its authors, with MSR, or with the challenge. The dataset is
theirs; the analysis, and any error in it, is ours.

Found something wrong? Open an issue. The analysis is public precisely so it
can be checked.
