"""Render the article to HTML, with every chart drawn from figures.json.

Run export_figures.py first. Nothing here retypes a number: the prose
carries placeholders that are filled from the same JSON the charts read,
so regenerating after the full-corpus run is two commands and no
transcription.

    uv run scripts/1_natural_language/export_figures.py
    uv run scripts/1_natural_language/build_article.py
"""

import json
from math import cos, pi, sin
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG = json.loads((ROOT / "results" / "figures.json").read_text())
OUT = ROOT / "results" / "article.html"

NATIVE = {"English": "English", "Chinese": "中文", "Japanese": "日本語",
          "German": "Deutsch", "Korean": "한국어", "Portuguese": "Português",
          "Spanish": "Español", "French": "Français", "Russian": "Русский",
          "Italian": "Italiano", "Turkish": "Türkçe", "Vietnamese": "Tiếng Việt"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------- charts
def chart_distribution():
    rows = [d for d in FIG["distribution"] if d["code"] != "uncertain"][:8]
    top = rows[0]["pct"]
    h, gap = 26, 10
    bars = []
    for i, d in enumerate(rows):
        y = i * (h + gap)
        w = max(2.0, 640 * (d["pct"] / top))
        fill = "var(--c-en)" if d["code"] == "en" else "var(--c-other)"
        native = NATIVE.get(d["name"], d["name"])
        label = (f'{esc(d["name"])}' if native == d["name"]
                 else f'{esc(d["name"])} <tspan class="native">{esc(native)}</tspan>')
        bars.append(f'''
    <text x="0" y="{y + 17}" class="lbl">{label}</text>
    <rect x="150" y="{y + 3}" width="{w:.1f}" height="{h - 6}" rx="1.5" fill="{fill}"/>
    <text x="{150 + w + 10:.1f}" y="{y + 17}" class="val">{d["pct"]}%</text>''')
    height = len(rows) * (h + gap)
    return f'''<svg viewBox="0 0 900 {height}" role="img"
     aria-label="Language distribution of agent skills">{"".join(bars)}
</svg>'''


def chart_trend():
    pts = FIG["trend_monthly"]
    W, H, PAD_L, PAD_B, PAD_T = 900, 300, 46, 34, 14
    lo_y, hi_y = 0, 24
    n = len(pts)

    def x(i):
        return PAD_L + i * (W - PAD_L - 18) / (n - 1)

    def y(v):
        return PAD_T + (1 - (v - lo_y) / (hi_y - lo_y)) * (H - PAD_T - PAD_B)

    band = ([f"{x(i):.1f},{y(p['hi']):.1f}" for i, p in enumerate(pts)]
            + [f"{x(i):.1f},{y(p['lo']):.1f}" for i in range(n - 1, -1, -1)
               for p in [pts[i]]])
    line = " ".join(f"{x(i):.1f},{y(p['pct']):.1f}" for i, p in enumerate(pts))
    grid = "".join(
        f'<line x1="{PAD_L}" y1="{y(v):.1f}" x2="{W - 18}" y2="{y(v):.1f}" class="grid"/>'
        f'<text x="{PAD_L - 10}" y="{y(v) + 4:.1f}" class="axis" text-anchor="end">{v}%</text>'
        for v in (0, 8, 16, 24))
    ticks = "".join(
        f'<text x="{x(i):.1f}" y="{H - 12}" class="axis" text-anchor="middle">'
        f'{p["period"][2:].replace("-", "·")}</text>'
        for i, p in enumerate(pts))
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(p["pct"]):.1f}" r="{4 if not p["partial"] else 3}" '
        f'class="{"dot" if not p["partial"] else "dot partial"}"/>'
        for i, p in enumerate(pts))
    last = pts[-1]
    shade = (f'<rect x="{x(n - 1) - 14:.1f}" y="{PAD_T}" width="{W - 18 - x(n - 1) + 14:.1f}" '
             f'height="{H - PAD_T - PAD_B}" class="censored"/>') if last["partial"] else ""
    return f'''<svg viewBox="0 0 {W} {H}" role="img"
     aria-label="Non-English share of newly created skills by month">
  {grid}{shade}
  <polygon points="{" ".join(band)}" class="ci"/>
  <polyline points="{line}" class="trendline"/>
  {dots}{ticks}
</svg>'''


def chart_clock():
    dials = FIG["clock"]
    size, r_out, r_in = 190, 74, 26
    cells = []
    for d in dials:
        total = sum(d["hours"]) or 1
        peak = max(d["hours"]) or 1
        cx = cy = size / 2
        wedges = []
        for h, v in enumerate(d["hours"]):
            a0 = (h / 24) * 2 * pi - pi / 2
            a1 = ((h + 1) / 24) * 2 * pi - pi / 2
            rr = r_in + (r_out - r_in) * (v / peak)
            night = 16 <= h < 24
            x0, y0 = cx + r_in * cos(a0), cy + r_in * sin(a0)
            x1, y1 = cx + r_in * cos(a1), cy + r_in * sin(a1)
            x2, y2 = cx + rr * cos(a1), cy + rr * sin(a1)
            x3, y3 = cx + rr * cos(a0), cy + rr * sin(a0)
            wedges.append(
                f'<path d="M{x0:.1f},{y0:.1f} A{r_in},{r_in} 0 0 1 {x1:.1f},{y1:.1f} '
                f'L{x2:.1f},{y2:.1f} A{rr:.1f},{rr:.1f} 0 0 0 {x3:.1f},{y3:.1f} Z" '
                f'class="{"wedge night" if night else "wedge"}"/>')
        cells.append(f'''
  <figure class="dial">
    <svg viewBox="0 0 {size} {size}" role="img" aria-label="Commit hours for {esc(d["language"])}">
      <circle cx="{cx}" cy="{cy}" r="{r_out + 6}" class="dialring"/>
      {"".join(wedges)}
      <text x="{cx}" y="{cy + 4}" class="dialpct">{d["night_pct"]}%</text>
    </svg>
    <figcaption><strong>{esc(d["language"])}</strong><span>n={d["n"]}</span></figcaption>
  </figure>''')
    return f'<div class="dials">{"".join(cells)}</div>'


def chart_copies():
    rows = FIG["copies_all"]
    W, H = 900, 210
    bw, gap = 132, 44
    top = 18.0
    bars = []
    for i, c in enumerate(rows):
        x = 70 + i * (bw + gap)
        bh = (H - 58) * (c["pct"] / top)
        y = H - 40 - bh
        bars.append(f'''
    <rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" rx="2" class="copybar"/>
    <text x="{x + bw / 2}" y="{y - 9:.1f}" class="val" text-anchor="middle">{c["pct"]}%</text>
    <text x="{x + bw / 2}" y="{H - 20}" class="axis" text-anchor="middle">{esc(c["bucket"])} {"copy" if c["bucket"] == "1" else "copies"}</text>
    <text x="{x + bw / 2}" y="{H - 6}" class="axis dim" text-anchor="middle">n={c["n"]:,}</text>''')
    return f'''<svg viewBox="0 0 {W} {H}" role="img"
     aria-label="Non-English share falls as skills are copied more">{"".join(bars)}
</svg>'''


def chart_maintenance():
    rows = FIG["maintenance"]
    W, H = 900, 230
    group, bw, gap = 230, 88, 14
    top = 46.0
    out = []
    for i, m in enumerate(rows):
        gx = 78 + i * group
        for j, (key, cls) in enumerate((("english", "c-en"), ("non_english", "c-other"))):
            v = m[key]["pct"]
            bh = (H - 66) * (v / top)
            x = gx + j * (bw + gap)
            y = H - 46 - bh
            out.append(f'''
    <rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" rx="2" fill="var(--{cls})"/>
    <text x="{x + bw / 2}" y="{y - 9:.1f}" class="val" text-anchor="middle">{v}%</text>''')
        out.append(f'<text x="{gx + bw + gap / 2}" y="{H - 24}" class="axis" '
                   f'text-anchor="middle">within {m["window"]} days</text>')
    return f'''<svg viewBox="0 0 {W} {H}" role="img"
     aria-label="Revision rate by language at fixed ages">{"".join(out)}
</svg>'''


# ------------------------------------------------------------------ prose
q = {t["period"]: t for t in FIG["trend_quarterly"]}
q1, q2 = q["2026-Q1"], q["2026-Q2"]
rob = {r["period"]: r for r in FIG["robustness"]["never_copied"]}
auth = FIG["authorship"]
zh = FIG["chinese_script"]
dist = {d["name"]: d for d in FIG["distribution"]}
m30 = next(m for m in FIG["maintenance"] if m["window"] == 30)
m90 = next(m for m in FIG["maintenance"] if m["window"] == 90)
clock = {c["language"]: c for c in FIG["clock"]}

HTML = f"""<title>The Language of Agent Skills</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,300;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root {{
    --ground:      #f5f6f8;
    --surface:     #ffffff;
    --ink:         #14181f;
    --ink-soft:    #4a5261;
    --ink-faint:   #838b9a;
    --rule:        #dde0e6;
    --c-en:        #2d4ea2;
    --c-other:     #c8761a;
    --c-en-soft:   rgba(45, 78, 162, .14);
    --accent:      #2d4ea2;
    --flag:        #a03c2e;
    --measure:     34rem;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground:    #101317;
      --surface:   #171b21;
      --ink:       #e8eaed;
      --ink-soft:  #a8b0bd;
      --ink-faint: #6f7885;
      --rule:      #262b33;
      --c-en:      #7c9be8;
      --c-other:   #e0a155;
      --c-en-soft: rgba(124, 155, 232, .18);
      --accent:    #7c9be8;
      --flag:      #e08a78;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground:    #101317;
    --surface:   #171b21;
    --ink:       #e8eaed;
    --ink-soft:  #a8b0bd;
    --ink-faint: #6f7885;
    --rule:      #262b33;
    --c-en:      #7c9be8;
    --c-other:   #e0a155;
    --c-en-soft: rgba(124, 155, 232, .18);
    --accent:    #7c9be8;
    --flag:      #e08a78;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    background: var(--ground);
    color: var(--ink);
    font-family: Newsreader, Georgia, "Times New Roman", serif;
    font-size: 19px;
    line-height: 1.62;
    margin: 0;
    padding: 0 1.5rem 6rem;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 58rem; margin: 0 auto; }}
  .col {{ max-width: var(--measure); margin-left: auto; margin-right: auto; }}

  .mono, .eyebrow, figcaption, .axis, .val, .lbl, .note, .stat-l, table {{
    font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }}

  header {{ padding: 5rem 0 2.5rem; }}
  .eyebrow {{
    font-size: .7rem; letter-spacing: .13em; text-transform: uppercase;
    color: var(--ink-faint); display: flex; gap: .6rem; flex-wrap: wrap;
  }}
  .eyebrow b {{ color: var(--accent); font-weight: 500; }}
  h1 {{
    font-size: clamp(2.6rem, 6.5vw, 4.1rem); font-weight: 400;
    line-height: 1.04; letter-spacing: -.022em; text-wrap: balance;
    margin: 1.2rem 0 0;
  }}
  h1 em {{ font-style: italic; color: var(--ink-soft); }}
  .standfirst {{
    font-size: 1.24rem; color: var(--ink-soft); margin: 1.4rem 0 0;
    max-width: 40rem; text-wrap: pretty;
  }}
  h2 {{
    font-size: 1.85rem; font-weight: 400; letter-spacing: -.015em;
    margin: 4.5rem 0 .3rem; text-wrap: balance;
  }}
  h3 {{ font-size: 1.15rem; font-weight: 600; margin: 2.6rem 0 .2rem; }}
  p {{ margin: 1.05em 0; text-wrap: pretty; }}
  a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }}
  strong {{ font-weight: 600; }}

  hr.rule {{ border: 0; border-top: 1px solid var(--rule); margin: 0; }}

  figure {{ margin: 2.6rem 0; }}
  figure svg {{ width: 100%; height: auto; display: block; overflow: visible; }}
  figcaption {{
    font-size: .74rem; color: var(--ink-faint); line-height: 1.55;
    margin-top: .9rem; max-width: 44rem;
  }}
  .figlabel {{
    font-family: "IBM Plex Mono", monospace; font-size: .68rem;
    letter-spacing: .12em; text-transform: uppercase; color: var(--ink-faint);
    margin-bottom: 1rem; display: block;
  }}

  .lbl {{ font-size: 13px; fill: var(--ink); }}
  .lbl .native {{ fill: var(--ink-faint); }}
  .val {{ font-size: 13px; fill: var(--ink-soft); font-weight: 500; font-variant-numeric: tabular-nums; }}
  .axis {{ font-size: 11.5px; fill: var(--ink-faint); font-variant-numeric: tabular-nums; }}
  .axis.dim {{ opacity: .7; }}
  .grid {{ stroke: var(--rule); stroke-width: 1; }}
  .ci {{ fill: var(--c-en-soft); }}
  .trendline {{ fill: none; stroke: var(--c-other); stroke-width: 2.4; stroke-linejoin: round; }}
  .dot {{ fill: var(--c-other); }}
  .dot.partial {{ fill: var(--ground); stroke: var(--c-other); stroke-width: 2; }}
  .censored {{ fill: var(--rule); opacity: .35; }}
  .copybar {{ fill: var(--c-other); }}

  .dials {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1.4rem; margin: 2rem 0 0;
  }}
  .dial {{ margin: 0; }}
  .dial figcaption {{ text-align: center; margin-top: .3rem; display: grid; gap: .1rem; }}
  .dial figcaption strong {{ color: var(--ink); font-size: .78rem; font-weight: 500; }}
  .dialring {{ fill: none; stroke: var(--rule); }}
  .wedge {{ fill: var(--c-other); opacity: .85; }}
  .wedge.night {{ fill: var(--c-en); opacity: .9; }}
  .dialpct {{ font-family: "IBM Plex Mono", monospace; font-size: 15px; font-weight: 600;
              fill: var(--ink); text-anchor: middle; font-variant-numeric: tabular-nums; }}

  .legend {{ display: flex; gap: 1.4rem; flex-wrap: wrap; font-family: "IBM Plex Mono", monospace;
             font-size: .72rem; color: var(--ink-faint); margin-top: 1.1rem; }}
  .legend i {{ width: .8rem; height: .8rem; border-radius: 2px; display: inline-block;
               vertical-align: -1px; margin-right: .4rem; }}

  .stat {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1px; background: var(--rule); border: 1px solid var(--rule);
    margin: 2.4rem 0;
  }}
  .stat > div {{ background: var(--surface); padding: 1.25rem 1.35rem; }}
  .stat-n {{ font-size: 2.05rem; line-height: 1; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
  .stat-l {{ font-size: .7rem; letter-spacing: .06em; color: var(--ink-faint);
             margin-top: .5rem; line-height: 1.45; }}

  table {{ width: 100%; border-collapse: collapse; font-size: .8rem; margin: 1.8rem 0; }}
  th, td {{ text-align: left; padding: .58rem .7rem; border-bottom: 1px solid var(--rule); }}
  th {{ font-weight: 500; color: var(--ink-faint); font-size: .68rem;
        letter-spacing: .08em; text-transform: uppercase; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.us td {{ background: var(--c-en-soft); font-weight: 600; }}
  .scroll {{ overflow-x: auto; }}

  .note {{
    font-size: .78rem; line-height: 1.6; color: var(--ink-soft);
    border-left: 2px solid var(--rule); padding: .1rem 0 .1rem 1.1rem;
    margin: 2rem 0;
  }}
  .note b {{ color: var(--flag); font-weight: 600; }}

  footer {{ margin-top: 5rem; padding-top: 1.6rem; border-top: 1px solid var(--rule);
            font-family: "IBM Plex Mono", monospace; font-size: .72rem;
            color: var(--ink-faint); line-height: 1.7; }}
  footer a {{ color: var(--ink-soft); }}
  footer strong {{ color: var(--ink-soft); }}
  .credit-h {{ font-family: "IBM Plex Mono", monospace; font-size: .68rem;
               letter-spacing: .12em; text-transform: uppercase; color: var(--ink-faint);
               font-weight: 500; margin: 2.2rem 0 .2rem; }}
  .credit-h:first-child {{ margin-top: 0; }}
  blockquote.cite {{
    margin: 1rem 0; padding: .9rem 1.1rem; background: var(--surface);
    border-left: 2px solid var(--accent); color: var(--ink-soft);
    font-size: .74rem; line-height: 1.65;
  }}
  @media (prefers-reduced-motion: no-preference) {{
    .trendline {{ animation: draw 1.1s ease-out both; }}
    @keyframes draw {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
  }}
</style>

<div class="wrap">
<header class="col">
  <div class="eyebrow"><b>Article 01</b><span>·</span><span>The GitSkills series</span>
    <span>·</span><span>Plicara Research</span></div>
  <h1>What language are agent skills <em>written in?</em></h1>
  <p class="standfirst">Three point eight million instruction files on GitHub, read by a
  model that speaks every language. So why are {dist["English"]["pct"]}% of them in English —
  and what is changing?</p>
</header>
<hr class="rule">

<div class="col">
<p>In October 2025 Anthropic published a small open specification. Put a
<span class="mono">SKILL.md</span> file in a folder, write instructions for an AI agent in
plain prose, and the agent loads it when it judges the task relevant.</p>

<p>No compiler checks it. No type system validates it. There is no package manager and no
registry of record. A skill spreads the way a recipe spreads — somebody copies the folder.</p>

<p>Nine months later there were <strong>3.8 million</strong> of them across 282,200 public
repositories. That is the <a href="https://arxiv.org/abs/2608.10906">GitSkills</a> dataset,
released in August 2026.</p>

<p>Here is what makes skills strange as software: <strong>they are written in human
language, and the runtime is a multilingual model.</strong> There is no technical reason to
write one in English. A developer in Shenzhen or São Paulo can state a procedure more
precisely in their own language, and the agent will follow it just as well.</p>

<p>So do they? Nobody had checked — the dataset's own authors list it as an open
question and answer it nowhere.</p>

<h2>The distribution</h2>
<p>We ran language identification over the prose body of every distinct skill, after
stripping front matter and fenced code.</p>
</div>

<figure>
  <span class="figlabel">Share of distinct skills, by language</span>
  {chart_distribution()}
  <figcaption>Bars are proportional to English. {FIG["corpus"]["classified"]:,} distinct
  skill contents; the {FIG["non_english_overall"]["pct"]}% that are not English are led by
  Chinese at {dist["Chinese"]["pct"]}%.</figcaption>
</figure>

<div class="col">
<p>Chinese is a distant but clear second. Split by script, it is
<strong>{zh["simplified"]} simplified</strong> against <strong>{zh["traditional"]}
traditional</strong> — overwhelmingly mainland rather than Taiwan or Hong Kong.</p>

<p>The right comparison is GitHub's own documentation, not its issues or pull requests. A
2026 ICSE study put repository documentation at 13.0% non-English with Chinese at 3.3% of
repositories. So skills are <em>not</em> unusually non-English overall —
{FIG["non_english_overall"]["pct"]}% against 13.0% is a dead heat. But they are markedly
more Chinese: {dist["Chinese"]["pct"]}% against 3.3%.</p>

<h2>Why every published number disagrees</h2>
<p>Here is the part that should make you suspicious of all of this, including ours.</p>
<div class="scroll">
<table>
  <thead><tr><th>Reported English share</th><th>Corpus</th><th>Method</th></tr></thead>
  <tbody>
    <tr><td class="num">65.0%</td><td>557 healthcare skills, ClawHub</td><td>not stated</td></tr>
    <tr><td class="num">81.8%</td><td>26,502 skills, ClawHub</td><td>not stated</td></tr>
    <tr class="us"><td class="num">{dist["English"]["pct"]}%</td><td>{FIG["corpus"]["classified"]:,} distinct, GitHub — ours</td><td>py3langid, conf ≥ 0.80</td></tr>
    <tr><td class="num">92.6%</td><td>133,149 skills, skills.sh</td><td>fast-langdetect</td></tr>
    <tr><td class="num">99.7%</td><td>English-seeded crawl</td><td>seeded</td></tr>
  </tbody>
</table>
</div>

<p>These are not contradictions. They are five different populations. Curated marketplaces
skew English. Domain slices skew toward wherever that domain is active. A crawl seeded with
English queries finds English.</p>

<p>We tested one tidy explanation and it failed. We suspected that corpora filtering for
valid front matter were quietly discarding non-English skills. They are not — non-English
skills have <em>slightly better</em> front-matter validity, 88.4% against 86.9%, and
filtering moves the English share by 0.2 points. The spread is about where you look, not
about quality screening.</p>

<p>Which generalises past this dataset: when someone tells you what "the AI ecosystem"
looks like, ask which registry they scraped.</p>

<h2>Skills are getting less English</h2>
<p>Skills carry commit history, so each one has a creation date. That turns a static pie
chart into a trend.</p>
</div>

<figure>
  <span class="figlabel">Non-English share of newly created skills, by month</span>
  {chart_trend()}
  <figcaption>Band is the 95% Wilson interval. July 2026 is shaded because collection ran
  mid-month, so that cohort is censored and excluded from comparisons. Quarterly:
  {q1["pct"]}% [{q1["lo"]}, {q1["hi"]}] in Q1 against {q2["pct"]}% [{q2["lo"]},
  {q2["hi"]}] in Q2 — the intervals do not overlap.</figcaption>
</figure>

<div class="col">
<p>For scale, that ICSE study found GitHub-wide non-English documentation growing from 3.7%
to 13.0% — <strong>over ten years</strong>. Skills moved comparably in a single quarter. New
artifact types acquire their demographics much faster than mature ones.</p>

<p>Not every language is rising. Japanese is the exception: 6.5% of skills in Q4 2025, down
to {FIG["trend_by_language"]["Japanese"][-1]["pct"]}% by Q3 2026 — early to the format, and
losing share as everyone else arrives.</p>

<h3>Why we believe it</h3>
<p>A trend like this is exactly the kind of thing that turns out to be an artifact, so we
tried to break it. Commit history exists for only
{round(100 * FIG["corpus"]["dated"] / FIG["corpus"]["classified"])}% of skills, and that
subsample leans toward heavily copied ones — which matters, because copying is strongly
related to language. Holding copies fixed at one, the rise is
<strong>larger</strong>: {rob["2026-Q1"]["pct"]}% to {rob["2026-Q2"]["pct"]}%. Counting each
repository only once, so no bulk uploader can swing it: 12.4% to 16.2%.</p>
</div>

<h2 class="col">The clock</h2>
<div class="col">
<p>This is the result we did not expect to get.</p>
<p>Commit timestamps are stored in UTC, so an author's local timezone is gone. But people
mostly commit while awake. If a group of skills is written by people in one part of the
world, their commits should <em>vanish</em> during that region's night.</p>
</div>

<figure>
  <span class="figlabel">When skills are first committed — 24 hours, UTC, midnight at top</span>
  {chart_clock()}
  <div class="legend col">
    <span><i style="background:var(--c-other)"></i>00:00–16:00 UTC</span>
    <span><i style="background:var(--c-en)"></i>16:00–24:00 UTC — midnight to 8am in UTC+8</span>
  </div>
  <figcaption class="col">Centre figure is the share of first commits falling in that
  16:00–24:00 window. Groups outside English are small — {clock["Chinese"]["n"]} Chinese,
  {clock["Japanese"]["n"]} Japanese, {clock["Korean"]["n"]} Korean,
  {clock["Spanish/Portuguese"]["n"]} Spanish/Portuguese — so read the contrast, not the
  decimals.</figcaption>
</figure>

<div class="col">
<p>Chinese-language skills nearly disappear from East Asia's night:
<strong>{clock["Chinese"]["night_pct"]}%</strong> against English's
{clock["English"]["night_pct"]}%. English is flat across all 24 hours — the signature of a
globally distributed population with no single night. And Spanish/Portuguese runs the
opposite way at {clock["Spanish/Portuguese"]["night_pct"]}%, peaking while Europe sleeps.
Those skills are being written in the Americas, not Iberia.</p>

<p>Why it matters: <strong>nothing in the language identifier knows what time a file was
committed.</strong> Two independent signals, agreeing.</p>

<div class="note"><b>Honest limits.</b> This is a population-level phase estimate, good to
a couple of hours at best. It cannot separate UTC+8 from UTC+9, a language is not a country,
and it says nothing about any individual author. We found no published validation of
hour-of-day inference at this granularity, so treat it as corroboration rather than
geolocation. Worth noting for anyone building on this: a raw git commit <em>does</em> record
the author's UTC offset — this dataset normalised it away.</div>

<h2>Copied, or tended?</h2>
<p>Two findings point in opposite directions, and together they are the most interesting
thing here.</p>
</div>

<figure>
  <span class="figlabel">Non-English share, by how often a skill has been copied verbatim</span>
  {chart_copies()}
  <figcaption>Across all {FIG["corpus"]["classified"]:,} distinct contents. Ten
  repositories hold 28% of every skill file in this corpus — registries and mirrors rather
  than authors — so we re-ran it with them removed (15.2% → 5.1%) and again counting
  distinct owners ({FIG["copies_owner"][0]["pct"]}% → {FIG["copies_owner"][-1]["pct"]}%).
  Both widen the gap.</figcaption>
</figure>

<div class="col">
<p><strong>English skills get copied more.</strong> The non-English share falls steadily
the more a skill is reused — from {FIG["copies_all"][0]["pct"]}% among skills nobody ever
copied to {FIG["copies_all"][-1]["pct"]}% among those copied six or more times.</p>

<p><strong>But non-English skills get revised more.</strong> That one needs an age
correction, since non-English skills are younger and have had less time to be touched.
Compared at equal age, the gap is wide and it widens as the window grows.</p>
</div>

<figure>
  <span class="figlabel">Share revised within N days, among skills at least N days old</span>
  {chart_maintenance()}
  <div class="legend col">
    <span><i style="background:var(--c-en)"></i>English</span>
    <span><i style="background:var(--c-other)"></i>Non-English</span>
  </div>
  <figcaption class="col">At 30 days, {m30["english"]["pct"]}% of English skills have been
  revised against {m30["non_english"]["pct"]}% of non-English ones; by 90 days it is
  {m90["english"]["pct"]}% against {m90["non_english"]["pct"]}%.</figcaption>
</figure>

<div class="col">
<p>So the two populations behave differently. English skills <em>propagate</em> — written
once, copied widely, rarely touched again. Non-English skills are <em>tended</em> — copied
less, revised more.</p>

<p>There is a plausible mechanical reason for the copying half. Discovery is search, search
is lexical, and a developer searching in English will not surface a skill written in Chinese
even when a multilingual model could execute it perfectly. The bottleneck is not the
runtime. It is the index.</p>

<h2>Who is actually writing these?</h2>
<p>The dataset's authors asked one more thing: how many skills do agents write themselves?
The obvious way to check fails. GitHub's own bot flag catches almost nothing, because
agent-written code is committed under the human's account.</p>

<p>The signal that works is the trailer — the <span class="mono">Co-Authored-By</span> line
a coding agent appends to commits it authored. That is the tool claiming authorship, not us
inferring it from prose.</p>
</div>

<div class="stat col">
  <div><div class="stat-n" style="color:var(--c-other)">{auth["overall"]["pct"]}%</div>
    <div class="stat-l">name an AI agent in a commit trailer<br>[{auth["overall"]["lo"]}, {auth["overall"]["hi"]}] · n={auth["overall"]["n"]:,}</div></div>
  <div><div class="stat-n">0.8%</div>
    <div class="stat-l">flagged as a bot by the platform itself</div></div>
  <div><div class="stat-n">{auth["by_language"]["Japanese"]["pct"]}%</div>
    <div class="stat-l">of Japanese skills are agent-authored — against {auth["by_language"]["Chinese"]["pct"]}% of Chinese</div></div>
</div>

<div class="col">
<p>Nearly a third of skills carry an agent's fingerprint, and the platform sees almost none
of it. Claude accounts for the overwhelming majority of those trailers, with Cursor, Copilot
and Codex trailing far behind; the trailers even carry model versions.</p>

<p>Read it as a floor, not a measurement. A skill whose author stripped the trailer, or
squashed it away, or used a tool that never emits one, counts as human here.</p>

<div class="note"><b>What this doesn't show.</b> These numbers come from the 13,000-skill
public sample, not the full 3.8M corpus. Language identification keys on script and function
words, so a German skill thick with English technical vocabulary gets pulled toward English —
non-English share is a lower bound. Dates cover only part of the corpus and only
deduplication representatives, so "created" means the first commit touching <em>that copy</em>.
And a crawl sees only survivors: any skill created and deleted before July 2026 is invisible,
which inflates every maintenance figure here.</div>

<h2>Next</h2>
<p>Article 02 asks which <em>programming</em> languages skills talk about — with a warning
attached. Our first pass had Shell/Bash leading every language at 37.5%, which turned out to
be an artifact of counting pasted commands. Measured as authoring rather than mentioning,
Python leads and Shell drops to 2.6%. The gap between those two questions is the whole
article.</p>
</div>

<footer class="col">
  <h3 class="credit-h">The data</h3>
  <p>None of this exists without the dataset, which was built and released by someone else.
  Every number on this page is derived from <strong>GitSkills</strong>, and all credit for
  collecting, deduplicating and documenting 3.8 million skill files belongs to its authors:</p>

  <blockquote class="cite">Giuseppe Destefanis, Daniel Graziotin, Matteo Vaccargiu, and
  Marco Ortu. 2027. GitSkills: A Dataset of Agent Skills on GitHub. In <i>Proceedings of the
  24th International Conference on Mining Software Repositories (MSR '27)</i>.</blockquote>

  <p>Preprint: <a href="https://arxiv.org/abs/2608.10906">arXiv:2608.10906</a> ·
  Archive: <a href="https://doi.org/10.5281/zenodo.21875637">10.5281/zenodo.21875637</a> ·
  Mirror: <a href="https://huggingface.co/datasets/mvaccargiu/gitskills">mvaccargiu/gitskills</a> ·
  Licence: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</p>

  <p>GitSkills is the dataset for the MSR '27 Mining Challenge. <strong>We are not affiliated
  with its authors, with MSR, or with the challenge</strong>, and nothing here should be read
  as endorsed by them. The dataset is theirs; the analysis, and any error in it, is ours.
  Several of the research questions we take up — including which natural languages skills are
  written in — are ones the GitSkills authors posed and left open.</p>

  <h3 class="credit-h">Everything else</h3>
  <p>Analysis code: <a href="https://github.com/plicara/gitskills-analysis">github.com/plicara/gitskills-analysis</a>.
  Every figure on this page is generated from a single machine-readable export rather than
  transcribed by hand, so the whole thing can be regenerated and checked.</p>
  <p>Comparisons drawn from Bhuiyan et al., ICSE '26 (<a href="https://arxiv.org/abs/2602.19446">arXiv:2602.19446</a>);
  Hong et al. (<a href="https://arxiv.org/abs/2607.01456">arXiv:2607.01456</a>);
  Hu, Shang &amp; Zhang (<a href="https://arxiv.org/abs/2604.13064">arXiv:2604.13064</a>);
  and <a href="https://arxiv.org/abs/2605.02709">arXiv:2605.02709</a>,
  <a href="https://arxiv.org/abs/2606.03565">arXiv:2606.03565</a>,
  <a href="https://arxiv.org/abs/2601.10338">arXiv:2601.10338</a>.</p>
  <p>Found something wrong? We would genuinely like to know — corrections are welcome and
  will be logged on the page.</p>
</footer>
</div>
"""

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(HTML)
print(f"wrote {OUT}  ({len(HTML):,} bytes)")
