# articles

Code behind Plicara's published research articles. This is the public
counterpart to
[`articles-workbench`](https://github.com/plicara/articles-workbench), which
stays private: drafts are written there, and the code that produced their
numbers is published here once the piece is out.

## Layout

```
shared/       what every project needs
<project>/    one folder per project, self-contained
```

A project folder is the whole record of how its numbers were produced, so a
reader who doubts a figure can rerun it:

```
<project>/
  README.md     what the project is, what each script answers, how to run it
  scripts/      the analysis, grouped by the article it belongs to
  results/      machine-readable exports the articles are built from
  pyproject.toml, uv.lock, .python-version
```

One folder per project rather than per article: a series shares its dataset,
its cleaning rules and its helpers, and splitting those across folders would
duplicate them. Scripts are grouped by article inside `scripts/`.

## What's here

| Project | Articles |
|---|---|
| [`gitskills-analysis/`](gitskills-analysis) | The GitSkills series, on 3.8M `SKILL.md` agent-skill files from GitHub. Article 01: what natural language are agent skills written in? |

Code arrives here only once the piece that uses it is out, so a folder may
cover fewer articles than its series eventually runs to. Until then it lives
in the workbench alongside the draft, so there is one copy of the work
instead of two that drift apart.

## Running anything here

Each project is self-contained and managed with
[uv](https://docs.astral.sh/uv/):

```sh
cd <project>
uv sync
uv run scripts/<script>.py
```

Datasets are not vendored. Each project's README says where its data comes
from and how to fetch it.

## Corrections

If a number here is wrong we would rather know. Open an issue; the analysis
is public precisely so it can be checked.
