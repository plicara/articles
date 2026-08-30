"""The eight figures for article 02, as inline SVG.

Separate from build_article.py so the charts can be rendered and eyeballed on
their own, which is the last step of the design procedure and the one that
catches what a colour validator cannot: label collisions, overflow, geometry.

Local colour names are rewritten to the site's tokens when the article ships:

    --c-subject  ->  --pl-series-2   the series carrying the claim
    --c-compare  ->  --pl-series-1   the comparison, and CI bands at 18%
    --ground     ->  --pl-bg

Everything else is text, muted text or rule. No figure introduces a colour,
because the site only defines two series colours and every finding here is a
single-series magnitude or a two-value comparison.
"""

import json
import math
from pathlib import Path

FIG = json.loads(
    (Path(__file__).resolve().parents[2] / "results" / "figures_02.json").read_text())


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap(body, w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'{body}\n</svg>')


# --------------------------------------------------------------- FIG-1
def fig_composition():
    """A unit chart: how many skills in a hundred ship any code."""
    ships = FIG["ships_code"]["nonroot"]["pct"]
    filled = round(ships)
    cell, gap, cols = 30, 7, 10
    grid_w = cols * (cell + gap) - gap
    sq = []
    for i in range(100):
        r, c = divmod(i, cols)
        x, y = c * (cell + gap), r * (cell + gap)
        on = i < filled
        sq.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
                  f'fill="{"var(--c-subject)" if on else "var(--pl-rule)"}"'
                  f'{"" if on else ' opacity=".55"'}/>')
    grid_h = 10 * (cell + gap) - gap

    tx = grid_w + 66
    text = (
        f'<text x="{tx}" y="52" class="huge">{filled}</text>'
        f'<text x="{tx}" y="92" class="lbl">in every 100 skills</text>'
        f'<text x="{tx}" y="118" class="lbl">ship any code at all</text>'
        f'<text x="{tx}" y="168" class="axis">The other {100 - filled} are prose:</text>'
        f'<text x="{tx}" y="192" class="axis">instructions for a model,</text>'
        f'<text x="{tx}" y="216" class="axis">with nothing to execute.</text>')

    # the stacked bar of what bundled files actually are
    y0 = grid_h + 62
    kinds = FIG["composition_files"]["kinds"]
    total = FIG["composition_files"]["total"]
    bar_w, bar_h, x = 900, 46, 0.0
    segs, labs = [], []
    for k in kinds:
        w = bar_w * k["n"] / total
        segs.append(f'<rect x="{x:.1f}" y="{y0}" width="{max(0.0, w - 2):.1f}" '
                    f'height="{bar_h}" rx="2" '
                    f'fill="{"var(--c-subject)" if k["kind"] in ("docs", "code") else "var(--pl-rule)"}"'
                    f'{"" if k["kind"] == "docs" else ' opacity=".72"' if k["kind"] == "code" else ' opacity=".5"'}/>')
        if w > 90:
            on_fill = k["kind"] in ("docs", "code")
            labs.append(
                f'<text x="{x + 14:.1f}" y="{y0 + 29}" '
                f'class="onbar{"" if on_fill else " off"}">{esc(k["kind"])}'
                f'  {k["pct"]}%</text>')
        x += w
    head = (f'<text x="0" y="{y0 - 18}" class="axis">'
            f'and of the {total:,} files they do bundle</text>')
    return _wrap("".join(sq) + text + head + "".join(segs) + "".join(labs),
                 900, y0 + bar_h + 16,
                 "Twelve skills in a hundred ship code; half of all bundled "
                 "files are documentation")


# --------------------------------------------------------------- FIG-2
def fig_repo_language():
    """Dumbbell: the repository's own language against what its skills ship."""
    rows = FIG["repo_language"]
    h, top = 30, 76
    L, R = 178, 858            # plot area
    def x(pct):
        return L + (R - L) * pct / 100.0

    out = []
    for i, r in enumerate(rows):
        y = top + i * h + h / 2
        a, b = x(r["ships_python"]), x(r["ships_own"])
        out.append(
            f'<line x1="{min(a, b):.1f}" y1="{y:.1f}" x2="{max(a, b):.1f}" y2="{y:.1f}" '
            f'class="connector"/>'
            f'<circle cx="{a:.1f}" cy="{y:.1f}" r="6" fill="var(--c-compare)"/>'
            f'<circle cx="{b:.1f}" cy="{y:.1f}" r="6" fill="var(--c-subject)"/>'
            f'<text x="{L - 16}" y="{y + 6:.1f}" class="lbl" text-anchor="end">'
            f'{esc(r["lang"])}</text>')
        # direct labels only on the rows that carry the argument
        if r["lang"] in ("Shell/Bash", "Python", "Rust", "C/C++"):
            out.append(
                f'<text x="{b + 14:.1f}" y="{y + 5:.1f}" class="val">'
                f'{r["ships_own"]:.0f}%</text>')
    grid = "".join(
        f'<line x1="{x(v):.1f}" y1="{top - 10}" x2="{x(v):.1f}" '
        f'y2="{top + len(rows) * h + 4}" class="grid"/>'
        f'<text x="{x(v):.1f}" y="{top - 18}" class="axis" text-anchor="middle">{v}%</text>'
        for v in (0, 20, 40, 60, 80))
    key = (f'<circle cx="{L}" cy="16" r="6" fill="var(--c-subject)"/>'
           f'<text x="{L + 14}" y="21" class="axis">ships its own language</text>'
           f'<circle cx="{L + 250}" cy="16" r="6" fill="var(--c-compare)"/>'
           f'<text x="{L + 264}" y="21" class="axis">ships Python</text>')
    return _wrap(key + grid + "".join(out), 900, top + len(rows) * h + 18,
                 "Share of a repository's code-shipping skills written in the "
                 "repository's own language, against Python")


# --------------------------------------------------------------- FIG-3
def fig_typescript():
    """TypeScript's share of new skills, with the Octoverse fact annotated."""
    pts = FIG["over_time"]["series"]["TypeScript"]
    W, H, PAD_L, PAD_T, PAD_B = 900, 320, 52, 74, 40
    hi_y = 2.4
    n = len(pts)
    def X(i):
        return PAD_L + i * (W - PAD_L - 30) / (n - 1)
    def Y(v):
        return PAD_T + (1 - v / hi_y) * (H - PAD_T - PAD_B)

    band = ([f"{X(i):.1f},{Y(p['hi']):.1f}" for i, p in enumerate(pts)]
            + [f"{X(i):.1f},{Y(pts[i]['lo']):.1f}" for i in range(n - 1, -1, -1)])
    line = " ".join(f"{X(i):.1f},{Y(p['pct']):.1f}" for i, p in enumerate(pts))
    grid = "".join(
        f'<line x1="{PAD_L}" y1="{Y(v):.1f}" x2="{W - 30}" y2="{Y(v):.1f}" class="grid"/>'
        f'<text x="{PAD_L - 10}" y="{Y(v) + 5:.1f}" class="axis" text-anchor="end">'
        f'{v}%</text>' for v in (0, 0.8, 1.6, 2.4))
    ticks = "".join(
        f'<text x="{X(i):.1f}" y="{H - 14}" class="axis" text-anchor="'
        f'{"start" if i == 0 else "end" if i == n - 1 else "middle"}">'
        f'{p["q"]}</text>' for i, p in enumerate(pts))
    dots = "".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(p["pct"]):.1f}" r="{3 if i == n - 1 else 4.5}" '
        f'class="{"dot partial" if i == n - 1 else "dot"}"/>'
        for i, p in enumerate(pts))
    shade = (f'<rect x="{X(n - 1) - 16:.1f}" y="{PAD_T}" '
             f'width="{W - 30 - X(n - 1) + 16:.1f}" height="{H - PAD_T - PAD_B}" '
             f'class="censored"/>')
    ann = (f'<line x1="{PAD_L}" y1="34" x2="{W - 30}" y2="34" class="annrule"/>'
           f'<text x="{PAD_L}" y="18" class="ann">Meanwhile on GitHub, TypeScript grew '
           f'66% in a year to become the most used language</text>'
           f'<text x="{PAD_L}" y="52" class="ann">Octoverse 2025</text>')
    first, last = pts[0], pts[-2]
    lab = (f'<text x="{X(0) + 10:.1f}" y="{Y(first["pct"]) - 12:.1f}" class="val">'
           f'{first["pct"]}%</text>'
           f'<text x="{X(n - 2):.1f}" y="{Y(last["pct"]) - 14:.1f}" class="val" '
           f'text-anchor="middle">{last["pct"]}%</text>'
           f'<text x="{X(n - 1):.1f}" y="{H - 30}" class="axis" text-anchor="end">'
           f'censored</text>')
    return _wrap(ann + grid + shade + f'<polygon points="{" ".join(band)}" class="ci"/>'
                 + f'<polyline points="{line}" class="trendline"/>' + dots + ticks + lab,
                 W, H, "TypeScript's share of newly created skills, by quarter")


# --------------------------------------------------------------- FIG-4
def fig_ratio():
    """The mention-to-ship ratio climbing, with Python flat as the control."""
    ts = FIG["over_time"]["series"]["TypeScript"]
    py = FIG["over_time"]["series"]["Python"]
    W, H, PAD_L, PAD_T, PAD_B = 900, 280, 52, 34, 40
    RIGHT = 210
    hi_y = 36
    n = len(ts)
    def X(i):
        return PAD_L + i * (W - PAD_L - 80) / (n - 1)
    def Y(v):
        return PAD_T + (1 - v / hi_y) * (H - PAD_T - PAD_B)

    grid = "".join(
        f'<line x1="{PAD_L}" y1="{Y(v):.1f}" x2="{W - 80}" y2="{Y(v):.1f}" class="grid"/>'
        f'<text x="{PAD_L - 10}" y="{Y(v) + 5:.1f}" class="axis" text-anchor="end">'
        f'{v}x</text>' for v in (0, 12, 24, 36))
    tsl = " ".join(f"{X(i):.1f},{Y(p['ratio'] or 0):.1f}" for i, p in enumerate(ts))
    pyl = " ".join(f"{X(i):.1f},{Y(p['ratio'] or 0):.1f}" for i, p in enumerate(py))
    ticks = "".join(
        f'<text x="{X(i):.1f}" y="{H - 14}" class="axis" text-anchor="'
        f'{"start" if i == 0 else "middle"}">{p["q"]}</text>'
        for i, p in enumerate(ts))
    dots = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(p["ratio"] or 0):.1f}" r="4.5" '
                   f'class="dot"/>' for i, p in enumerate(ts))
    ends = (f'<text x="{X(0) + 12:.1f}" y="{Y(ts[0]["ratio"]) - 12:.1f}" class="val">'
            f'{ts[0]["ratio"]}x</text>'
            f'<text x="{X(n - 1) + 14:.1f}" y="{Y(ts[-1]["ratio"]) + 1:.1f}" '
            f'class="val">{ts[-1]["ratio"]}x</text>'
            f'<text x="{X(n - 1) + 14:.1f}" y="{Y(ts[-1]["ratio"]) + 19:.1f}" '
            f'class="axis">TypeScript</text>'
            f'<text x="{X(n - 1) + 14:.1f}" y="{Y(py[-1]["ratio"]) + 1:.1f}" '
            f'class="val">{py[-1]["ratio"]}x</text>'
            f'<text x="{X(n - 1) + 14:.1f}" y="{Y(py[-1]["ratio"]) + 19:.1f}" '
            f'class="axis">Python</text>')
    return _wrap(grid + f'<polyline points="{pyl}" class="control"/>'
                 + f'<polyline points="{tsl}" class="trendline"/>' + dots + ticks + ends,
                 W, H, "Mention-to-ship ratio by quarter, TypeScript against Python")


# --------------------------------------------------------------- FIG-5
def fig_gap():
    """Log dot plot of mention-to-ship ratio, one row per language."""
    ranked = [r for r in FIG["mention_vs_ship"] if r["ratio"]]
    rows = ranked[:14]
    # Python is the anchor every other row is read against and has the lowest
    # ratio of all, so sorting by ratio and taking the head drops exactly the
    # row that gives the figure its meaning. Pin it.
    if not any(r["lang"] == "Python" for r in rows):
        py = next((r for r in ranked if r["lang"] == "Python"), None)
        if py:
            rows = rows + [py]
    h, top = 26, 40
    L, R = 150, 840
    lo, hi = 1.0, 100.0
    def X(v):
        v = max(lo, min(hi, v))
        return L + (R - L) * (math.log10(v) - math.log10(lo)) / (
            math.log10(hi) - math.log10(lo))

    grid = "".join(
        f'<line x1="{X(v):.1f}" y1="{top - 12}" x2="{X(v):.1f}" '
        f'y2="{top + len(rows) * h}" class="grid"/>'
        f'<text x="{X(v):.1f}" y="{top - 20}" class="axis" text-anchor="middle">'
        f'{v:g}x</text>' for v in (1, 3, 10, 30, 100))
    out = []
    for i, r in enumerate(rows):
        y = top + i * h + h / 2
        out.append(
            f'<line x1="{X(1):.1f}" y1="{y:.1f}" x2="{X(r["ratio"]):.1f}" y2="{y:.1f}" '
            f'class="connector"/>'
            f'<circle cx="{X(r["ratio"]):.1f}" cy="{y:.1f}" r="5.5" '
            f'fill="var(--c-subject)"/>'
            f'<text x="{L - 14}" y="{y + 5:.1f}" class="lbl" text-anchor="end">'
            f'{esc(r["lang"])}</text>')
        if r["lang"] in ("Python", "TypeScript", "Kotlin"):
            out.append(f'<text x="{X(r["ratio"]) + 12:.1f}" y="{y + 5:.1f}" '
                       f'class="val">{r["ratio"]:g}x</text>')
    return _wrap(grid + "".join(out), 900, top + len(rows) * h + 14,
                 "How many times more often each language is mentioned than shipped")


# --------------------------------------------------------------- FIG-6
def fig_written_language():
    """Dot plot with Wilson whiskers, owners as the denominator."""
    rows = FIG["by_written_language"]
    h, top = 46, 44
    L, R = 210, 830
    hi_x = 50
    def X(v):
        return L + (R - L) * v / hi_x

    en = next(r for r in rows if r["group"] == "English")
    grid = "".join(
        f'<line x1="{X(v):.1f}" y1="{top - 12}" x2="{X(v):.1f}" '
        f'y2="{top + len(rows) * h}" class="grid"/>'
        f'<text x="{X(v):.1f}" y="{top - 20}" class="axis" text-anchor="middle">{v}%</text>'
        for v in (0, 10, 20, 30, 40, 50))
    ref = (f'<line x1="{X(en["pct"]):.1f}" y1="{top - 12}" x2="{X(en["pct"]):.1f}" '
           f'y2="{top + len(rows) * h}" class="refline"/>')
    out = []
    for i, r in enumerate(rows):
        y = top + i * h + h / 2
        out.append(
            f'<line x1="{X(r["lo"]):.1f}" y1="{y:.1f}" x2="{X(r["hi"]):.1f}" '
            f'y2="{y:.1f}" class="whisker"/>'
            f'<circle cx="{X(r["pct"]):.1f}" cy="{y:.1f}" r="6" '
            f'fill="var(--c-subject)"/>'
            f'<text x="{L - 16}" y="{y + 5:.1f}" class="lbl" text-anchor="end">'
            f'{esc(r["group"])}</text>'
            f'<text x="{X(r["hi"]) + 14:.1f}" y="{y + 5:.1f}" class="val">'
            f'{r["pct"]:.0f}%</text>'
            f'<text x="{L - 16}" y="{y + 19:.1f}" class="sub" text-anchor="end">'
            f'{r["n"]:,} owners</text>')
    lab = (f'<text x="{X(en["pct"]):.1f}" y="{top + len(rows) * h + 22:.1f}" '
           f'class="axis" text-anchor="middle">English rate</text>')
    return _wrap(grid + ref + "".join(out) + lab, 900,
                 top + len(rows) * h + 34,
                 "Share of repository owners who ship code in a skill, by the "
                 "language the skill is written in")


# --------------------------------------------------------------- FIG-7
def fig_reuse():
    """Paired bars: shipping code and bundling anything, by how widely copied."""
    rows = FIG["reuse"]
    W, H, PAD_L, PAD_T, PAD_B = 900, 300, 52, 46, 56
    hi_y = 56
    group_w = (W - PAD_L - 40) / len(rows)
    bw = 54
    def Y(v):
        return PAD_T + (1 - v / hi_y) * (H - PAD_T - PAD_B)

    grid = "".join(
        f'<line x1="{PAD_L}" y1="{Y(v):.1f}" x2="{W - 40}" y2="{Y(v):.1f}" class="grid"/>'
        f'<text x="{PAD_L - 10}" y="{Y(v) + 5:.1f}" class="axis" text-anchor="end">'
        f'{v}%</text>' for v in (0, 14, 28, 42, 56))
    out = []
    for i, r in enumerate(rows):
        cx = PAD_L + group_w * (i + 0.5)
        for j, (key, fill, op) in enumerate(
                [("ships", "var(--c-subject)", "1"), ("bundles", "var(--c-compare)", ".85")]):
            v = r[key]["pct"]
            x = cx - bw - 4 + j * (bw + 8)
            out.append(
                f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw}" '
                f'height="{Y(0) - Y(v):.1f}" rx="4" fill="{fill}" opacity="{op}"/>'
                f'<text x="{x + bw / 2:.1f}" y="{Y(v) - 9:.1f}" class="val" '
                f'text-anchor="middle">{v:.0f}%</text>')
        out.append(f'<text x="{cx:.1f}" y="{H - 30}" class="axis" '
                   f'text-anchor="middle">{esc(r["bucket"])}</text>')
    axis = (f'<text x="{(PAD_L + W - 40) / 2:.1f}" y="{H - 8}" class="axis" '
            f'text-anchor="middle">distinct repository owners holding a copy</text>')
    key = (f'<rect x="{PAD_L}" y="10" width="12" height="12" rx="2" '
           f'fill="var(--c-subject)"/>'
           f'<text x="{PAD_L + 20}" y="21" class="axis">ships code</text>'
           f'<rect x="{PAD_L + 130}" y="10" width="12" height="12" rx="2" '
           f'fill="var(--c-compare)" opacity=".85"/>'
           f'<text x="{PAD_L + 150}" y="21" class="axis">bundles anything</text>')
    return _wrap(key + grid + "".join(out) + axis, W, H,
                 "Share of skills that ship code, by how many owners hold a copy")


# --------------------------------------------------------------- FIG-8
def fig_spec_layout():
    """One bar: the three directories the spec names, against everywhere else."""
    rows = {r["place"]: r for r in FIG["spec_layout"]["rows"]}
    order = ["references/", "scripts/", "assets/",
             "other subdirectory", "loose beside SKILL.md"]
    total = FIG["spec_layout"]["total"]
    W, bar_h, y0 = 900, 54, 52
    x = 0.0
    segs, labs = [], []
    named = 0.0
    for place in order:
        r = rows[place]
        w = W * r["n"] / total
        in_spec = place in ("references/", "scripts/", "assets/")
        named += r["pct"] if in_spec else 0
        segs.append(
            f'<rect x="{x:.1f}" y="{y0}" width="{max(0.0, w - 2):.1f}" height="{bar_h}" '
            f'rx="2" fill="{"var(--c-subject)" if in_spec else "var(--pl-rule)"}"'
            f'{"" if in_spec else ' opacity=".55"'}/>')
        # roughly 8.4px per monospace character at 15px; a label that will not
        # fit inside its own segment is dropped rather than allowed to overflow
        if w > max(78, 8.4 * len(place) + 26):
            off = "" if in_spec else " off"
            labs.append(f'<text x="{x + 12:.1f}" y="{y0 + 23}" class="onbar{off}">'
                        f'{esc(place)}</text>'
                        f'<text x="{x + 12:.1f}" y="{y0 + 42}" class="onbar sm{off}">'
                        f'{r["pct"]}%</text>')
        x += w
    brace_w = W * named / 100
    head = (f'<line x1="0" y1="{y0 - 16}" x2="{brace_w - 2:.1f}" y2="{y0 - 16}" '
            f'class="annrule"/>'
            f'<text x="0" y="{y0 - 26}" class="ann">the three directories the '
            f'specification names: {named:.0f}% of files</text>')
    return _wrap(head + "".join(segs) + "".join(labs), W, y0 + bar_h + 16,
                 "Where bundled files sit, against the layout the specification "
                 "defines")


CHARTS = {1: fig_composition, 2: fig_repo_language, 3: fig_typescript,
          4: fig_ratio, 5: fig_gap, 6: fig_written_language, 7: fig_reuse,
          8: fig_spec_layout}
