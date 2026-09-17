"""Build the Jev article from one prose source and one number source.

    article.md.tmpl   hand prose, {{placeholders}}, [FIG-N: label] markers
    results/figures.json  every number (see scripts/jev_decisions/export_figures.py)

Writes three outputs that cannot disagree:
    article.md        numbers filled, figure markers in place (review target)
    article.site.md   markers replaced by themed inline SVG (ships to site)
    preview.html      designed page for reading here (ships nowhere)

    python3 build_article.py
"""
from __future__ import annotations

import json
import re
from html import escape as esc
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
ART = PROJ / "01-jev-decisions"
FIG = json.loads((PROJ / "results" / "jev_decisions" / "figures.json").read_text())

INK, TEAL, RUST, PAPER = "#05192B", "#31606D", "#6A2A12", "#FDF5E6"
ORANGE = "#EE8B33"

FIGURE_CSS = """<style>
.pl-fig { margin: 2.4rem 0; }
.pl-fig svg { width: 100%; height: auto; display: block; overflow: visible; }
.pl-fig .figlabel { font-family: var(--pl-font-mono, monospace); font-size: 0.68rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--pl-text-muted, #666);
  display: block; margin-bottom: .9rem; }
.pl-fig .grid { stroke: var(--pl-rule, #ccc); stroke-width: 1; }
.pl-fig .axis { stroke: var(--pl-text, #111); stroke-width: 1; }
.pl-fig .tick { fill: var(--pl-text-muted, #666); font: 0.72rem var(--pl-font-mono, monospace); }
.pl-fig .axistitle { fill: var(--pl-text, #111); font: 700 0.71rem var(--pl-font-mono, monospace); letter-spacing: .06em; }
.pl-fig .front { fill: none; stroke: var(--pl-series-1, #31606D); stroke-width: 3; stroke-dasharray: 7 5; }
.pl-fig .dot { stroke-width: 2; }
.pl-fig .dot-f { fill: var(--pl-series-1, #31606D); }
.pl-fig .dot-d { fill: var(--pl-series-1, #31606D); opacity: .3; }
.pl-fig .lbl { fill: var(--pl-text, #111); font: 600 0.75rem Georgia, serif; }
.pl-fig .leader { stroke: var(--pl-text-muted, #666); stroke-width: 1; }
.pl-fig .axistitle { fill: var(--pl-text, #111); font: 700 0.71rem var(--pl-font-mono, monospace); letter-spacing: .06em; }
.pl-fig .jlab { fill: var(--pl-orange, #EE8B33); font: 0.78rem var(--pl-font-mono, monospace); }
.pl-fig .ci { stroke: var(--pl-text-muted, #666); stroke-width: 1.5; }
</style>"""

PREVIEW_ROOT_VARS = "<style>:root{--pl-text:#05192B;--pl-text-muted:#31606D;--pl-rule:#C9C2B4;--pl-series-1:#31606D;--pl-series-2:#B3402A;--pl-orange:#EE8B33;--pl-font-mono:monospace;}</style>"


def fmt_usd(value: float) -> str:
    return f"${value:.3f}"


def fmt_ms(value: float) -> str:
    return f"{value:.0f} ms"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _frontier_idx(points: list[tuple[float, float]]) -> list[int]:
    order = sorted(range(len(points)), key=lambda i: points[i][0])
    return [i for i in order
            if not any(ox <= points[i][0] and oy >= points[i][1]
                        and (ox < points[i][0] or oy > points[i][1])
                        for j, (ox, oy) in enumerate(points) if j != i)]


def _figwrap(label: str, svg: str) -> str:
    return (f'<figure class="pl-fig"><span class="figlabel">{esc(label)}</span>'
            f"{svg}</figure>")


def pareto_figure(title: str, desc: str, chat: list[dict], jev: dict,
                  x_key: str, x_label: str, x_ticks: list[tuple[float, str]],
                  log_x: bool = False, clip: str = "fig") -> str:
    """Score-vs-x scatter; styled by FIGURE_CSS theme variables."""
    import math
    W, H, L, T, PW, PH = 840, 410, 86, 36, 704, 296
    raw_xs = [c[x_key] for c in chat]
    if log_x:
        logs = [math.log10(v) for v in raw_xs]
        lo, hi = min(logs), max(logs)
        pos = lambda v: L + (math.log10(v) - lo) / (hi - lo) * PW
        tpos = lambda v: L + (math.log10(v) - lo) / (hi - lo) * PW
    else:
        pad = max((max(raw_xs) - min(raw_xs)) * 0.08, 1.0)
        lo, hi = max(0.0, min(raw_xs) - pad), max(raw_xs) + pad
        pos = lambda v: L + (v - lo) / (hi - lo) * PW
        tpos = pos
    score_bounds = [c["score"] for c in chat] + [jev["score"]]
    score_bounds.extend(bound for c in chat for bound in c.get("ci", []))
    score_bounds.extend(jev.get("ci", []))
    ylo, yhi = max(0.0, min(score_bounds) - 0.015), min(1.0, max(score_bounds) + 0.01)
    ypos = lambda sc: T + PH - (sc - ylo) / (yhi - ylo) * PH
    pairs = [(c[x_key], c["score"]) for c in chat]
    front = _frontier_idx(pairs)
    front_set = set(front)
    grid = "\n".join(
        f'<line class="grid" x1="{L}" y1="{ypos(ylo + (yhi - ylo) * i / 4):.2f}" x2="{L + PW}" y2="{ypos(ylo + (yhi - ylo) * i / 4):.2f}" />'
        for i in range(5))
    yticks = "\n".join(
        f'<text class="tick" x="{L - 12}" y="{ypos(ylo + (yhi - ylo) * i / 4) + 4:.2f}" text-anchor="end">{_pct(ylo + (yhi - ylo) * i / 4)}</text>'
        for i in range(5))
    xticks = "\n".join(
        f'<text class="tick" x="{tpos(v):.2f}" y="{T + PH + 23}" text-anchor="middle">{esc(label)}</text>'
        for v, label in x_ticks)
    fline = " ".join(f'{"M" if k == 0 else "L"} {pos(chat[i][x_key]):.2f} {ypos(chat[i]["score"]):.2f}'
                      for k, i in enumerate(sorted(front, key=lambda i: chat[i][x_key])))
    marks, leaders, labels, placed = [], [], [], []

    def _box(lx: float, ly: float, anchor: str, text: str) -> tuple[float, float, float, float]:
        w = 0.55 * 13 * len(text)
        x0 = {"start": lx, "middle": lx - w / 2, "end": lx - w}[anchor]
        return (x0, ly - 11, x0 + w, ly + 2)

    def _overlaps(box: tuple[float, float, float, float]) -> bool:
        return any(box[0] < p[2] and p[0] < box[2] and box[1] < p[3] and p[1] < box[3] for p in placed)

    def _whisker(x: float, ci: list[float]) -> None:
        y1, y2 = ypos(ci[1]), ypos(ci[0])
        marks.append(f'<line class="ci" x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" />')
        marks.append(f'<line class="ci" x1="{x - 5:.2f}" y1="{y1:.2f}" x2="{x + 5:.2f}" y2="{y1:.2f}" />')
        marks.append(f'<line class="ci" x1="{x - 5:.2f}" y1="{y2:.2f}" x2="{x + 5:.2f}" y2="{y2:.2f}" />')
        placed.append((x - 1, min(y1, y2), x + 1, max(y1, y2)))

    order = sorted(front, key=lambda i: chat[i][x_key])
    for i in order:
        c = chat[i]
        px, py = pos(c[x_key]), ypos(c["score"])
        marks.append(f'<g><title>{esc(c["name"])}: {_pct(c["score"])} at {esc(c["tip"])} </title>'
                     f'<circle class="dot dot-f" cx="{px:.2f}" cy="{py:.2f}" r="6.5" /></g>')
        if c.get("ci"):
            _whisker(px, c["ci"])
    for i, c in enumerate(chat):
        if i in front_set:
            continue
        marks.append(f'<g><title>{esc(c["name"])}: {_pct(c["score"])} at {esc(c["tip"])} </title>'
                     f'<circle class="dot dot-d" cx="{pos(c[x_key]):.2f}" cy="{ypos(c["score"]):.2f}" r="6.5" /></g>')
    for i in order:
        c = chat[i]
        px, py = pos(c[x_key]), ypos(c["score"])
        text = c["short"]
        options = [(px + 10, py - 17, "start"), (px - 10, py + 24, "end"),
                   (px, py + 34, "middle"), (px - 10, py - 17, "end"),
                   (px + 10, py + 24, "start"), (px, py - 24, "middle")]
        lx, ly, anchor = next(((x, y, a) for x, y, a in options if not _overlaps(_box(x, y, a, text))), options[0])
        placed.append(_box(lx, ly, anchor, text))
        off = {"start": -4, "middle": 0, "end": 4}[anchor]
        leaders.append(f'<line class="leader" x1="{px:.2f}" y1="{py:.2f}" x2="{lx + off:.2f}" y2="{ly + (5 if ly < py else -10):.2f}" />')
        labels.append(f'<text class="lbl" x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}">{esc(text)}</text>')
    jx, jy = pos(jev[x_key]), ypos(jev["score"])
    if jev.get("ci"):
        _whisker(jx, jev["ci"])
    jtext = "Jev (separate interface)"
    joptions = [(jx + 14, jy + 4, "start"), (jx - 14, jy + 4, "end"),
                (jx, jy - 18, "middle"), (jx, jy + 28, "middle")]
    jlx, jly, janchor = next(((x, y, a) for x, y, a in joptions if not _overlaps(_box(x, y, a, jtext))), joptions[0])
    placed.append(_box(jlx, jly, janchor, jtext))
    marks.append(f'<g><title>Jev ({esc(jev["resolved"])}): {_pct(jev["score"])} at {esc(jev["tip"])}; separate interface, not comparable</title>'
                 f'<rect x="{jx - 7:.2f}" y="{jy - 7:.2f}" width="14" height="14" fill="var(--pl-orange, #EE8B33)" />'
                 f'<line class="leader" x1="{jx:.2f}" y1="{jy:.2f}" x2="{jlx:.2f}" y2="{jly:.2f}" /></g>')
    marks.append(f'<text class="jlab" x="{jlx:.2f}" y="{jly:.2f}" text-anchor="{janchor}">{jtext}</text>')
    clipdef = f'<clipPath id="{clip}"><rect x="{L}" y="{T}" width="{PW}" height="{PH}" /></clipPath>'
    svg = (f'<svg class="pl-chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">'
            f"<title>{esc(title)}</title><desc>{esc(desc)}</desc>" + clipdef +
            f"{grid}\n{yticks}\n{xticks}\n"
            f'<line class="axis" x1="{L}" y1="{T + PH}" x2="{L + PW}" y2="{T + PH}" />'
            f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T + PH}" />'
            f'<text class="axistitle" x="{L + PW / 2:.2f}" y="{H - 4}" text-anchor="middle">{esc(x_label)}</text>'
            f'<text class="axistitle" x="19" y="{(T + PH / 2):.2f}" text-anchor="middle" transform="rotate(-90 19 {(T + PH / 2):.2f})">ADVENTURE BENCH SCORE</text>'
            f'<path class="front" d="{fline}" />' + "".join(leaders) + f'<g clip-path="url(#{clip})">' + "".join(marks) + "</g>" + "".join(labels) + "</svg>")
    return _figwrap(title.lower(), svg)


SHORT = {
    "ibm-granite/granite-4.0-h-micro": "Granite Micro",
    "mistralai/ministral-3b-2512": "Ministral 3B",
    "mistralai/ministral-8b-2512": "Ministral 8B",
    "mistralai/ministral-14b-2512": "Ministral 14B",
    "z-ai/glm-5.2": "GLM 5.2",
    "nvidia/nemotron-3.5-lightning": "Nemotron",
    "ibm-granite/granite-4.2-8b": "Granite 4.2",
    "ibm-granite/granite-4.1-8b": "Granite 4.1",
    "meta-llama/llama-3.1-8b-instruct": "Llama 3.1 8B",
    "meta-llama/llama-3.2-3b-instruct": "Llama 3.2 3B",
    "google/gemma-3-4b-it": "Gemma 3 4B",
    "qwen/qwen3.5-9b": "Qwen 9B",
}


def _with_labels(chat: list[dict], tip: str) -> list[dict]:
    rows = []
    for c in chat:
        rows.append({"name": c["name"], "short": SHORT.get(c["name"], c["name"]),
                     "score": c["score"], "tip": c[tip], "cost": c["cost"],
                     "latency_ms": c["latency_ms"], "ci": c.get("ci")})
    return rows


def numbers() -> dict[str, str]:
    jev = FIG["jev"]
    tags = FIG["jev_by_tag"]

    def cell(tag: str) -> tuple[str, str]:
        return str(tags[tag]["passed"]), str(tags[tag]["total"])

    oov = cell("out-of-vocab")
    absent = cell("absent-object")
    exact = cell("exact-verb")
    typo = cell("typo")
    abbrev = cell("abbreviation")
    missprep = cell("missing-preposition")
    return {
        "jev_score": f"{jev['score']:.3f}",
        "jev_total": str(jev["total"]),
        "jev_cost": fmt_usd(jev["cost"]),
        "jev_latency": fmt_ms(jev["latency_ms"]),
        "jev_threshold": str(jev["threshold"]),
        "mapping_threshold": str(jev["mapping_threshold"]),
        "jev_resolved": jev["resolved"],
        "eval_fails": str(FIG["eval_fails"]),
        "eval_refusal_fails": str(FIG["eval_refusal_fails"]),
        "alias_agree": str(FIG["alias_agree"]),
        "alias_total": str(FIG["alias_total"]),
        "pinned_score": f"{FIG['pinned_score']:.3f}",
        "pinned_passed": str(FIG["pinned_passed"]),
        "pinned_total": str(FIG["pinned_total"]),
        "ci_lo": f"{FIG['ci_lo']:.3f}",
        "ci_hi": f"{FIG['ci_hi']:.3f}",
        "unclear_precision": f"{FIG['unclear_precision']:.3f}",
        "unclear_recall": f"{FIG['unclear_recall']:.3f}",
        "ministral8b_score": f"{FIG['ministral8b_score']:.3f}",
        "oov_passed": oov[0], "oov_total": oov[1],
        "absent_passed": absent[0], "absent_total": absent[1],
        "exact_passed": exact[0], "exact_total": exact[1],
        "typo_passed": typo[0], "typo_total": typo[1],
        "abbrev_passed": abbrev[0], "abbrev_total": abbrev[1],
        "missprep_passed": missprep[0], "missprep_total": missprep[1],
    }


def fig_cost() -> str:
    jev = FIG["jev"]
    chat = _with_labels(FIG["chat_models"], "cost")
    for c, raw in zip(chat, FIG["chat_models"]):
        c["tip"] = fmt_usd(raw["cost"])
    ticks = [(0.01, "$0.01"), (0.02, "$0.02"), (0.05, "$0.05"), (0.10, "$0.10")]
    return pareto_figure("Score versus cost", "Chat-model cost frontier with the Jev point marked separately",
                         chat, {"score": jev["score"], "resolved": jev["resolved"],
                                "tip": fmt_usd(jev["cost"]), "ci": jev.get("ci"), "cost": jev["cost"],
                                "latency_ms": jev["latency_ms"]},
                         "cost", "FULL-RUN COST (USD, LOG SCALE)", ticks, log_x=True, clip="fig-cost")


def fig_latency() -> str:
    jev = FIG["jev"]
    chat = _with_labels(FIG["chat_models"], "latency_ms")
    for c, raw in zip(chat, FIG["chat_models"]):
        c["tip"] = fmt_ms(raw["latency_ms"])
    ticks = [(0, "0 ms"), (500, "500 ms"), (1000, "1.0 s"), (1500, "1.5 s"), (2000, "2.0 s")]
    return pareto_figure("Score versus latency", "Chat-model latency frontier with the Jev point marked separately",
                         chat, {"score": jev["score"], "resolved": jev["resolved"],
                                "tip": fmt_ms(jev["latency_ms"]), "ci": jev.get("ci"), "cost": jev["cost"],
                                "latency_ms": jev["latency_ms"]},
                         "latency_ms", "MEDIAN PER-CASE LATENCY", ticks, clip="fig-lat")


FIGURES = {"1": fig_cost, "2": fig_latency}


def md_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)


def md_to_html(body: str) -> str:
    out = []
    for para in [p for p in body.split("\n\n") if p.strip()]:
        lines = para.strip().split("\n")
        if len(lines) == 1 and lines[0].startswith("## "):
            out.append(f"<h2>{md_inline(lines[0][3:])}</h2>")
        elif lines[0].startswith("|"):
            cells = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines if "---" not in line]
            head, rows = cells[0], cells[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
        elif re.match(r"^\[FIG-\d+:", lines[0]):
            out.append(lines[0])
        elif lines[0].startswith("<svg"):
            out.extend(lines)
        else:
            out.append(f"<p>{md_inline(' '.join(lines))}</p>")
    return "\n".join(out)


def main() -> None:
    tmpl = (ART / "article.md.tmpl").read_text()
    filled = tmpl
    for key, value in numbers().items():
        filled = filled.replace("{{" + key + "}}", value)
    leftover = sorted(set(re.findall(r"\{\{(\w+)\}\}", filled)))
    if leftover:
        raise SystemExit(f"unfilled placeholders: {leftover}")
    (ART / "article.md").write_text(filled)
    site = filled
    missing = sorted(set(re.findall(r"\[FIG-(\d+)[^\]]*\]", site)))
    for number in missing:
        if number not in FIGURES:
            raise SystemExit(f"no figure builder for FIG-{number}")
        site = site.replace(f"[FIG-{number}:", "\x00", 1)
        marker = site.index("\x00")
        end = site.index("`", marker)
        start = marker - 1 if site[marker - 1] == "`" else marker
        site = site[:start] + FIGURES[number]() + site[end + 1:]
    if "[FIG-" in site:
        raise SystemExit("unreplaced figure markers remain")
    (ART / "article.site.md").write_text(site)
    head, sep, rest = site.partition("---\n")
    fm_keys, sep2, body_rest = rest.partition("---\n")
    site_with_css = head + sep + fm_keys + sep2 + FIGURE_CSS + "\n" + body_rest
    (ART / "article.site.md").write_text(site_with_css)
    fm, _, body = filled.partition("---\n")[2].partition("---\n")
    _, _, site_body = site.partition("---\n")[2].partition("---\n")
    title = re.search(r"^title:\s*(.+)$", fm, re.M).group(1)
    (ART / "preview.html").write_text(
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>" + esc(title) + "</title>"
        "<style>body{max-width:44rem;margin:2rem auto;font-family:Georgia,serif;line-height:1.6;padding:0 1rem}"
        "table{border-collapse:collapse}td,th{border:1px solid #999;padding:.3rem .7rem;text-align:left}"
        "</style>" + PREVIEW_ROOT_VARS + FIGURE_CSS + "</head><body>" + md_to_html(site_body) + "</body></html>")
    print(f"built article.md, article.site.md, preview.html ({title})")


if __name__ == "__main__":
    main()
