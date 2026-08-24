# gitskills-analysis

Analysis code behind Plicara's articles on the
[GitSkills](https://arxiv.org/abs/2608.10906) dataset — 3,797,117 `SKILL.md`
agent-skill files collected from 282,200 public GitHub repositories in
July 2026.

Published so the numbers in those articles can be checked and rerun, not
taken on trust.

## What's here

**Article 01 — what language are agent skills written in?**
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
| `export_figures.py` | Emits every published number to `results/figures.json` |
| `build_article.py` | Renders the article from that JSON |

Also here: `lang_refs.py` (which programming languages skills mention, and
which they actually ship code in) and `word_freq.py` (vocabulary of skill
bodies). Code for later articles lands as those articles are published.

## Running it

```sh
uv sync
uv run scripts/fetch_sample.py        # ~83 MB sample into data/
uv run scripts/1_natural_language/natural_lang.py
```

Every script resolves its input from `GITSKILLS_DB`, defaulting to the
local sample. Against the full 44 GB release:

```sh
GITSKILLS_DB=/path/to/agent_skills_release.db uv run scripts/<script>.py
```

Figures are regenerated end to end with two commands, so no number in an
article is transcribed by hand:

```sh
uv run scripts/1_natural_language/export_figures.py
uv run scripts/1_natural_language/build_article.py
```

## Reading the code

The docstrings carry the reasoning, including the measurement traps we fell
into. Three worth knowing before trusting any similar analysis of this
dataset:

- **DuckDB's `regexp_replace` only replaces the first match** without the
  `g` flag. Our cleaning passes silently left ~85% of fenced code in text we
  were treating as prose.
- **`sibling_count` counts bundled files, not copies.** Verbatim copies are
  counted by grouping on `file_sha`; the two are uncorrelated.
- **Mentioning a language is not writing in one.** Shell/Bash appears in
  37.5% of skills but only 2.6% ship a shell script — most matches are
  pasted commands.

Results are reported with 95% Wilson intervals, and differences are only
claimed when intervals don't overlap.

## Credit

The dataset is not ours. All credit for collecting, deduplicating and
documenting 3.8 million skill files belongs to its authors:

> Giuseppe Destefanis, Daniel Graziotin, Matteo Vaccargiu, and Marco Ortu.
> 2027. GitSkills: A Dataset of Agent Skills on GitHub. In *Proceedings of
> the 24th International Conference on Mining Software Repositories
> (MSR '27)*.

Preprint [arXiv:2608.10906](https://arxiv.org/abs/2608.10906) ·
archive [10.5281/zenodo.21875637](https://doi.org/10.5281/zenodo.21875637) ·
mirror [`mvaccargiu/gitskills`](https://huggingface.co/datasets/mvaccargiu/gitskills) ·
licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

GitSkills is the dataset for the MSR '27 Mining Challenge. We are not
affiliated with its authors, with MSR, or with the challenge. The dataset is
theirs; the analysis, and any error in it, is ours.

Found something wrong? Open an issue — corrections are welcome.
