"""Article 02's words and tables, in one place.

The review page and the shipped article both read this, so the thing that was
approved and the thing that publishes cannot drift. Article 01 learned that
the hard way with its numbers; this is the same rule applied to the prose.

Everything here is **Markdown**, because the site renders Markdown and the
review page can convert the small subset used (links, bold, inline code) to
HTML in a few lines. Going the other way, HTML into Markdown, is the harder
direction and buys nothing.

Every number is interpolated from results/figures_02.json. There are no typed
figures in this file, including inside the sentences, so a rerun of the
analysis moves the prose with it.

The eight figures, their order and their copy were approved on 2026-08-28 and
are fixed. Add nothing to them without asking.
"""

import json
from pathlib import Path

FIG = json.loads(
    (Path(__file__).resolve().parents[2] / "results" / "figures_02.json").read_text())

# ---------------------------------------------------------------- sources
SRC = {
    "gitskills": "https://arxiv.org/abs/2608.10906",
    "zenodo": "https://doi.org/10.5281/zenodo.21875637",
    "hf": "https://huggingface.co/datasets/mvaccargiu/gitskills",
    "ccby": "https://creativecommons.org/licenses/by/4.0/",
    "spec": "https://agentskills.io/specification",
    "anthropic": ("https://www.anthropic.com/engineering/"
                  "equipping-agents-for-the-real-world-with-agent-skills"),
    "octoverse": ("https://github.blog/news-insights/octoverse/"
                  "octoverse-a-new-developer-joins-github-every-second-"
                  "as-ai-leads-typescript-to-1/"),
    "llmprefs": "https://arxiv.org/abs/2503.17181",
    "wild": "https://arxiv.org/abs/2601.10338",
    "article01": "https://plicara.ai/research/agent-skill-languages/",
    "code": "https://github.com/plicara/articles",
}


def a(key, text):
    return f"[{text}]({SRC[key]})"


# ---------------------------------------------------------------- shorthand
_sc = FIG["ships_code"]
_ts = FIG["over_time"]["series"]["TypeScript"]
_py = FIG["over_time"]["series"]["Python"]
_reuse = {r["bucket"]: r for r in FIG["reuse"]}
_spec = {r["place"]: r for r in FIG["spec_layout"]["rows"]}
_named = round(sum(_spec[k]["pct"] for k in ("scripts/", "references/", "assets/")))
_zh = next(r for r in FIG["by_written_language"] if r["group"] == "Chinese")
_en = next(r for r in FIG["by_written_language"] if r["group"] == "English")
_kot = FIG["mention_vs_ship"][0]
_pyr = next(r for r in FIG["mention_vs_ship"] if r["lang"] == "Python")
_docs = next(k for k in FIG["composition_files"]["kinds"] if k["kind"] == "docs")
_rl = {r["lang"]: r for r in FIG["repo_language"]}
_ships_pct = round(_sc["nonroot"]["pct"])


def _one_line(s):
    return " ".join(s.split())


# ---------------------------------------------------------------- the piece
TITLE = "What agent skills are actually made of"
SLUG = "agent-skill-programming-languages"
DATE = "2026-08-30"
AUTHORS = "Plicara Research"
SUMMARY = _one_line(f"""
    {FIG['corpus']['skills'] / 1e6:.1f} million agent skills on GitHub. Only
    {_ships_pct} in 100 come with any code attached, and when they do it is
    usually Python, whatever the skill is about.""")

LEDE = _one_line(f"""
    An agent skill is a folder holding instructions for an AI coding assistant,
    written in ordinary prose. {a('anthropic', 'Anthropic introduced the format')}
    in October 2025 and it is now {a('spec', 'an open specification')} that around
    forty products read. These eight figures ask one question of the
    {a('gitskills', f"{FIG['corpus']['skills'] / 1e6:.1f} million of them")} on
    GitHub: when a skill does come with code attached, what language is that code
    in?""")

FIGURES = [
    dict(
        n=1,
        claim="Most skills are just writing",
        label="unit chart, and the composition of everything skills bundle",
        explain=_one_line(f"""
            A skill is a folder: a SKILL.md file of instructions, plus whatever its
            author puts beside it. **Coming with code means that folder holds a file
            the agent can run**, so `pdf-tools/SKILL.md` sitting next to
            `pdf-tools/scripts/extract.py` counts, and a skill that only describes
            what to do does not. It is the skill's own folder that matters, not the
            repository around it, which is usually a software project full of code
            either way. Each square here is one skill in a hundred:
            {_ships_pct} come with code, the other {100 - _ships_pct} are
            instructions and nothing else. The bar underneath breaks down the
            {FIG['composition_files']['total'] / 1e6:.1f} million files that do sit
            beside a SKILL.md, and {_docs['pct']:.0f}% of those are more writing
            rather than code. An independent study of
            {a('wild', '31,132 skills from two marketplaces')} found almost the same
            rate, 11.5% against our {_sc['nonroot']['pct']}%."""),
        table=(["", "skills", "share"], [
            ["bundle nothing at all", f"{FIG['bundles_nothing']['k']:,}",
             f"{FIG['bundles_nothing']['pct']}%"],
            ["ship code", f"{_sc['nonroot']['k']:,}", f"**{_sc['nonroot']['pct']}%**"],
            ["ship code, counting root-level skills", f"{_sc['all']['k']:,}",
             f"{_sc['all']['pct']}%"]]),
    ),
    dict(
        n=2,
        claim="A Rust project's skill is usually written in Python",
        label="dumbbell chart, the repository's own language against Python",
        explain=_one_line(f"""
            Each row is a group of repositories, sorted by the language GitHub says
            the project is mainly written in. The orange dot shows how often those
            projects' skills contain code in that same language; the blue dot shows
            how often they contain Python instead. Reading down the list the two dots
            trade places: a Shell project writes its skills in Shell
            {_rl['Shell/Bash']['ships_own']:.0f}% of the time, but a Rust project
            writes them in Rust only {_rl['Rust']['ships_own']:.0f}% of the time and
            reaches for Python {_rl['Rust']['ships_python']:.0f}%. Nothing here reads
            a word of the skill text, so it is an independent check on the same idea.
            It matches what
            {a('llmprefs', 'a study of how language models pick languages')} found
            from the other direction: asked to start high-performance projects, models
            chose Python 58% of the time and Rust not once."""),
        table=(["repository is mostly", "skills", "own language", "Python"],
               [[r["lang"], f"{r['n']:,}", f"**{r['ships_own']}%**",
                 f"{r['ships_python']}%"]
                for r in FIG["repo_language"] if r["lang"] in
                ("Shell/Bash", "Python", "JavaScript", "TypeScript", "Java",
                 "C/C++", "Rust")]),
    ),
    dict(
        n=3,
        claim="TypeScript is growing everywhere except here",
        label="share of new skills shipping TypeScript, by quarter",
        explain=_one_line(f"""
            The line is the share of newly written skills carrying at least one
            TypeScript file, quarter by quarter, and the shaded band around it is the
            margin of error. It falls the whole way, from {_ts[0]['pct']}% to
            {_ts[-1]['pct']}%. The note along the top is GitHub's own count of the
            opposite: {a('octoverse', 'Octoverse 2025')} reports TypeScript passing
            Python in August 2025 to become the most used language on the site, on
            66% growth in a year. The two count different things, contributors there
            and files here, so this is one measure falling while another rises rather
            than a contradiction. The final quarter is greyed out because collection
            stopped partway through it, so it is shown but never compared."""),
        table=(["quarter", "new skills", "mention it", "ship it"],
               [[p["q"], f"{p['n']:,}", f"{p['mention_pct']}%", f"**{p['pct']}%**"]
                for p in _ts]),
    ),
    dict(
        n=4,
        claim="The distance between talking and writing keeps growing",
        label="mention-to-ship ratio by quarter, TypeScript against Python",
        explain=_one_line(f"""
            Both halves of this count skills. Take the skills written in one quarter,
            count how many name a language anywhere in their text, then count how many
            actually hold a file in it, and divide. In the last quarter
            {_ts[-1]['mention_pct']:.0f}% of new skills mentioned TypeScript while
            {_ts[-1]['pct']}% contained a `.ts` file, and
            {_ts[-1]['mention_pct']:.0f} divided by {_ts[-1]['pct']} is the
            {_ts[-1]['ratio']} at the right-hand end. A value of 1 would mean people
            write what they talk about. TypeScript climbs from {_ts[0]['ratio']} to
            {_ts[-1]['ratio']}, so the gap widens every quarter, while Python is the
            faint line along the bottom holding near {_py[-1]['ratio']}."""),
        table=(["quarter", "TypeScript", "Python"],
               [[x["q"], f"**{x['ratio']}x**", f"{y['ratio']}x"]
                for x, y in zip(_ts, _py)]),
    ),
    dict(
        n=5,
        claim="Some languages are only ever discussed",
        label="mention-to-ship ratio per language, log scale",
        explain=_one_line(f"""
            The same ratio as the previous figure, one row per language, over the
            whole corpus rather than by quarter. **Both numbers count skills, not
            repositories**: how many skills name the language, divided by how many
            skills hold a file in it. {_kot['lang']} sits at the top, named in
            {_kot['mentions']:,} skills and present as a file in {_kot['ships']:,},
            which is {_kot['ratio']:.0f} times more talk than code. Python sits at the
            bottom at {_pyr['ratio']}x, near enough to 1 that the people who mention
            it mostly go on to write it. The scale stretches as it moves right, so
            each gridline is about three times the one before."""),
        table=(["language", "mention it", "ship it", "times more talk"],
               [[r["lang"], f"{r['mentions']:,}", f"{r['ships']:,}",
                 f"**{r['ratio']}x**"] for r in FIG["mention_vs_ship"][:6]]),
    ),
    dict(
        n=6,
        claim="Chinese-language skills carry code twice as often",
        label="share of owners shipping code, by the language the skill is written in",
        explain=_one_line(f"""
            Each row groups skills by the human language they are written in, then
            asks what share of the people publishing them ever include code. The dot
            is that share, the bar through it is the margin of error, and the dotted
            line marks the English rate so the comparison is visible rather than
            arithmetic. Chinese sits well to the right at {_zh['pct']:.0f}% against
            English at {_en['pct']:.0f}%. Every other group sits to the left of the
            line, so this is not a general non-English effect: it is specific to
            Chinese authors. The language column is the one
            {a('article01', 'the previous article in this series')} built."""),
        table=(["written in", "owners", "ever ship code", "margin of error"],
               [[r["group"], f"{r['n']:,}", f"**{r['pct']}%**",
                 f"{r['lo']} to {r['hi']}%"]
                for r in FIG["by_written_language"]]),
    ),
    dict(
        n=7,
        claim="The most-copied skills are the ones with code in them",
        label="share shipping code, by how many owners hold a copy",
        explain=_one_line(f"""
            Skills are grouped by how many separate people hold a copy of the
            identical file, from never copied on the left to six or more owners on the
            right. Orange is the share whose folder holds a runnable file, in the
            sense set out in the first figure; blue is the share holding any extra
            file at all, code or not. Both rise as you move right, from
            {_reuse['1']['ships']['pct']:.0f}% to
            {_reuse['6+']['ships']['pct']:.0f}% on code, but the jump is at the far
            end rather than a steady climb. Whether the code is what makes them worth
            copying, or popular skills simply attract more work, is not a question a
            file listing can settle."""),
        table=(["people holding a copy", "skills", "ship code", "bundle anything"],
               [[r["bucket"], f"{r['ships']['n']:,}", f"**{r['ships']['pct']}%**",
                 f"{r['bundles']['pct']}%"] for r in FIG["reuse"]]),
    ),
    dict(
        n=8,
        claim="The official folder layout is a minority habit",
        label="where bundled files sit, against the layout the specification defines",
        explain=_one_line(f"""
            The {a('spec', 'specification')} sets out three folders for a skill's
            extra files: scripts/, references/ and assets/. This bar shows where those
            {FIG['spec_layout']['total'] / 1e6:.1f} million files actually sit, and
            the highlighted stretch on the left is those three folders put together.
            They account for {_named}% of everything. The rest sits in folders people
            invented themselves, or loose beside the skill file with no folder at
            all."""),
        table=(["where the file sits", "files", "share"],
               [[r["place"], f"{r['n']:,}", f"**{r['pct']}%**"]
                for r in FIG["spec_layout"]["rows"]]),
    ),
]

# ---------------------------------------------------------------- back matter
LIMITS_HEADING = "what this does not show"
LIMITS = [
    _one_line(f"""
        Every "ships code" figure is a floor and a ceiling at once. A floor because
        the crawler truncated the folder listing for {FIG['corpus']['truncated']['pct']}%
        of skills, so some code went uncounted. A ceiling because a SKILL.md at the
        root of a repository has the whole project sitting beside it, and those
        skills, {FIG['corpus']['skills'] - FIG['corpus']['skills_nonroot']:,} of them,
        report code at {[d for d in _sc['depth'] if d['depth'] == 0][0]['pct']:.0f}%
        when the corpus as a whole reports {_sc['nonroot']['pct']}%. They are excluded
        from every figure here, which is why the headline is
        {_sc['nonroot']['pct']}% rather than {_sc['all']['pct']}%."""),
    _one_line(f"""
        The two figures that move through time rest on the minority of skills
        carrying commit history, and on the first commit that touched that copy
        rather than the first appearance of the content anywhere. A crawl also sees
        only survivors, so a skill created and deleted before July 2026 is invisible
        here."""),
    _one_line("""
        Naming a language and shipping a file in it are both crude. The mention
        patterns are deliberately loose, so the mention counts are ceilings, and a
        file extension says what a file is rather than whether it runs or matters."""),
]

CREDIT = [
    _one_line(f"""
        None of this exists without the dataset, which was built and released by
        someone else, and all credit for collecting, deduplicating and documenting
        {FIG['corpus']['artifact_rows'] / 1e6:.1f} million skill files belongs to its
        authors:"""),
    _one_line(f"""
        > Giuseppe Destefanis, Daniel Graziotin, Matteo Vaccargiu, and Marco Ortu.
        2027. {a('gitskills', 'GitSkills: A Dataset of Agent Skills on GitHub')}. In
        *Proceedings of the 24th International Conference on Mining Software
        Repositories (MSR '27)*."""),
    _one_line(f"""
        Preprint {a('gitskills', 'arXiv:2608.10906')}, archive
        {a('zenodo', '10.5281/zenodo.21875637')}, Parquet mirror
        {a('hf', '`mvaccargiu/gitskills`')}, licence {a('ccby', 'CC BY 4.0')}. We are
        not affiliated with its authors, with MSR, or with the Mining Challenge, so
        nothing here should be read as endorsed by them: the dataset is theirs, and
        the analysis and any error in it is ours. This article answers one question
        the authors pose and leave open, how often skills bundle executable files and
        how widely those skills are copied."""),
    _one_line(f"""
        Analysis code lives at {a('code', 'github.com/plicara/articles')} under
        `gitskills-analysis/`, where every figure and every number in the sentences
        above is generated from a single machine-readable export and never typed by
        hand, so the whole thing can be regenerated and checked."""),
    "Found something wrong? We would genuinely like to know.",
]

SOURCES = [
    ("octoverse", "GitHub Octoverse 2025",
     _one_line("""TypeScript reaching number one on GitHub by monthly contributors in
        August 2025, up 66% year over year, which GitHub attributes partly to
        agent-assisted coding. Cited in the third figure.""")),
    ("llmprefs", "Twist et al., A Study of LLMs' Preferences for Libraries and "
                 "Programming Languages",
     _one_line("""Language models choosing Python for 90 to 97% of benchmark tasks,
        and not choosing Rust once on high-performance ones. Cited in the second
        figure.""")),
    ("wild", "Liu et al., Agent Skills in the Wild",
     _one_line("""The 31,132-skill marketplace study whose script-bundling rate the
        first figure replicates.""")),
    ("spec", "The Agent Skills specification",
     _one_line("""The required front matter and the three optional folders the last
        figure measures against.""")),
    ("article01", "What language are agent skills written in?",
     _one_line("""The previous article in this series, whose language column the sixth
        figure reuses.""")),
]
