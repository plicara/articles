"""When, in the day, is each language's skills written?

Commit timestamps in this dataset are normalised to UTC, so the author's
local offset is gone. But authors mostly commit during their own waking
hours, so the *shape* of a language group's UTC hour-of-day distribution
still carries geography: if a group's commits collapse during a particular
UTC window, that window is probably its night.

This does two things:

1. Prints the UTC hour-of-day profile per language group.
2. Estimates an implied UTC offset per group -- the offset that best
   concentrates that group's commits into a plausible local working day
   (WORK_START..WORK_END local time). This is a descriptive summary of the
   distribution's phase, not a claim about any individual author.

Why bother: it is an *independent* check on the language identification.
Nothing about py3langid knows what time of day a file was committed, so if
Chinese-labelled skills independently show a UTC+8-shaped clock, the two
signals corroborate each other.

Caveats, which are real:
- Hour-of-day inference is coarse. It cannot separate neighbouring zones
  (UTC+8 vs UTC+9), and a language is not a country -- Spanish and
  Portuguese skills are written across Europe and the Americas, so their
  aggregate clock is a blend of several zones and the implied offset for
  such a group is close to meaningless.
- Commits can be made by CI, by bots, or at unusual hours; the estimate
  describes a population, never an author.
- A first commit is one timestamp per skill, so groups with few skills
  produce noisy clocks. Groups under MIN_N are skipped.
"""

from collections import Counter, defaultdict

import duckdb

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (source, MAX_CHARS, PROSE_SQL, classify, connect, db_path,
                    identifier)

MIN_N = 40
WORK_START, WORK_END = 8, 20  # local hours counted as "awake"

GROUPS = [
    ("English", {"en"}),
    ("Chinese", {"zh"}),
    ("Japanese", {"ja"}),
    ("Korean", {"ko"}),
    ("German", {"de"}),
    ("Russian", {"ru"}),
    ("Spanish/Portuguese", {"es", "pt"}),
]

con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE d AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           CAST(first_commit_at AS TIMESTAMP) AS created
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
      AND first_commit_at IS NOT NULL
""")

ident = identifier()
hours_by_lang = defaultdict(Counter)
for prose, created in con.execute("SELECT prose, created FROM d").fetchall():
    code = classify(ident, prose)
    if code and code != "uncertain":
        hours_by_lang[code][created.hour] += 1


def implied_offset(hours: Counter):
    """Offset whose local WORK_START..WORK_END window holds the most commits."""
    total = sum(hours.values())
    best, best_share = None, -1.0
    for off in range(-11, 15):
        awake = sum(
            n for h, n in hours.items()
            if WORK_START <= (h + off) % 24 < WORK_END
        )
        share = awake / total
        if share > best_share:
            best, best_share = off, share
    return best, best_share


print("=== UTC hour-of-day profile of first commits ===")
print("  each bar is one UTC hour, 00 on the left; height is share of that group\n")

results = []
for label, codes in GROUPS:
    hours = Counter()
    for c in codes:
        hours.update(hours_by_lang.get(c, {}))
    n = sum(hours.values())
    if n < MIN_N:
        continue
    peak = max(range(24), key=lambda h: hours[h])
    off, share = implied_offset(hours)
    results.append((label, n, hours, peak, off, share))

    bars = ""
    top = max(hours[h] for h in range(24)) or 1
    for h in range(24):
        level = 8 * hours[h] / top
        bars += " ▁▂▃▄▅▆▇█"[min(8, int(round(level)))]
    print(f"  {label:<20} n={n:<6} {bars}")

print("\n  hour  " + " ".join(f"{h:02d}" for h in range(0, 24, 2)))

print("\n=== implied timezone ===")
print(f"  offset that best fits commits into a local {WORK_START:02d}:00-{WORK_END:02d}:00 day\n")
print(f"  {'language':<20}{'n':>6}{'peak UTC':>10}{'implied':>10}{'in-window':>12}")
for label, n, hours, peak, off, share in results:
    sign = "+" if off >= 0 else ""
    print(f"  {label:<20}{n:>6}{peak:>7}:00{'  UTC' + sign + str(off):>10}"
          f"{100 * share:>11.1f}%")

print("\n=== night check: share of commits in 16:00-24:00 UTC ===")
print("  that window is 00:00-08:00 in UTC+8, so an East Asian population")
print("  should nearly vanish from it while a global one should not\n")
print(f"  {'language':<20}{'n':>6}{'share':>9}")
for label, n, hours, _, _, _ in results:
    night = sum(hours[h] for h in range(16, 24))
    print(f"  {label:<20}{n:>6}{100 * night / n:>8.1f}%")
