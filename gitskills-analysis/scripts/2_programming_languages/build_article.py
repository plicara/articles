#!/usr/bin/env python3
"""Build article 02's three outputs from one source of words and one of numbers.

    02-programming-languages/article.md        markers where figures go
    02-programming-languages/preview.html      the designed page, charts inline
    02-programming-languages/article.site.md   what ships, SVG inline, site tokens

The words come from content.py and the numbers from results/figures_02.json,
so no output can disagree with another or with the analysis. Article 01 kept
its prose in a template and its numbers in an export and still drifted three
times, because the preview and the shipped markdown were built by different
code; here they are built by the same function.

    uv run scripts/2_programming_languages/export_figures.py
    uv run scripts/2_programming_languages/build_article.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content as C
from charts import CHARTS

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "02-programming-languages"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(md):
    """The small Markdown subset content.py uses, as HTML.

    Links, inline code, bold and italic, and nothing else. The link and code
    passes run first and park their output behind placeholders, so escaping
    cannot reach a URL or double-escape a tag it just built; the prose around
    them is escaped, and the placeholders come back last.

    Bold runs before italic because `**x**` would otherwise be read as an
    italic star either side of x, which is how the credit block's journal
    title first shipped with literal asterisks around it.
    """
    held = {}

    def hold(html):
        token = f"\x00{len(held)}\x00"
        held[token] = html
        return token

    md = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                lambda m: hold(f'<a href="{m.group(2)}" target="_blank" '
                               f'rel="noopener">{esc(m.group(1))}</a>'), md)
    md = re.sub(r"`([^`]+)`", lambda m: hold(f"<code>{esc(m.group(1))}</code>"), md)
    out = esc(md)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", out)
    for token, html in held.items():
        out = out.replace(token, html)
    return out


# ------------------------------------------------------------------ tables
def md_table(head, rows):
    out = ["| " + " | ".join(str(c) for c in head) + " |",
           "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def html_table(head, rows):
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                for r in rows)
    return (f'<div class="tw"><table><thead><tr>{h}</tr></thead>'
            f"<tbody>{b}</tbody></table></div>")


# ------------------------------------------------------------------ markdown
def build_markdown():
    parts = [
        "---",
        f"title: {C.TITLE}",
        f"date: {C.DATE}",
        f"summary: {C.SUMMARY}",
        f"authors: {C.AUTHORS}",
        f"slug: {C.SLUG}",
        "---",
        "",
        C.LEDE,
        "",
    ]
    for f in C.FIGURES:
        parts += [f"## {f['claim']}", "", f["explain"], "",
                  f"`[FIG-{f['n']}: {f['label']}]`", "",
                  md_table(*f["table"]), ""]
    parts += [f"## {C.LIMITS_HEADING}", ""]
    for p in C.LIMITS:
        parts += [p, ""]
    parts += ["## credit", ""]
    for p in C.CREDIT:
        parts += [p, ""]
    parts += ["## sources", ""]
    parts += [f"- {C.a(key, name)}. {note}" for key, name, note in C.SOURCES]
    parts += [""]
    return "\n".join(parts)


# -------------------------------------------------------------------- charts
# The figures are drawn once against the review page's variables and then
# rewritten for whichever page is asking. --c-subject and --c-compare are the
# only two colours any chart uses, and the site defines exactly two series
# tokens, so the mapping is total rather than approximate.
SITE_COLOURS = {
    "var(--c-subject)": "var(--pl-series-2)",
    "var(--c-compare)": "var(--pl-series-1)",
    "var(--surface)": "var(--pl-bg)",
    "var(--muted)": "var(--pl-text-muted)",
    "var(--ink)": "var(--pl-text)",
}


def site_svg(n):
    svg = CHARTS[n]()
    for src, dst in SITE_COLOURS.items():
        svg = svg.replace(src, dst)
    return svg


def figure_html(f, svg):
    return (f'<figure class="pl-fig">\n'
            f'<span class="figlabel">Figure {f["n"]}. {esc(f["label"])}</span>\n'
            f"{svg}\n</figure>")


# The site renders markdown and passes raw HTML through, so the charts ship as
# inline SVG rather than flat images and theme with the page. Only tokens the
# site actually defines are used: --pl-series-1, --pl-series-2, --pl-text,
# --pl-text-muted, --pl-rule, --pl-bg and --pl-font-mono. Anything else would
# resolve to nothing, and a shape drawn in nothing is an invisible shape.
SITE_STYLE = """<style>
.pl-fig { margin: 2.4rem 0; }
.pl-fig svg { width: 100%; height: auto; display: block; overflow: visible; }
.pl-fig .figlabel { font-family: var(--pl-font-mono); font-size: .68rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--pl-text-muted);
  display: block; margin-bottom: .9rem; }
.pl-fig .lbl { font-size: 17px; fill: var(--pl-text); }
.pl-fig .val { font-size: 15px; fill: var(--pl-text); font-weight: 600;
  font-variant-numeric: tabular-nums; font-family: var(--pl-font-mono); }
.pl-fig .axis { font-size: 13.5px; fill: var(--pl-text-muted);
  font-family: var(--pl-font-mono); font-variant-numeric: tabular-nums; }
.pl-fig text.sub { font-size: 11.5px; fill: var(--pl-text-muted);
  font-family: var(--pl-font-mono); }
.pl-fig .ann { font-size: 13.5px; fill: var(--pl-text-muted);
  font-family: var(--pl-font-mono); }
.pl-fig .onbar { font-size: 14px; fill: var(--pl-bg); font-weight: 600;
  font-family: var(--pl-font-mono); }
.pl-fig .onbar.sm { font-size: 12px; font-weight: 400; opacity: .9; }
.pl-fig .onbar.off { fill: var(--pl-text-muted); }
.pl-fig .huge { font-size: 62px; fill: var(--pl-text); font-weight: 600;
  font-family: var(--pl-font-mono); font-variant-numeric: tabular-nums; }
.pl-fig .grid { stroke: var(--pl-rule); stroke-width: 1; }
.pl-fig .annrule { stroke: var(--pl-rule); stroke-width: 1; stroke-dasharray: 3 3; }
.pl-fig .refline { stroke: var(--pl-text-muted); stroke-width: 1; stroke-dasharray: 4 4; }
.pl-fig .connector { stroke: var(--pl-rule); stroke-width: 3; }
.pl-fig .whisker { stroke: var(--pl-series-1); stroke-width: 3; opacity: .55; }
.pl-fig .ci { fill: var(--pl-series-1); opacity: .18; }
.pl-fig .trendline { fill: none; stroke: var(--pl-series-2); stroke-width: 2.6;
  stroke-linejoin: round; }
.pl-fig .control { fill: none; stroke: var(--pl-rule); stroke-width: 2.2;
  stroke-linejoin: round; }
.pl-fig .dot { fill: var(--pl-series-2); }
.pl-fig .censored { fill: var(--pl-rule); opacity: .35; }
</style>"""


def build_site(md):
    out = md
    for f in C.FIGURES:
        block = figure_html(f, site_svg(f["n"]))
        out = re.sub(rf"`\[FIG-{f['n']}:.*?\]`", lambda _: block, out,
                     count=1, flags=re.S)
    left = re.findall(r"\[FIG-\d+", out)
    if left:
        raise SystemExit(f"site copy still has markers: {left}")
    # after the front matter, so the site parses its metadata first
    end = out.index("\n---\n", 3) + 5
    return out[:end] + "\n" + SITE_STYLE + "\n" + out[end:]


# ------------------------------------------------------------------- preview
def build_preview():
    figs = "\n".join(f"""<article class="fig">
  <div class="rail"><span class="num">{f['n']:02d}</span></div>
  <div class="body">
    <h2>{inline(f['claim'])}</h2>
    <p class="explain">{inline(f['explain'])}</p>
    <div class="plot">{CHARTS[f['n']]()}</div>
    {html_table(*f['table'])}
  </div>
</article>""" for f in C.FIGURES)

    limits = "".join(f"<p>{inline(p)}</p>" for p in C.LIMITS)
    credit = "".join(
        f"<blockquote>{inline(p[2:])}</blockquote>" if p.startswith("> ")
        else f"<p>{inline(p)}</p>" for p in C.CREDIT)
    sources = "".join(f"<li>{inline(C.a(key, name))}. {inline(note)}</li>"
                      for key, name, note in C.SOURCES)

    css = (Path(__file__).resolve().parent / "_review.css").read_text()
    return f"""<title>{esc(C.TITLE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{css}</style>
<header>
  <p class="eyebrow">Plicara Research &middot; article 02 &middot; the GitSkills series</p>
  <h1>{esc(C.TITLE)}</h1>
  <p class="lede">{inline(C.LEDE)}</p>
</header>
<main>{figs}</main>
<footer>
  <h3>{esc(C.LIMITS_HEADING)}</h3>
  {limits}
  <h3>Credit</h3>
  {credit}
  <h3>Sources</h3>
  <ul class="src">{sources}</ul>
</footer>"""


# ------------------------------------------------------------------ validate
def validate(md, site, preview):
    """Checks that have each caught a real defect on the way out the door."""
    problems = []

    if re.search(r"\{\{\w+\}\}|@@\w+@@", md + site + preview):
        problems.append("an unsubstituted placeholder survived")
    if "—" in md or "—" in site:
        problems.append("em-dash in shipped markdown; house style forbids it")

    # Every figure has to reach every output. A figure that is silently
    # dropped still leaves a page that looks finished.
    for f in C.FIGURES:
        if f"[FIG-{f['n']}:" not in md:
            problems.append(f"FIG-{f['n']} missing from article.md")
        if f"Figure {f['n']}." not in site:
            problems.append(f"FIG-{f['n']} missing from the site copy")

    for tag in ("div", "figure", "table", "article"):
        opens = len(re.findall(rf"<{tag}[ >]", preview))
        closes = preview.count(f"</{tag}>")
        if opens != closes:
            problems.append(f"preview {tag}: {opens} open against {closes} closed")

    # Colours only the review page defines would resolve to nothing on the
    # site, and a shape drawn in nothing is an invisible shape.
    for token in sorted(set(re.findall(r"var\(--[a-z0-9-]+\)", site))):
        if not token.startswith("var(--pl-"):
            problems.append(f"site copy carries a non-site colour token: {token}")

    # The dataset is someone else's work; every naming of it should be one
    # click from the paper.
    body = site[site.index("\n---\n", 3):]
    for m in re.finditer(r"GitSkills", body):
        if "arxiv.org/abs/2608.10906" not in body[max(0, m.start() - 300):m.start() + 300]:
            problems.append("GitSkills named without a nearby link to the paper")

    if problems:
        raise SystemExit("build failed validation:\n  "
                         + "\n  ".join(sorted(set(problems))[:12]))


md = build_markdown()
site = build_site(md)
preview = build_preview()
validate(md, site, preview)

for path, text in ((ART / "article.md", md),
                   (ART / "article.site.md", site),
                   (ART / "preview.html", preview)):
    path.write_text(text)
    print(f"wrote {path.relative_to(ROOT)}  ({len(text):,} bytes)")
print(f"{len(C.FIGURES)} figures, validated")
