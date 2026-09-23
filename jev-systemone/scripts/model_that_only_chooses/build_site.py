"""Write 02-model-that-only-chooses/article.site.md from article.md.

The draft marks each figure with a `[FIG-N: label. caption. Source: /path]`
marker. The site has no idea what to do with those, so this replaces each one
with a `pl-fig` figure: SVG figures are inlined, so they pick up the page's
brand fonts and light or dark scheme, and photos load from the site's asset
tree. It also drops
`draft: true` from the front matter, unquotes its values and sets the publication date.

    python3 jev-systemone/scripts/model_that_only_chooses/build_site.py 2026-09-23
"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "02-model-that-only-chooses"
ASSETS = "/assets/research/model-that-only-chooses"

STYLE = """<style>
.pl-fig { margin: 2.4rem 0; }
.pl-fig img, .pl-fig svg { width: 100%; height: auto; display: block; border-radius: 4px; }
.pl-fig .figlabel { font-family: var(--pl-font-mono, monospace); font-size: 0.68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--pl-text-muted, #666); display: block; margin-bottom: .9rem; }
.pl-fig figcaption { font-size: 0.9rem; line-height: 1.5; color: var(--pl-text-muted, #666); margin-top: .8rem; }
</style>"""

MARKER = re.compile(r"^`\[FIG-(\d+): (.*?) Source: (\S+)\]`$", re.M)


def inline_svg(path, n):
    """One line, so markdown passes it through as a single raw HTML block, and
    each figure's `.jv` styles renamed to `.jvN` so figures cannot restyle each other."""
    svg = re.sub(r"<\?xml[^>]*>", "", path.read_text())
    svg = re.sub(r"\.jv\b", f".jv{n}", svg).replace('class="jv"', f'class="jv{n}"')
    return " ".join(line.strip() for line in svg.splitlines() if line.strip())


def figure(m):
    n, text, src = m.group(1), m.group(2).strip(), Path(m.group(3)).name
    label, _, caption = text.partition(". ")
    alt = html.escape(text.rstrip("."), quote=True)
    if src.endswith(".svg"):
        body = inline_svg(HERE / src, n)
    else:
        body = f'<img src="{ASSETS}/{src}" alt="{alt}" loading="lazy" />'
    return (f'<figure class="pl-fig" id="fig-{n}"><span class="figlabel">{html.escape(label)}</span>'
            f'{body}<figcaption>{html.escape(caption)}</figcaption></figure>')


def main(date):
    text = (HERE / "article.md").read_text()
    _, front, body = text.split("---\n", 2)
    front = "".join(line + "\n" for line in front.splitlines() if not line.startswith("draft:"))
    front = re.sub(r"^date: .*$", f"date: {date}", front, flags=re.M)
    # the site reads front matter as plain `key: value` and would print YAML's quotes
    front = re.sub(r'^(\w+): "(.*)"$', r"\1: \2", front, flags=re.M)
    body = MARKER.sub(figure, body)
    if "[FIG-" in body:
        sys.exit("a figure marker was left unreplaced")
    (HERE / "article.site.md").write_text(f"---\n{front}---\n{STYLE}\n{body}")


if __name__ == "__main__":
    main(sys.argv[1])
