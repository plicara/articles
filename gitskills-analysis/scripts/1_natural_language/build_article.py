"""Build the article from one prose source and one number source.

article.md.tmpl holds the prose, once, with {{placeholders}} where numbers
go. This fills them from results/figures.json and writes three outputs:

    01-natural-language/article.md      the readable draft
    01-natural-language/article.site.md the copy that ships to the site
    01-natural-language/preview.html    designed page, charts inline

Both come from the same template, so they cannot disagree. Before this,
article.md was maintained by hand against the same export and drifted from
the HTML three separate times.

    uv run scripts/1_natural_language/export_figures.py
    uv run scripts/1_natural_language/build_article.py
"""

import json
import re
from math import cos, pi, sin
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
FIG = json.loads((ROOT / "results" / "figures.json").read_text())
# The preview belongs beside the prose it previews, so regenerating updates
# the file people actually open. Writing it to results/ meant the committed
# preview silently went stale whenever figures moved.
ART = ROOT / "01-natural-language"
TMPL = ART / "article.md.tmpl"
OUT_MD = ART / "article.md"
OUT_HTML = ART / "preview.html"

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
        w = max(2.0, 430 * (d["pct"] / top))
        fill = "var(--c-en)" if d["code"] == "en" else "var(--c-other)"
        native = NATIVE.get(d["name"], d["name"])
        label = (f'{esc(d["name"])}' if native == d["name"]
                 else f'{esc(d["name"])} <tspan class="native">{esc(native)}</tspan>')
        bars.append(f'''
    <text x="330" y="{y + 17}" class="lbl" text-anchor="end">{label}</text>
    <rect x="348" y="{y + 3}" width="{w:.1f}" height="{h - 6}" rx="1.5" fill="{fill}"/>
    <text x="{348 + w + 12:.1f}" y="{y + 17}" class="val">{d["pct"]}%</text>''')
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
    # the end ticks are anchored inward so they cannot run past the viewBox
    ticks = "".join(
        f'<text x="{x(i):.1f}" y="{H - 12}" class="axis" text-anchor="'
        f'{"start" if i == 0 else "end" if i == n - 1 else "middle"}">'
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
  <div class="dial">
    <svg viewBox="0 0 {size} {size}" role="img" aria-label="Commit hours for {esc(d["language"])}">
      <circle cx="{cx}" cy="{cy}" r="{r_out + 6}" class="dialring"/>
      {"".join(wedges)}
      <text x="{cx}" y="{cy + 4}" class="dialpct">{d["night_pct"]}%</text>
    </svg>
    <div class="dial-label"><strong>{esc(d["language"])}</strong><span>n={d["n"]:,}</span></div>
  </div>''')
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



def chart_language_trends():
    """Small multiples: one panel per language, so levels stay comparable.

    Plotted on a shared axis rather than one chart with four lines, because
    the bands overlap heavily at these levels and the point of the figure is
    the direction each language moves, not their ranking.
    """
    series = FIG["trend_by_language"]
    W, H = 232, 168
    PAD_L, PAD_T, PAD_B = 34, 16, 30
    y_max = 8.0
    panels = []
    for name, pts in series.items():
        n = len(pts)
        # Direction and delta are read across the two complete quarters that
        # carry enough skills to mean anything, not from 2025-Q4, whose cells
        # are single files and whose interval spans most of the axis.
        solid = [p for p in pts if not p["partial"] and p["n"] >= 300]
        ref, cur = solid[0], solid[-1]
        colour = "var(--c-other)" if cur["pct"] >= ref["pct"] else "var(--c-en)"

        def x(i, n=n):
            return PAD_L + i * (W - PAD_L - 12) / (n - 1)

        def y(v):
            return PAD_T + (1 - min(v, y_max) / y_max) * (H - PAD_T - PAD_B)

        band = ([f"{x(i):.1f},{y(p['hi']):.1f}" for i, p in enumerate(pts)]
                + [f"{x(i):.1f},{y(pts[i]['lo']):.1f}" for i in range(n - 1, -1, -1)])
        line = " ".join(f"{x(i):.1f},{y(p['pct']):.1f}" for i, p in enumerate(pts))
        grid = "".join(
            f'<line x1="{PAD_L}" y1="{y(v):.1f}" x2="{W - 12}" y2="{y(v):.1f}" class="grid"/>'
            for v in (0, 4, 8))
        dots = "".join(
            f'<circle cx="{x(i):.1f}" cy="{y(p["pct"]):.1f}" '
            f'r="{3.4 if not p["partial"] else 2.6}" '
            f'fill="{"var(--ground)" if p["partial"] else colour}" '
            f'stroke="{colour}" stroke-width="{2 if p["partial"] else 0}"/>'
            for i, p in enumerate(pts))
        ends = {0: "start", n - 1: "end"}
        ticks = "".join(
            f'<text x="{x(i):.1f}" y="{H - 14}" class="axis" '
            f'text-anchor="{ends[i]}">{p["period"][2:]}</text>'
            for i in ends for p in [pts[i]])
        yaxis = "".join(
            f'<text x="{PAD_L - 7}" y="{y(v) + 4:.1f}" class="axis" text-anchor="end">{v}%</text>'
            for v in (0, 4, 8))
        delta = cur["pct"] - ref["pct"]
        panels.append(f"""
  <div class="panel">
    <svg viewBox="0 0 {W} {H}" role="img"
         aria-label="{esc(name)} share of new skills by quarter">
      {grid}{yaxis}
      <polygon points="{" ".join(band)}" fill="{colour}" opacity=".15"/>
      <polyline points="{line}" fill="none" stroke="{colour}"
                stroke-width="2.2" stroke-linejoin="round"/>
      {dots}{ticks}
    </svg>
    <div class="panel-label"><strong>{esc(name)}</strong>
      <span class="delta" style="color:{colour}">{delta:+.1f} pts
      <span class="dwin">{ref["period"][2:]}&thinsp;&rarr;&thinsp;{cur["period"][2:]}</span>
      </span></div>
  </div>""")
    return f'<div class="panels">{"".join(panels)}</div>'


# ----------------------------------------------------------------- values
def pct(x):
    return f"{x}%"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


d = FIG
dist = {x["name"]: x for x in d["distribution"]}
quarters = {x["period"]: x for x in d["trend_quarterly"]}
months = {x["period"]: x for x in d["trend_monthly"]}
nc = {x["period"]: x for x in d["robustness"]["never_copied"]}
ro = {x["period"]: x for x in d["robustness"]["repo_once"]}
clock = {c["language"]: c for c in d["clock"]}
maint = {m["window"]: m for m in d["maintenance"]}
cop = {c["bucket"]: c for c in d["copies_all"]}
own = {c["bucket"]: c for c in d["copies_owner"]}
noagg = {c["bucket"]: c for c in d["copies_noagg"]}
tbl = d["trend_by_language"]
auth = d["authorship"]
val = d["validity"]
conc = d["concentration"]
prog = d["prog_languages"]


def by_lang(lang, period):
    return next(p for p in tbl[lang] if p["period"] == period)


VALUES = {
    "en_pct": pct(dist["English"]["pct"]),
    "zh_pct": pct(dist["Chinese"]["pct"]),
    "non_en_pct": pct(d["non_english_overall"]["pct"]),
    "classified": f"{d['corpus']['classified']:,}",
    "sample_size": f"{round(d['corpus']['classified'], -3):,}",
    "zh_simp": f'{d["chinese_script"]["simplified"]:,}',
    "zh_trad": f'{d["chinese_script"]["traditional"]:,}',
    "fm_en": pct(val["english"]["pct"]),
    "fm_non_en": pct(val["non_english"]["pct"]),
    "en_unfiltered": pct(val["english_share_unfiltered"]["pct"]),
    "en_valid_only": pct(val["english_share_valid_only"]["pct"]),
    "q2_n": f'{quarters["2026-Q2"]["n"]:,}',
    "q1_pct": pct(quarters["2026-Q1"]["pct"]), "q1_lo": quarters["2026-Q1"]["lo"],
    "q1_hi": quarters["2026-Q1"]["hi"],
    "q2_pct": pct(quarters["2026-Q2"]["pct"]), "q2_lo": quarters["2026-Q2"]["lo"],
    "q2_hi": quarters["2026-Q2"]["hi"],
    "jan_pct": pct(months["2026-01"]["pct"]),
    "jun_pct": pct(months["2026-06"]["pct"]),
    "coverage_pct": pct(round(100 * d["corpus"]["dated"] / d["corpus"]["classified"])),
    "nc_q1": pct(nc["2026-Q1"]["pct"]), "nc_q2": pct(nc["2026-Q2"]["pct"]),
    "ro_q1": pct(ro["2026-Q1"]["pct"]), "ro_q2": pct(ro["2026-Q2"]["pct"]),
    "bot_pct": pct(auth["platform_bot"]["pct"]),
    "feb_pct": pct(months["2026-02"]["pct"]), "mar_pct": pct(months["2026-03"]["pct"]),
    "uncertain_n": f'{next(x["n"] for x in d["distribution"] if x["code"] == "uncertain"):,}',
    "copies_1": pct(cop["1"]["pct"]), "copies_6": pct(cop["6+"]["pct"]),
    "owners_1": pct(own["1"]["pct"]), "owners_6": pct(own["6+"]["pct"]),
    "noagg_1": pct(noagg["1"]["pct"]), "noagg_6": pct(noagg["6+"]["pct"]),
    "top10_pct": pct(conc["top10_pct"]), "n_repos": f"{conc['repos']:,}",
    "effective_repos": round(conc["effective_repos"]),
    "agg_non_en": pct(conc["aggregator"]["pct"]),
    "ord_non_en": pct(conc["ordinary"]["pct"]),
    "auth_pct": pct(auth["overall"]["pct"]), "auth_lo": auth["overall"]["lo"],
    "auth_hi": auth["overall"]["hi"],
    "auth_ja": pct(auth["by_language"]["Japanese"]["pct"]),
    "auth_zh": pct(auth["by_language"]["Chinese"]["pct"]),
    "shell_mention": pct(prog["Shell/Bash"]["mention_pct"]),
    "shell_authoring": pct(prog["Shell/Bash"]["authoring_pct"]),
    "python_authoring": pct(prog["Python"]["authoring_pct"]),
    "distribution_table": table(
        ["Language", "Share of distinct skills"],
        [(x["name"], pct(x["pct"]))
         for x in d["distribution"] if x["code"] != "uncertain"][:8]),
    "language_trend_table": table(
        ["", "2026 Q1", "2026 Q2", "Change"],
        [(lang,
          f'{by_lang(lang, "2026-Q1")["pct"]}% [{by_lang(lang, "2026-Q1")["lo"]}, {by_lang(lang, "2026-Q1")["hi"]}]',
          f'{by_lang(lang, "2026-Q2")["pct"]}% [{by_lang(lang, "2026-Q2")["lo"]}, {by_lang(lang, "2026-Q2")["hi"]}]',
          f'{by_lang(lang, "2026-Q2")["pct"] - by_lang(lang, "2026-Q1")["pct"]:+.1f}')
         for lang in ("Chinese", "European", "Korean", "Japanese")]),
    "clock_table": table(
        ["Language", "Commits during East Asian night", "n"],
        [(c["language"],
          f'**{c["night_pct"]}%**' if c["language"] in ("Chinese", "Spanish/Portuguese")
          else pct(c["night_pct"]),
          f'{c["n"]:,}') for c in d["clock"]]),
    "xcheck_agree": pct(FIG["crosscheck"]["agreement_pct"]),
    "xcheck_delta": f'{FIG["crosscheck"]["delta_points"]:+.1f}',
    "m7_gap": f'{maint[7]["non_english"]["pct"] - maint[7]["english"]["pct"]:+.1f}',
    "m30_gap": f'{maint[30]["non_english"]["pct"] - maint[30]["english"]["pct"]:+.1f}',
    "m90_gap": f'{maint[90]["non_english"]["pct"] - maint[90]["english"]["pct"]:+.1f}',
    "maintenance_table": table(
        ["Window", "English", "Non-English"],
        [(f'{m["window"]} days', pct(m["english"]["pct"]), pct(m["non_english"]["pct"]))
         for m in d["maintenance"]]),
}

# ------------------------------------------------------------------ build
md = TMPL.read_text()
missing = set(re.findall(r"\{\{(\w+)\}\}", md)) - set(VALUES)
if missing:
    raise SystemExit(f"template placeholder with no value: {sorted(missing)}")
for key, value in VALUES.items():
    md = md.replace("{{" + key + "}}", str(value))
OUT_MD.write_text(md)

CHARTS = {
    1: chart_distribution, 2: chart_trend, 3: chart_language_trends,
    4: chart_clock, 5: chart_copies, 6: chart_maintenance,
}
CAPTIONS = {
    1: f'{VALUES["classified"]} distinct skill contents. The '
       f'{VALUES["non_en_pct"]} that are not English are led by Chinese.',
    2: "Band is the 95% Wilson interval. July 2026 is shaded: collection ran "
       "mid-month, so that cohort is censored and excluded from comparisons.",
    3: "Shaded band is the 95% Wilson interval; the hollow final point is the "
       "censored July cohort, plotted but never compared. European groups "
       "German, French, Spanish, Portuguese, Italian, Russian and Dutch.",
    4: "Centre figure is the share of first commits in that window. The "
       "non-English groups are small, so read the contrast, not the decimals.",
    5: f'Across all {VALUES["classified"]} distinct contents. Removing the ten '
       "aggregator repositories, or counting distinct owners, widens the gap.",
    6: "Compared at equal age: among skills at least N days old, the share "
       "revised within their first N days.",
}

body, fm = md, ""
if md.startswith("---"):
    end = md.index("\n---\n", 3)
    fm, body = md[:end + 5], md[end + 5:]

html_body = markdown.markdown(body, extensions=["extra"])


# Figures are held out as tokens while the prose is wrapped, then put back.
# Splitting rendered HTML with a regex looked simpler and was wrong: the
# clock chart contains its own nested elements, so a non-greedy
# <figure>.*?</figure> stopped inside it and left unbalanced divs behind.
figures = {}


def hold_figure(m):
    n = int(m.group(1))
    label = m.group(2).split(":", 1)[-1].strip().rstrip("]").strip()
    token = f"@@FIGURE{n}@@"
    figures[token] = (
        f'<figure>\n  <span class="figlabel">{esc(label)}</span>\n'
        f'  {CHARTS[n]()}\n'
        f'  <figcaption>{CAPTIONS[n]}</figcaption>\n</figure>')
    return token


html_body = re.sub(r"<p><code>\[FIG-(\d+)(.*?)</code></p>", hold_figure, html_body,
                   flags=re.S)
if re.search(r"\[FIG-\d+", html_body):
    raise SystemExit("figure marker not replaced")

# Wrap each run of prose between figure tokens; the tokens sit between the
# wrappers, never inside them, so the div nesting cannot go wrong.
chunks = re.split(r"(@@FIGURE\d+@@)", html_body)
wrapped = "".join(
    c if c in figures else (f'<div class="col">{c}</div>' if c.strip() else c)
    for c in chunks)
for token, html in figures.items():
    wrapped = wrapped.replace(token, html)

# Header comes from the front matter, so the page title and the site's index
# entry can never disagree.
def fm_value(key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    return m.group(1).strip() if m else ""


title, summary = fm_value("title"), fm_value("summary")

# Everything from the credit heading onward becomes the footer. Fail loudly
# if it is not found: str.find returns -1, and quietly splitting at -1 cuts
# the last character off the document, which is how a </div> once shipped
# as "</div" with its ">" stranded after the footer tag.
m = re.search(r"<h2[^>]*>\s*credit\s*</h2>", wrapped, re.I)
if not m:
    raise SystemExit("no credit heading found; the footer split would corrupt the page")
split_at = m.start()
main_html, credit_html = wrapped[:split_at], wrapped[split_at:]
# main_html now ends inside the prose wrapper, so close it
if main_html.count('<div class="col">') > main_html.count("</div>"):
    main_html += "</div>"
credit_html = re.sub(r"</?div class=\"col\">", "", credit_html)
credit_html = credit_html.replace("<h2", '<h3 class="credit-h"').replace("</h2>", "</h3>")

SHELL = (Path(__file__).parent / "_shell.html").read_text()
SHELL = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", SHELL, flags=re.S)

page = f"""{SHELL}<div class="wrap">
<header class="col">
  <div class="eyebrow"><b>Article 01</b><span>·</span><span>The GitSkills series</span>
    <span>·</span><span>Plicara Research</span></div>
  <h1>{esc(title)}</h1>
  <p class="standfirst">{esc(summary)}</p>
</header>
<hr class="rule">

{main_html}

<footer class="col">
{credit_html}
</footer>
</div>
"""

def validate(page):
    """Structural checks on the rendered page, because eyeballing missed these.

    Every fault below shipped at least once. Unbalanced divs came from a
    non-greedy regex splitting nested figures, and a truncated closing tag
    came from str.find returning -1. Neither showed up in a content check:
    the numbers were all correct and traceable while the layout was broken.
    """
    body = page[page.index('<div class="wrap">'):]
    problems = []

    for tag in ("div", "figure"):
        opens = len(re.findall(rf"<{tag}[ >]", body))
        closes = body.count(f"</{tag}>")
        if opens != closes:
            problems.append(f"{tag}: {opens} open against {closes} closed")

    for tag in ("div", "figure", "p", "svg"):
        if re.search(rf"</{tag}(?![>\s])", body):
            problems.append(f"malformed closing </{tag} without '>'")

    if re.search(r"@@FIGURE\d+@@|\{\{\w+\}\}|\[FIG-\d+", body):
        problems.append("an unsubstituted placeholder survived")

    # The dataset is someone else's work, so every time it is named the
    # reader should be one click from the paper. An unlinked mention is a
    # citation that only looks like one.
    prose_start = body.find('<hr class="rule">')
    for m in re.finditer(r"GitSkills", body[prose_start:]):
        at = prose_start + m.start()
        window = body[max(0, at - 260):at + 260]
        if "arxiv.org/abs/2608.10906" not in window:
            problems.append(
                f"GitSkills named without a nearby link to the paper: "
                f"...{re.sub(r'<[^>]+>', '', body[max(0, at-60):at+60])!r}")

    # SVG text that runs past its own viewBox, which is how the language
    # labels ended up printed across their bars.
    for m in re.finditer(r'<svg viewBox="0 0 ([\d.]+) [\d.]+"(.*?)</svg>', body, re.S):
        width = float(m.group(1))
        for t in re.finditer(r"<text ([^>]*)>(.*?)</text>", m.group(2), re.S):
            attrs, inner = t.group(1), t.group(2)
            xm = re.search(r'\bx="([\d.-]+)"', attrs)
            if not xm:
                continue
            am = re.search(r'text-anchor="(\w+)"', attrs)
            x, anchor = float(xm.group(1)), (am.group(1) if am else "start")
            text = re.sub(r"<[^>]+>", "", inner)
            est = len(text) * 9.5  # generous for the sizes in use
            left = x if anchor == "start" else (x - est if anchor == "end" else x - est / 2)
            right = left + est
            if left < -2 or right > width + 2:
                problems.append(
                    f"text {text[:24]!r} spans {left:.0f}..{right:.0f} "
                    f"outside a {width:.0f}-wide viewBox")

    if problems:
        raise SystemExit("page failed validation:\n  " + "\n  ".join(problems[:10]))
    return len(re.findall(r"<figure[ >]", body)), body.count("<table>")


figs, tables = validate(page)
OUT_HTML.write_text(page)
print(f"wrote {OUT_MD}  ({len(md):,} bytes)")
print(f"wrote {OUT_HTML}  ({len(page):,} bytes, {figs} figures, {tables} tables, validated)")


# ---------------------------------------------------------------- site copy
# The site renders markdown with the same extension set and passes raw HTML
# through, so the charts can ship inline rather than as flat images. They are
# restyled against the site's own tokens, including --pl-series-1 and
# --pl-series-2, which exist for exactly this and carry their own light and
# dark values, so the figures theme with the page instead of fighting it.
SITE_STYLE = """<style>
.pl-fig { margin: 2.4rem 0; }
.pl-fig svg { width: 100%; height: auto; display: block; overflow: visible; }
.pl-fig .figlabel { font-family: var(--pl-font-mono); font-size: .68rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--pl-text-muted);
  display: block; margin-bottom: .9rem; }
.pl-fig figcaption { font-family: var(--pl-font-mono); font-size: .74rem;
  line-height: 1.55; color: var(--pl-text-muted); margin-top: .9rem; }
.pl-fig .lbl { font-size: 18px; fill: var(--pl-text); }
.pl-fig .lbl .native { fill: var(--pl-text-muted); }
.pl-fig .val { font-size: 18px; fill: var(--pl-text-muted); font-weight: 500;
  font-variant-numeric: tabular-nums; }
.pl-fig .axis { font-size: 15.5px; fill: var(--pl-text-muted);
  font-variant-numeric: tabular-nums; }
.pl-fig .grid { stroke: var(--pl-rule); stroke-width: 1; }
.pl-fig .ci { fill: var(--pl-series-1); opacity: .18; }
.pl-fig .trendline { fill: none; stroke: var(--pl-series-2); stroke-width: 2.4;
  stroke-linejoin: round; }
.pl-fig .dot { fill: var(--pl-series-2); }
.pl-fig .dot.partial { fill: var(--pl-bg); stroke: var(--pl-series-2); stroke-width: 2; }
.pl-fig .censored { fill: var(--pl-rule); opacity: .35; }
.pl-fig .copybar { fill: var(--pl-series-2); }
.pl-fig .wedge { fill: var(--pl-series-2); opacity: .85; }
.pl-fig .wedge.night { fill: var(--pl-series-1); opacity: .9; }
.pl-fig .dialring { fill: none; stroke: var(--pl-rule); }
.pl-fig .dialpct { font-family: var(--pl-font-mono); font-size: 26px;
  font-weight: 600; fill: var(--pl-text); text-anchor: middle;
  font-variant-numeric: tabular-nums; }
.pl-dials { display: grid; grid-template-columns: repeat(5, 1fr); gap: .7rem; }
.pl-dial-label { text-align: center; margin-top: .35rem; display: grid; gap: .05rem;
  font-family: var(--pl-font-mono); font-size: .58rem; color: var(--pl-text-muted);
  line-height: 1.3; overflow-wrap: anywhere; }
.pl-dial-label strong { color: var(--pl-text); font-size: .66rem; font-weight: 500; }
.pl-panels { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.6rem 1.2rem; }
.pl-panels .axis { font-size: 11px; }
.pl-panel-label { display: flex; justify-content: space-between; align-items: baseline;
  gap: .5rem; margin-top: .2rem; font-family: var(--pl-font-mono); }
.pl-panel-label strong { color: var(--pl-text); font-size: .86rem; font-weight: 600; }
.pl-panel-label .delta { font-size: .7rem; font-weight: 600;
  font-variant-numeric: tabular-nums; white-space: nowrap; }
.pl-panel-label .dwin { font-weight: 400; color: var(--pl-text-muted); font-size: .66rem; }
</style>"""


def site_markdown(md_text):
    """article.md with the figure markers replaced by inline, themed SVG."""
    out = md_text
    for n, chart in CHARTS.items():
        svg = chart()
        # site classes, and the two series colours the site already defines
        svg = (svg.replace('class="dials"', 'class="pl-dials"')
                  .replace('class="dial"', 'class="pl-dial"')
                  .replace('class="dial-label"', 'class="pl-dial-label"')
                  .replace('class="panels"', 'class="pl-panels"')
                  .replace('class="panel"', 'class="pl-panel"')
                  .replace('class="panel-label"', 'class="pl-panel-label"')
                  .replace("var(--c-other)", "var(--pl-series-2)")
                  .replace("var(--c-en)", "var(--pl-series-1)")
                  .replace("var(--ground)", "var(--pl-bg)"))
        marker = re.search(rf"`\[FIG-{n}:(.*?)\]`", out, re.S)
        label = marker.group(1).strip() if marker else ""
        block = (f'<figure class="pl-fig">\n<span class="figlabel">{esc(label)}</span>\n'
                 f'{svg}\n<figcaption>{CAPTIONS[n]}</figcaption>\n</figure>')
        out = re.sub(rf"`\[FIG-{n}:.*?\]`", lambda _: block, out, count=1, flags=re.S)
    left = re.findall(r"\[FIG-\d+", out)
    if left:
        raise SystemExit(f"site copy still has markers: {left}")
    # style block goes after the front matter so the site parses metadata first
    end = out.index("\n---\n", 3) + 5
    return out[:end] + "\n" + SITE_STYLE + "\n" + out[end:]


SITE_OUT = ART / "article.site.md"
SITE_OUT.write_text(site_markdown(md))
print(f"wrote {SITE_OUT}  ({len(SITE_OUT.read_text()):,} bytes, site tokens)")
