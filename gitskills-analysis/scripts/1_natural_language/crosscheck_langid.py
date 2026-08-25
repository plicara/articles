"""Is our English share a property of the corpus, or of the tool?

We report roughly 85% English. A published study of a skills marketplace
reports 92.6%, using fast-langdetect where we use py3langid. Two numbers
that far apart invite the obvious objection: that the gap is the
identifier, not the population.

This runs both identifiers over the same documents and reports how often
they agree, where they disagree, and what English share each produces. If
the two land close together, the gap is about which corpus was sampled. If
they diverge, our headline needs a caveat it does not currently carry.

Deliberate choices:

- Both see identical input: the same cleaned prose, same truncation. Any
  difference is the model, not the preprocessing.
- fast-langdetect is applied without a confidence floor, matching how the
  comparison study describes using it as a filter. Our own floor is applied
  separately so both effects are visible.
- A random subsample rather than all 1.87M documents, because the point is
  an agreement rate and its interval, not another census. Set SAMPLE_N.

    uv run scripts/1_natural_language/crosscheck_langid.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (CONF_FLOOR, MAX_CHARS, MIN_PROSE, NAMES, PROSE_SQL,
                    connect, identifier, scale, source, wilson)

SAMPLE_N = 60_000
SEED = 0.42  # DuckDB reproducible sampling


def main():
    try:
        from fast_langdetect import detect
    except ImportError:
        raise SystemExit(
            "fast-langdetect not installed. It is an optional comparison "
            "dependency: uv add fast-langdetect")

    con = connect(duckdb.connect)
    con.execute(f"SELECT setseed({SEED})")
    rows = con.execute(f"""
        SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose
        FROM {source('artifacts')}
        WHERE dedup_primary = 1 AND content IS NOT NULL
        USING SAMPLE {SAMPLE_N} ROWS
    """).fetchall()

    ident = identifier()
    agree = both = 0
    ours, theirs = Counter(), Counter()
    disagreements = Counter()
    low_conf_ours = 0

    for (prose,) in rows:
        text = prose.strip()
        if len(text) < MIN_PROSE:
            continue
        both += 1

        a, prob = ident.classify(text)
        if prob < CONF_FLOOR:
            low_conf_ours += 1
        ours[a] += 1

        # fastText chokes on newlines; it expects a single line
        b = detect(text.replace("\n", " "))[0]["lang"]
        theirs[b] += 1

        if a == b:
            agree += 1
        else:
            disagreements[(a, b)] += 1

    print(f"=== {both:,} documents, {scale()} ===\n")

    lo, hi = wilson(agree, both)
    print(f"  agreement          {100 * agree / both:>6.1f}%  "
          f"[{100 * lo:.1f}, {100 * hi:.1f}]")
    print(f"  our low-confidence {100 * low_conf_ours / both:>6.1f}%  "
          f"(held out as uncertain in the article)")

    print("\n=== English share, same documents, two identifiers ===")
    for label, counts in (("py3langid (ours)", ours), ("fast-langdetect", theirs)):
        en = counts["en"]
        lo, hi = wilson(en, both)
        print(f"  {label:<20}{100 * en / both:>6.1f}%  [{100*lo:.1f}, {100*hi:.1f}]")
    delta = 100 * (theirs["en"] - ours["en"]) / both
    print(f"  difference          {delta:>+6.1f} points")

    print("\n=== where they disagree, most common first ===")
    print(f"  {'ours':<12}{'theirs':<12}{'n':>7}")
    for (a, b), n in disagreements.most_common(10):
        print(f"  {NAMES.get(a, a):<12}{NAMES.get(b, b):<12}{n:>7}")

    print("\n=== top languages, side by side ===")
    print(f"  {'language':<14}{'ours':>9}{'theirs':>9}")
    for code, _ in ours.most_common(8):
        print(f"  {NAMES.get(code, code):<14}"
              f"{100 * ours[code] / both:>8.1f}%{100 * theirs[code] / both:>8.1f}%")

    # written beside figures.json and folded into it by export_figures.py,
    # which is the file the article reads; this one is the raw record
    out = Path(__file__).resolve().parents[2] / "results" / "crosscheck.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "documents": both,
        "agreement_pct": round(100 * agree / both, 1),
        "ours_english_pct": round(100 * ours["en"] / both, 1),
        "theirs_english_pct": round(100 * theirs["en"] / both, 1),
        "delta_points": round(100 * (theirs["en"] - ours["en"]) / both, 1),
        "ours_tool": "py3langid", "theirs_tool": "fast-langdetect",
    }, indent=2))
    print(f"\n  wrote {out}")

    print("\n  Read the difference above against the 7-point gap between our "
          "\n  reported English share and the marketplace study's 92.6%. If the "
          "\n  identifiers differ by much less than that, the gap is the corpus.")


if __name__ == "__main__":
    main()
