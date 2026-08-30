# gitskills-analysis

Reproducible analysis behind Plicara's articles on the [GitSkills](https://arxiv.org/abs/2608.10906) dataset: 3,797,117 `SKILL.md` agent-skill files collected from 282,200 public GitHub repositories in July 2026, grouped into 1,877,981 distinct contents.

The public repository contains finished articles and the code and exports behind their published numbers. Drafts, research notes, and data remain private in the workbench.

## Articles

### Article 01: what language are agent skills written in?

Published at [plicara.ai/research/agent-skill-languages](https://plicara.ai/research/agent-skill-languages/). `scripts/1_natural_language/` identifies the language of each skill, measures changes over time, copying, maintenance, authorship and UTC commit-hour distributions, then writes every published number to `results/figures.json`.

### Article 02: what agent skills are actually made of

Published at [plicara.ai/research/agent-skill-programming-languages](https://plicara.ai/research/agent-skill-programming-languages/). `scripts/2_programming_languages/` measures which programming languages skills mention and ship, their bundled-file composition, language trends, reuse, repository-language cross-checks, and the relationship between a skill's natural language and whether it ships code. `results/figures_02.json` holds every number printed in the article.

`02-programming-languages/` contains the generated readable article, the site copy with inline SVG figures, and the review preview. Its prose and tables live together in `scripts/2_programming_languages/content.py`; `build_article.py` regenerates all three outputs.

## Running it

```sh
uv sync
uv run scripts/fetch_sample.py
uv run scripts/test_regression.py
```

The regression suite always uses the 13,000-skill sample and pins 42 values across both articles. It stashes and restores the full-corpus exports while it runs.

The published figures use the full corpus. The Zenodo release is a 44 GB SQLite file; the Parquet mirror is approximately 13.4 GB and is generally more practical for a full run:

```sh
uv run scripts/fetch_full.py --all
uv run scripts/classify_languages.py
uv run scripts/2_programming_languages/export_figures.py
uv run scripts/2_programming_languages/build_article.py
```

Set `GITSKILLS_DB` or `GITSKILLS_PARQUET` to select a corpus explicitly. `common.source()` chooses the full Parquet corpus when present and otherwise uses the sample. `classify_languages.py` caches the natural-language result so Article 02 can reuse Article 01's measurement rather than identify the corpus twice.

## Credit

The dataset is not ours. All credit for collecting, deduplicating and documenting the corpus belongs to its authors:

> Giuseppe Destefanis, Daniel Graziotin, Matteo Vaccargiu, and Marco Ortu. 2027. [GitSkills: A Dataset of Agent Skills on GitHub](https://arxiv.org/abs/2608.10906). In *Proceedings of the 24th International Conference on Mining Software Repositories (MSR '27)*.

Preprint [arXiv:2608.10906](https://arxiv.org/abs/2608.10906) · archive [10.5281/zenodo.21875637](https://doi.org/10.5281/zenodo.21875637) · Parquet mirror [`mvaccargiu/gitskills`](https://huggingface.co/datasets/mvaccargiu/gitskills) · sample [`giuseppedestefanis/gitskills-sample`](https://github.com/giuseppedestefanis/gitskills-sample) · licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

GitSkills is the dataset for the MSR '27 Mining Challenge. We are not affiliated with its authors, with MSR, or with the challenge. The analysis, and any error in it, is ours.
