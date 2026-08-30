#!/usr/bin/env python3
"""Render the eight figures alone, so they can be looked at.

The colour validator checks colour. It cannot see a label colliding with a
dot, a value running past the viewBox, or a bar so thin it disappears. That
needs rendering the thing and looking at it, which is the last step of the
procedure and the one most often skipped.

    uv run scripts/2_programming_languages/preview_figures.py
    # writes 02-programming-languages/figures-preview.html

Light and dark are both emitted, stacked, because the site themes with the
reader and a figure that only works in one mode is half broken.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charts import CHARTS, FIG

OUT = (Path(__file__).resolve().parents[2] / "02-programming-languages"
       / "figures-preview.html")

TITLES = {
    1: "FIG-1  What a skill is made of",
    2: "FIG-2  A Rust project ships a Python skill",
    3: "FIG-3  TypeScript falls while GitHub says it is rising",
    4: "FIG-4  The gap is widening",
    5: "FIG-5  Talked about, not written",
    6: "FIG-6  Who ships code",
    7: "FIG-7  What gets copied",
    8: "FIG-8  Nobody uses the specification's layout",
}

CSS = """
:root {
  --pl-bg:#f5f6f8; --pl-surface:#fff; --pl-text:#14181f; --pl-text-muted:#6b7280;
  --pl-rule:#d3d7de; --c-compare:#2d4ea2; --c-subject:#c8761a;
  --pl-font-mono:'IBM Plex Mono',ui-monospace,monospace;
}
.dark {
  --pl-bg:#101317; --pl-surface:#171b21; --pl-text:#e8eaed; --pl-text-muted:#9aa3b0;
  --pl-rule:#2b313a; --c-compare:#7c9be8; --c-subject:#e0a155;
}
body { margin:0; font-family:'Newsreader',Georgia,serif; }
section { background:var(--pl-bg); color:var(--pl-text); padding:2.5rem 2rem 4rem; }
.wrap { max-width:64rem; margin:0 auto; }
h1 { font-family:var(--pl-font-mono); font-size:.8rem; letter-spacing:.16em;
     text-transform:uppercase; color:var(--pl-text-muted); margin:0 0 2.5rem; }
figure { margin:0 0 3.4rem; background:var(--pl-surface); padding:1.6rem 1.5rem 1.8rem;
         border:1px solid var(--pl-rule); border-radius:6px; }
figcaption { font-family:var(--pl-font-mono); font-size:.72rem; letter-spacing:.1em;
             text-transform:uppercase; color:var(--pl-text-muted); margin:0 0 1.3rem; }
svg { width:100%; height:auto; display:block; overflow:visible; }
.lbl  { font-size:17px; fill:var(--pl-text); }
.val  { font-size:16px; fill:var(--pl-text); font-weight:600;
        font-variant-numeric:tabular-nums; font-family:var(--pl-font-mono); }
.axis { font-size:14px; fill:var(--pl-text-muted); font-family:var(--pl-font-mono);
        font-variant-numeric:tabular-nums; }
.sub  { font-size:12px; fill:var(--pl-text-muted); font-family:var(--pl-font-mono); }
.ann  { font-size:14px; fill:var(--pl-text-muted); font-family:var(--pl-font-mono); }
.onbar{ font-size:15px; fill:var(--pl-bg); font-weight:600;
        font-family:var(--pl-font-mono); }
.onbar.sm { font-size:13px; font-weight:400; opacity:.85; }
.onbar.off { fill:var(--pl-text-muted); }
.huge { font-size:64px; fill:var(--pl-text); font-weight:600;
        font-family:var(--pl-font-mono); font-variant-numeric:tabular-nums; }
.grid { stroke:var(--pl-rule); stroke-width:1; }
.annrule  { stroke:var(--pl-rule); stroke-width:1; stroke-dasharray:3 3; }
.refline  { stroke:var(--pl-text-muted); stroke-width:1; stroke-dasharray:4 4; }
.connector{ stroke:var(--pl-rule); stroke-width:3; }
.whisker  { stroke:var(--c-compare); stroke-width:3; opacity:.55; }
.ci { fill:var(--c-compare); opacity:.18; }
.trendline{ fill:none; stroke:var(--c-subject); stroke-width:2.6; stroke-linejoin:round; }
.control  { fill:none; stroke:var(--pl-rule); stroke-width:2.2; stroke-linejoin:round; }
.dot { fill:var(--c-subject); }
.dot.partial { fill:var(--pl-bg); stroke:var(--c-subject); stroke-width:2; }
.censored { fill:var(--pl-rule); opacity:.35; }
"""


def body():
    return "\n".join(
        f'<figure><figcaption>{TITLES[n]}</figcaption>{CHARTS[n]()}</figure>'
        for n in sorted(CHARTS))


page = f"""<!doctype html><meta charset="utf-8">
<title>Article 02 figures</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:wght@300;400;500&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
<section><div class="wrap"><h1>light &middot; {FIG['provenance']['corpus']}</h1>
{body()}</div></section>
<section class="dark"><div class="wrap"><h1>dark</h1>
{body()}</div></section>
"""

OUT.write_text(page)
print(f"wrote {OUT}  ({len(page):,} bytes, {len(CHARTS)} figures x 2 modes)")
