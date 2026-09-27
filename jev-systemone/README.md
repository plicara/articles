# Jev System One

Two published research articles on TypeSafe's Jev, the System One decision model.

## Article 01: A model that answers in probabilities

`01-jev-decisions` evaluates Jev on the frozen AdventureBench set through a separate audited runtime. Its numbers come from the audited public chat and Jev v2 releases. The provenance footnote distinguishes the public alias and explicitly pinned requests and records the unresolved private-to-public lineage of the confirmation run.

```sh
python3 scripts/jev_decisions/export_figures.py
python3 scripts/jev_decisions/build_article.py
```

The exporter expects a sibling `benchmarks` checkout containing the public releases. The article builder reads `results/jev_decisions/figures.json` and writes the review Markdown, site Markdown and local HTML preview.

## Article 02: jev, three use cases

`02-model-that-only-chooses` covers Doom, ExtractBench verification, text adventures and a local reimplementation. The [26 September evidence package](02-model-that-only-chooses/evidence/2026-09-26/README.md) replays the adventure comparisons and captured round-five scores from exported observations. This is an offline reanalysis, not a new model run. The [27 September recovered-data package](02-model-that-only-chooses/evidence/2026-09-27/README.md) adds extraction relabeling, explicit peer comparisons, probability diagnostics and a later paired Doom experiment. It replaces unreproduced extraction headline rates and regenerates Figures 4 and 6. The original fly head-to-head and other exploratory claims remain explicitly outside replay coverage.

```sh
python3 02-model-that-only-chooses/evidence/2026-09-26/replay.py --check
python3 02-model-that-only-chooses/evidence/2026-09-27/replay.py --check
python3 scripts/model_that_only_chooses/build_site.py 2026-09-23
```

## Publication

Both articles ship from their generated `article.site.md` files. Edit `01-jev-decisions/article.md.tmpl` or `02-model-that-only-chooses/article.md`, then run the relevant builder. The latter replaces figure markers with inline figures and retains the original publication date. The explicit publication allowlist records the reviewed files and source revision; private notes and raw game transcripts are not exported.
