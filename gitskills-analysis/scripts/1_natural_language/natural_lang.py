"""Natural-language distribution of skill instructions.

Answers GitSkills RQ 1d ("in which natural languages are skills written?")
over distinct skill contents. Input per doc: cleaned prose (YAML front
matter and fenced code stripped, invisible chars removed), truncated to
MAX_CHARS -- language ID is reliable long before that. Docs below
CONF_FLOOR are held out as uncertain rather than forced into a class, and
docs left with almost no prose are excluded outright.

Positioning against published numbers for the English share of a skills
corpus, which range widely by sampling frame:
  65.0%  healthcare subset of a ClawHub snapshot   (arXiv:2605.02709)
  ~81.9% ClawHub general, English/Chinese only     (arXiv:2604.13064)
  92.6%  skills.sh marketplace, binary filter      (arXiv:2607.01456)
  99.7%  English-seeded GitHub crawl               (arXiv:2606.03565)
The spread is itself the finding: sampling frame drives the headline.
"""

from collections import Counter

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, NAMES, PROSE_SQL, classify, connect, db_path,
                    identifier)

DB = db_path()

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE docs AS
    SELECT {PROSE_SQL} AS prose
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")

ident = identifier()
texts = [t[0] for t in con.execute(
    "SELECT substr(prose, 1, $1) FROM docs", [MAX_CHARS]).fetchall()]

counts, too_short = Counter(), 0
for text in texts:
    code = classify(ident, text)
    if code is None:
        too_short += 1
        continue
    counts[code] += 1

total = sum(counts.values())
ranked = counts.most_common()

print(f"\n{total} distinct skills\n")
print(f"{'language':<16}{'skills':>8}{'%':>7}")
for code, n in ranked[:15]:
    print(f"{NAMES.get(code, code):<16}{n:>8}{100 * n / total:>6.1f}%")
rest = sum(n for _, n in ranked[15:])
if rest:
    tail = ", ".join(NAMES.get(c, c) for c, _ in ranked[15:])
    print(f"{'other':<16}{rest:>8}{100 * rest / total:>6.1f}%   ({tail})")

non_english = total - counts.get("en", 0) - counts.get("uncertain", 0)
print(f"\nnon-English (excl. uncertain): {non_english} "
      f"({100 * non_english / total:.1f}%)")
print(f"held out as uncertain: {counts.get('uncertain', 0)}")
print(f"excluded, too little prose: {too_short}")
