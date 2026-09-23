# Jev System One

Research article: TypeSafe's Jev (System One decision model) evaluated on the
frozen AdventureBench set through a separate audited runtime.

## Run the analysis

```bash
python3 scripts/jev_decisions/export_figures.py  # results/jev_decisions/figures.json
python3 scripts/jev_decisions/build_article.py   # 01-jev-decisions/{article.md,article.site.md,preview.html}
python3 ../shared/check_style.py 01-jev-decisions/article.md
```

All numbers come from audited public benchmark artifacts: the frozen chat release and the separate Jev v2 release. The figure exporter derives every displayed number before the article builder substitutes it into prose and SVG.

## Ship

Article ships from `01-jev-decisions/article.site.md` (markers already
replaced by inline SVG) per the workbench README. Draft only until reviewed.

## Article 02: jev, three use cases

`02-model-that-only-chooses/` is "jev: three use cases, a ton of learnings": Jev against a fruit fly connectome in Doom, as a verifier over 370 ExtractBench documents, and as the chooser in five text adventures. The experiments themselves live in the jev-tests repository, not here; this folder holds the published prose and the ten figures, which were rendered from those runs. The Doom run data was not kept, which the article footnotes.

```bash
python3 scripts/model_that_only_chooses/build_site.py 2026-09-23   # 02-model-that-only-chooses/article.site.md
```

