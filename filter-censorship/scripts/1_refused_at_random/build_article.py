"""Build the refused-at-random article from one prose source and one number
source, on the same rails as gitskills-analysis.

    article.md.tmpl   holds the prose once, {{placeholders}} where numbers go,
                      `[FIG-N: label]` markers where charts go
    results/figures.json  every number, exported by export_figures.py

Writes three outputs that cannot disagree:
    article.md        the piece, numbers filled, figure markers in place
    preview.html      designed page, charts inline, for reading here
    article.site.md   site copy with themed inline SVG and pl- tokens

    python3 build_article.py
"""
from __future__ import annotations

import json
import re
from html import escape as esc
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
ART = PROJ / "01-refused-at-random"
FIG = json.loads((PROJ / "results" / "1_refused_at_random" / "figures.json").read_text())
OUT_MD = ART / "article.md"
OUT_HTML = ART / "preview.html"

INK, TEAL, RUST, ORANGE = "#05192B", "#31606D", "#6A2A12", "#EE8B33"
PAPER, CREAM, IDLE, RULE = "#FDF5E6", "#FAEBD3", "#E7E2D8", "#C9C2B4"


# ----------------------------------------------------------------- charts
def strip_bar(data, width=1080):
    """One row per group of unit squares; filled squares are blankings."""
    rows, cell, gap_y = [], 14, 26
    H = 30 + len(data) * (cell + gap_y)
    for r, (label, total, blanks) in enumerate(data):
        y = 24 + r * (cell + gap_y)
        rows.append(f'<text x="0" y="{y + cell - 3}" class="rowlab">{esc(label)}</text>')
        for i in range(total):
            x = 250 + i * (cell + 3)
            cls = "b" if i < blanks else "i"
            rows.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" class="{cls}"/>')
        rows.append(f'<text x="{252 + total * (cell + 3)}" y="{y + cell - 3}" class="count">{blanks}/{total}</text>')
    return (f'<svg viewBox="0 0 {width} {H}" class="chart">' +
            "".join(rows) + "</svg>")
def chart_platforms():
    data = [(a["label"], a["calls"], a["blanks"]) for a in FIG["platforms"]]
    return strip_bar(data)


def chart_concentration():
    """Two strips over the same width: study window vs today."""
    n_desc = FIG["sr_descriptions"]
    then_full, then_part = FIG["sr_full_silence"], FIG["sr_partial_desc"]
    now_touched, now_full = FIG["br_touched"], FIG["br_full_silenced"]
    W, cell, gap_y = 900, 13, 30
    rows = []
    H = 40 + 2 * (cell + gap_y)
    per = (W - 260) / n_desc

    def strip(y, full_n, part_n, idle_n):
        out = []
        order = ["f"] * full_n + ["p"] * part_n + ["i"] * idle_n
        for i, k in enumerate(order):
            out.append(f'<rect x="{260 + i * per:.1f}" y="{y}" width="{per - 1.5:.1f}" '
                       f'height="{cell}" rx="1.5" class="{k}"/>')
        return out

    rows.append(f'<text x="0" y="{24 + cell - 3}" class="rowlab">study window</text>')
    rows += strip(24, then_full, then_part, n_desc - then_full - then_part)
    rows.append(f'<text x="0" y="{24 + cell + gap_y + cell - 3}" class="rowlab">today</text>')
    today_idle = 91 - now_touched
    rows += strip(24 + cell + gap_y, now_full, now_touched - now_full, today_idle + (n_desc - 91))
    rows.append(f'<text x="260" y="{H - 4}" class="axis">one square per description · dark: refused on every sample · mid: some samples · pale: never</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="chart">' + "".join(rows) + "</svg>"


def chart_then_now():
    """Two dumbbells on a log scale: refusal rate on identical work, then vs now."""
    pairs = [("sweep tasks\nthat fired", FIG["hist_rate_on_touched"], FIG["f1_opus_rate"]),
             ("blocked\ndescriptions", FIG["br_hist_initial_pct"], FIG["br_opus_rate"])]
    W, row_h = 900, 110
    H = 70 + len(pairs) * row_h
    lo, hi = 1.0, 100.0
    import math
    def x(v):
        return 240 + (math.log10(max(v, lo)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (W - 320)

    out = [f'<line x1="{x(1)}" y1="30" x2="{x(100)}" y2="30" class="axisline"/>']
    for gv in (1, 3, 10, 30, 100):
        out.append(f'<line x1="{x(gv)}" y1="26" x2="{x(gv)}" y2="34" class="tickline"/>'
                   f'<text x="{x(gv)}" y="20" text-anchor="middle" class="tick">{gv}%</text>')
    for r, (label, then, now) in enumerate(pairs):
        cy = 78 + r * row_h
        out.append(f'<text x="0" y="{cy + 4}" class="rowlab">{esc(label).replace(chr(10), "<tspan x=&quot;0&quot; dy='16'>")}</text>'
                   if "\n" not in label else
                   f'<text x="0" y="{cy - 4}" class="rowlab">{esc(label.splitlines()[0])}</text>'
                   f'<text x="0" y="{cy + 14}" class="rowlab">{esc(label.splitlines()[1])}</text>')
        out.append(f'<line x1="{x(now)}" y1="{cy}" x2="{x(then)}" y2="{cy}" class="drop"/>')
        out.append(f'<circle cx="{x(then)}" cy="{cy}" r="7" class="dthen"/>')
        out.append(f'<circle cx="{x(now)}" cy="{cy}" r="7" class="dnow"/>')
        out.append(f'<text x="{x(then)}" y="{cy - 14}" text-anchor="middle" class="val">{then}%</text>')
        out.append(f'<text x="{x(now)}" y="{cy + 24}" text-anchor="middle" class="val">{now}%</text>')
    out.append(f'<text x="{W - 10}" y="78" text-anchor="end" class="legend t">study window</text>')
    out.append(f'<text x="{W - 10}" y="{78 + row_h}" text-anchor="end" class="legend n">today</text>')
    return f'<svg viewBox="0 0 {W} {H}" class="chart">' + "".join(out) + "</svg>"


def chart_bias(width=1080):
    """One labelled row per model, so a reader can tell which dot is which."""
    diffs = sorted(((m["model"].split("/")[-1], m["diff"]) for m in FIG["bias_models"]),
                   key=lambda t: t[1])
    mean, sd = FIG["bias_mean"], FIG["bias_sd"]
    left, top, rowh = 240, 54, 26
    H = top + len(diffs) * rowh + 54
    lo, hi = min(d for _, d in diffs) - 1.5, 1.0
    plot_w = width - left - 90

    def x(v):
        return left + (v - lo) / (hi - lo) * plot_w

    zero = x(0)
    out = [f'<rect x="{x(mean - sd):.1f}" y="{top - 8}" width="{x(mean + sd) - x(mean - sd):.1f}" '
           f'height="{len(diffs) * rowh + 4}" class="band"/>',
           f'<line x1="{x(mean):.1f}" y1="{top - 14}" x2="{x(mean):.1f}" '
           f'y2="{top + len(diffs) * rowh + 6}" class="meanline"/>',
           f'<text x="{x(mean):.1f}" y="{top + len(diffs) * rowh + 30}" text-anchor="middle" '
           f'class="val">mean {mean}, sd {sd}</text>',
           f'<line x1="{zero:.1f}" y1="{top - 14}" x2="{zero:.1f}" '
           f'y2="{top + len(diffs) * rowh + 6}" class="axisline"/>',
           f'<text x="{zero:.1f}" y="{top - 22}" text-anchor="middle" class="tick">no difference</text>']
    for i, (name, d) in enumerate(diffs):
        cy = top + i * rowh + rowh / 2
        out.append(f'<text x="{left - 14}" y="{cy + 5:.1f}" text-anchor="end" '
                   f'class="rowlab">{esc(name)}</text>')
        out.append(f'<line x1="{x(d):.1f}" y1="{cy:.1f}" x2="{zero:.1f}" y2="{cy:.1f}" '
                   f'class="drop"/>')
        out.append(f'<circle cx="{x(d):.1f}" cy="{cy:.1f}" r="6" class="dnow"/>')
        out.append(f'<text x="{x(d) - 13:.1f}" y="{cy + 5:.1f}" text-anchor="end" '
                   f'class="count">{d}</text>')
    out.append(f'<text x="{left + plot_w / 2:.0f}" y="{H - 8}" text-anchor="middle" '
               f'class="axis">percentage points harder than the instances opus was allowed to answer</text>')
    return f'<svg viewBox="0 0 {width} {H}" class="chart">' + "".join(out) + "</svg>"


def chart_leaderboard(width=1080):
    """A rank ladder: one column per treatment, the subject's slot joined across.

    The earlier version drew three sorted bar lists side by side, which made
    a reader match names across columns that were ordered differently. Here
    the only thing that moves is the filled marker.
    """
    board = [(b["model"], b["score"]) for b in FIG["board"]]
    subject = "claude-opus-5"
    cols = [("drop the blanks", FIG["score_drop"], FIG["rank_drop"]),
            ("count them wrong", FIG["score_countwrong"], FIG["rank_countwrong"]),
            ("corrected", FIG["score_corrected"], FIG["rank_corrected"])]
    n = len(board) + 1
    left, top, rowh = 74, 74, 30
    H = top + n * rowh + 34
    span = width - left - 90
    xs = [left + span * (i + 0.5) / len(cols) for i in range(len(cols))]
    tick = span / len(cols) * 0.28

    out = []
    for r in range(1, n + 1):
        y = top + (r - 1) * rowh + rowh / 2
        out.append(f'<text x="{left - 18}" y="{y + 5:.1f}" text-anchor="end" '
                   f'class="tick">{r}</text>')
    out.append(f'<text x="{left - 18}" y="{top - 26}" text-anchor="end" '
               f'class="axis">rank</text>')

    marks = []
    for c, (name, score, rank) in enumerate(cols):
        cx = xs[c]
        out.append(f'<text x="{cx:.0f}" y="{top - 26}" text-anchor="middle" '
                   f'class="axis">{esc(name)}</text>')
        ordered = sorted(board + [(subject, score)], key=lambda t: -t[1])
        for i, (m, sc) in enumerate(ordered):
            y = top + i * rowh + rowh / 2
            if m == subject:
                marks.append((cx, y, sc, rank))
                continue
            out.append(f'<line x1="{cx - tick:.1f}" y1="{y:.1f}" x2="{cx + tick:.1f}" '
                       f'y2="{y:.1f}" stroke="{IDLE}" stroke-width="7" stroke-linecap="round"/>')
    # The subject last, so it sits above every neutral tick.
    out.append('<polyline points="' +
               " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy, _, _ in marks) +
               f'" fill="none" stroke="{RUST}" stroke-width="2" stroke-dasharray="5 4"/>')
    for cx, cy, sc, rank in marks:
        out.append(f'<line x1="{cx - tick:.1f}" y1="{cy:.1f}" x2="{cx + tick:.1f}" '
                   f'y2="{cy:.1f}" stroke="{RUST}" stroke-width="9" stroke-linecap="round"/>')
        out.append(f'<text x="{cx + tick + 10:.1f}" y="{cy + 5:.1f}" '
                   f'class="count">{sc}</text>')
    out.append(f'<text x="{left}" y="{H - 8}" class="axis">'
               f'{esc(subject)} in rust, the other ten models in grey, one row per rank</text>')
    return f'<svg viewBox="0 0 {width} {H}" class="chart">' + "".join(out) + "</svg>"


def chart_detection(width=1080):
    """Chance k samples catch the filter on one affected task."""
    det = FIG["detection"]
    ks, H, left, top = det["k"], 360, 64, 54
    plot_w, plot_h = width - left - 40, H - top - 62

    def pt(i, v):
        return (left + plot_w * i / (len(ks) - 1), top + plot_h * (1 - v / 100))

    out = []
    for gv in (0, 25, 50, 75, 100):
        y = top + plot_h * (1 - gv / 100)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                   f'stroke="{RULE}" stroke-width="1"/>')
        out.append(f'<text x="{left - 10}" y="{y + 4:.1f}" class="tick" '
                   f'text-anchor="end">{gv}%</text>')
    for k in ks:
        xk = left + plot_w * (k - 1) / (len(ks) - 1)
        out.append(f'<text x="{xk:.1f}" y="{top + plot_h + 24:.0f}" class="tick" '
                   f'text-anchor="middle">{k}</text>')
    out.append(f'<text x="{left + plot_w / 2:.0f}" y="{H - 10}" class="axis" '
               f'text-anchor="middle">samples per task (k)</text>')
    # Labels sit above their own curve inside the plot, so nothing overflows.
    for key, colour, label, anchor_i in (
            ("study", RUST, f'during the study, {det["study_rate_pct"]}% per call', 4),
            ("today", TEAL, f'today, {det["today_rate_pct"]}% per call', 6)):
        pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in (pt(i, v) for i, v in enumerate(det[key])))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
        lx, ly = pt(anchor_i, det[key][anchor_i])
        dy = -16 if key == "study" else 26
        out.append(f'<text x="{lx:.0f}" y="{ly + dy:.0f}" class="legend" text-anchor="middle" '
                   f'style="fill:{colour};font-size:14px">{esc(label)}</text>')
        for i in (0, 2):
            px, py = pt(i, det[key][i])
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{colour}"/>')
            out.append(f'<text x="{px + 12:.0f}" y="{py + 4:.0f}" class="count" '
                       f'text-anchor="start">{det[key][i]}%</text>')
    return f'<svg viewBox="0 0 {width} {H}" class="chart">' + "".join(out) + "</svg>"


CHARTS = {
    1: chart_leaderboard,   # what the handling choice did to the result
    2: chart_bias,          # the skew the blanks leave behind
    3: chart_detection,     # why k>1 is the instrument
    4: chart_concentration, # which tasks, and how completely
    5: chart_then_now,      # the dial moved under us
    6: chart_platforms,     # and it moved with the weights
}

CAPTIONS = {
    1: f'The same model, the same answers, the same corpus. Only the handling of '
       f'{FIG["sr_filter_blanks"]} blanked calls differs. Filled bar is claude-opus-5.',
    3: f'Chance that k samples of one affected task show the filter at least once, '
       f'at the per-call rate we measured then and the rate it runs at now.',
    4: f'Every StructuredRegex description the filter touched, by what it did to them. '
       f'Then: {FIG["sr_touched_desc"]} descriptions. Now: {FIG["br_touched"]}.',
    2: f'One row per model, none of them the filtered one. For each, we scored the '
       f'{FIG["sr_filter_blanks"]} instances the filter blanked for opus and the '
       f'{FIG["sr_scored"]} it did not, then plotted the gap between those two pass rates. '
       f'A dot left of the zero line means that model also found the blanked instances '
       f'harder. The orange band is the mean of the ten, plus or minus one standard deviation.',
    5: "Refusal rate on identical prompts, study window versus today. Log scale.",
    6: f'{FIG["upstream_calls_per_platform"]} calls per hosting platform, one square each. '
       f'Blanks on {FIG["upstream_platforms_with_blanks"]} of {FIG["upstream_platforms"]}; the clean arm is '
       f'underpowered, not exempt.',
}


def main():
    md = (ART / "article.md.tmpl").read_text()
    values = {k: v for k, v in FIG.items() if not isinstance(v, (list, dict))}
    for key, value in values.items():
        md = md.replace("{{" + key + "}}", str(value))
    # A placeholder that survives substitution means the prose is citing a
    # number the export does not have. Fail here rather than publish the
    # literal braces, and never let a figure be quietly hand-typed instead.
    leftover = sorted(set(re.findall(r"\{\{([a-z0-9_]+)\}\}", md)))
    if leftover:
        raise SystemExit("unresolved placeholders in article.md.tmpl: "
                         + ", ".join(leftover))
    OUT_MD.write_text(md)
    print(f"wrote {OUT_MD}")

    # preview.html ------------------------------------------------------
    fm = md.split("---")[1]
    title = re.search(r"^title:\s*(.+)$", fm, re.M).group(1).strip()
    summary = re.search(r"^summary:\s*(.+)$", fm, re.M).group(1).strip()

    body_html = _markdownish(md)
    figures, tokens = {}, {}
    for n in CHARTS:
        tokens[n] = f"@@FIGURE{n}@@"
    for n, token in tokens.items():
        body_html = re.sub(rf"(<p>)?<code>\[FIG-{n}:.*?\]</code>(</p>)?", token,
                           body_html, flags=re.S)
    parts = re.split(r"(@@FIGURE\d+@@)", body_html)
    wrapped = "".join(
        p if p.startswith("@@") else f'<div class="col">{p}</div>' for p in parts)
    for n, token in tokens.items():
        svg = CHARTS[n]()
        fig = (f'<figure><span class="figlabel">{esc(CAPTIONS[n])}</span>{svg}</figure>')
        wrapped = wrapped.replace(token, fig)
    if "@@FIGURE" in wrapped or "[FIG-" in wrapped:
        raise SystemExit("figure marker survived rendering")

    page = (SHELL.replace("@title@", esc(title)).replace("@summary@", esc(summary))
            .replace("@body@", wrapped)
            .replace("@ink@", INK).replace("@paper@", PAPER).replace("@teal@", TEAL)
            .replace("@rust@", RUST).replace("@orange@", ORANGE)
            .replace("@idle@", IDLE).replace("@rule@", RULE))
    OUT_HTML.write_text(page)
    print(f"wrote {OUT_HTML}")

    # article.site.md ----------------------------------------------------
    site = md
    for n, chart in CHARTS.items():
        svg = chart()
        svg = (svg.replace("var(--ink)", "var(--pl-text)")
                  .replace('class="chart"', 'class="pl-chart"'))
        marker = re.search(rf"`\[FIG-{n}:.*?\]`", site, re.S)
        block = (f'<figure class="pl-fig">\n{svg}\n'
                 f'<figcaption>{esc(CAPTIONS[n])}</figcaption>\n</figure>')
        site = re.sub(rf"`\[FIG-{n}:.*?\]`", lambda _: block, site, count=1, flags=re.S)
    style = ("<style>.pl-fig{margin:2rem 0}.pl-chart{width:100%;height:auto}"
             ".pl-chart .rowlab,.pl-chart .val,.pl-chart .tick,.pl-chart .axis,"
             ".pl-chart .legend{font-family:var(--pl-font-mono,monospace);fill:var(--pl-text-muted,#666)}"
             ".pl-chart .b{fill:var(--pl-series-2,#B3402A)}.pl-chart .i{fill:var(--pl-series-1,#31606D);opacity:.25}"
             ".pl-chart .p{fill:var(--pl-series-1,#31606D);opacity:.55}"
             ".pl-chart .f{fill:#B3402A}.pl-chart .drop{stroke:#B3402A;stroke-width:2}"
             ".pl-chart .dnow{fill:#31606D}.pl-chart .dthen{fill:#B3402A}"
             ".pl-chart .axisline,.pl-chart .tickline{stroke:#999}.pl-chart .meanline{stroke:#EE8B33;stroke-width:2}"
             ".pl-chart .band{fill:#EE8B33;opacity:.15}</style>")
    # The style block goes after the front matter, never inside it: the site
    # parses front matter as key: value lines between two --- fences, and a
    # raw <style> line in there is not one of those.
    head, sep, rest = site.partition("\n---\n")
    if not sep:
        raise SystemExit("article.site.md: no closing front-matter fence")
    site = head + sep + style + "\n" + rest

    # Prove the front matter still parses the way the site needs it to,
    # because this file is what ships and nothing downstream checks it.
    fm_lines = site.split("\n---\n")[0].lstrip("-\n").splitlines()
    bad = [l for l in fm_lines if l.strip() and not re.match(r"^[a-z_]+:\s*\S", l)]
    if bad:
        raise SystemExit(f"article.site.md front matter has non key: value lines: {bad}")
    for required in ("title", "date", "summary"):
        if not any(l.startswith(required + ":") for l in fm_lines):
            raise SystemExit(f"article.site.md front matter missing '{required}'")
    (ART / "article.site.md").write_text(site)
    print(f"wrote {ART / 'article.site.md'}")


def _markdownish(md):
    """Tiny renderer for exactly the constructs this article uses."""
    body = md.split("---", 2)[2].strip()
    body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", body, flags=re.M)
    body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=re.M)
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)
    body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  rf'<a href="\2">\1</a>', body)
    blocks, para = [], []
    table_buf = []
    for line in body.splitlines() + [""]:
        s = line.strip()
        if s.startswith("|"):
            table_buf.append(s)
            continue
        if table_buf:
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in table_buf
                     if not re.match(r"^\|[\s:-]+\|", r)]
            head, *rows = cells
            t = "<table><tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>"
            for row in rows:
                t += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            blocks.append(t + "</table>")
            table_buf = []
        if not s:
            if para:
                blocks.append("<p>" + " ".join(para) + "</p>")
                para = []
        elif s.startswith(("#", "<")) or s.startswith("`[FIG-"):
            blocks.append(s if s.startswith("<") else f"<p><code>{s[1:-1]}</code></p>")
        else:
            para.append(s)
    return "\n".join(blocks)


SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@title@</title>
<style>
:root{--ink:@ink@;--paper:@paper@;--teal:@teal@;--rust:@rust@;--orange:@orange@;--idle:@idle@;--rule:@rule@}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:'Newsreader',Georgia,'Times New Roman',serif;font-size:19px;line-height:1.62}
main{max-width:720px;margin:0 auto;padding:64px 20px 120px}
h1{font-size:44px;line-height:1.12;margin:0 0 12px;font-weight:600;letter-spacing:-.01em}
.summary{font-size:22px;color:#5A5548;margin:0 0 40px;font-style:italic}
h2{font-size:27px;margin:56px 0 12px;font-weight:600}
p{margin:0 0 22px}
code{font-family:ui-monospace,Menlo,monospace;font-size:.82em;background:var(--cream);padding:1px 5px;border-radius:4px}
a{color:var(--teal)}
table{border-collapse:collapse;width:100%;margin:0 0 26px;font-size:16px}
th,td{padding:7px 10px;border-bottom:1px solid var(--rule);text-align:left}
th{font-family:ui-monospace,Menlo,monospace;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#6b6355}
figure{margin:34px 0}
.figlabel{display:block;font-family:ui-monospace,Menlo,monospace;font-size:13px;
 letter-spacing:.02em;color:#6b6355;margin-bottom:10px}
svg.chart{width:100%;height:auto;display:block}
.rowlab{font-family:ui-monospace,Menlo,monospace;font-size:14px;fill:var(--ink)}
.count{font-family:ui-monospace,Menlo,monospace;font-size:13px;fill:#6b6355}
.axis{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;fill:#6b6355}
.tick,.val,.legend{font-family:ui-monospace,Menlo,monospace;font-size:14px;fill:var(--ink)}
.legend.t{fill:var(--rust)}.legend.n{fill:var(--teal)}
.b{fill:var(--rust)}.i{fill:var(--teal);opacity:.18}.p{fill:var(--teal);opacity:.55}.f{fill:var(--rust)}
.axisline,.tickline{stroke:#9a938a;stroke-width:1.5}
.drop{stroke:var(--rust);stroke-width:2}
.dthen{fill:var(--rust)}.dnow{fill:var(--teal)}
.meanline{stroke:var(--orange);stroke-width:2}.band{fill:var(--orange);opacity:.18}
.credit{margin-top:64px;font-size:15px;color:#6b6355}
</style></head><body><main>
<h1>@title@</h1><p class="summary">@summary@</p>
@body@
<p class="credit">Plicara Labs · analysis code and machine-readable exports are public.</p>
</main></body></html>"""


if __name__ == "__main__":
    main()
