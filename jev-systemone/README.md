# Jev on AdventureBench

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
