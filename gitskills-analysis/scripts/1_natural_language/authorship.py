"""Who writes skills -- people or agents? And does it depend on the language?

This is the other half of GitSkills RQ 1d ("How many skills do agents
themselves create or maintain, and in which natural languages are skills
written?"). The language half is answered by natural_lang.py; this is the
authorship half.

Measuring it needs care, because the obvious signals are wrong:

- `first_commit_author_type = 'Bot'` catches almost nothing (25 of 3,010
  here). Agent-written code is normally committed under the human's own
  account, so the platform never sees a bot.
- Searching commit messages for "claude" is far worse than it looks. Most
  matches are humans describing what they added -- "add Claude Code skills
  for drafting releases", "add all Claude skills from main config". One
  such message is even co-authored by a different agent entirely. That
  substring measures what the commit is ABOUT, not who wrote it.

What does work is the trailer convention. Coding agents append machine
-readable attribution to commits they author -- `Co-Authored-By: <model>`
and `Generated with <tool>`. That is an explicit claim of authorship by the
tool itself rather than an inference from prose.

Read the result as a LOWER BOUND. An agent-written skill whose author
stripped the trailer, squashed it away, or used a tool that does not emit
one is counted as human here. Nothing in this data can catch those.
"""

import re
from collections import Counter, defaultdict

import duckdb

from common import (MAX_CHARS, PROSE_SQL, classify, connect, db_path,
                    identifier, is_non_english, wilson)

MIN_CELL = 30

TRAILER = re.compile(r"co-authored-by:\s*([^<\n]+)", re.I)
GENERATED = re.compile(r"generated with\s*\[?([^\]\n(]+)", re.I)
# Tools that emit authorship trailers. Matched against the trailer VALUE,
# never against the message body, so a commit that merely mentions a tool
# is not counted.
AGENT = re.compile(
    r"claude|cursor|copilot|codex|devin|aider|windsurf|gemini|gpt|openai|cline",
    re.I,
)


def agents_in(message: str):
    """Agent names claimed as authors of this commit, deduplicated."""
    found = set()
    for pattern in (TRAILER, GENERATED):
        for raw in pattern.findall(message):
            name = raw.strip()
            if name and AGENT.search(name):
                found.add(name)
    return found


con = connect(duckdb.connect)
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE d AS
    SELECT substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose,
           coalesce(first_commit_message, '') AS msg,
           CAST(first_commit_at AS TIMESTAMP) AS created,
           coalesce(first_commit_author_type, '') AS author_type
    FROM sqlite_scan('{db_path()}', 'artifacts')
    WHERE dedup_primary = 1 AND content IS NOT NULL
      AND first_commit_message IS NOT NULL
""")

ident = identifier()
recs, models = [], Counter()
for prose, msg, created, atype in con.execute(
        "SELECT prose, msg, created, author_type FROM d").fetchall():
    code = classify(ident, prose)
    if code is None:
        continue
    found = agents_in(msg)
    models.update(found)
    recs.append({"lang": code, "agent": bool(found), "created": created,
                 "bot": atype == "Bot"})

total = len(recs)
agent_n = sum(r["agent"] for r in recs)
bot_n = sum(r["bot"] for r in recs)
lo, hi = wilson(agent_n, total)

print(f"=== agent authorship, {total} skills with a first-commit message ===")
print(f"  named an agent in a trailer : {agent_n}  {100*agent_n/total:.1f}%  "
      f"[{100*lo:.1f}, {100*hi:.1f}]")
print(f"  flagged Bot by the platform : {bot_n}  {100*bot_n/total:.1f}%")
print("  -> the platform's own bot flag misses almost all of it")

print("\n=== which agents claim authorship? ===")
grouped = Counter()
for name, n in models.items():
    key = "Claude" if re.search(r"claude", name, re.I) else name
    grouped[key] += n
for name, n in grouped.most_common(8):
    print(f"  {n:>5}  {name}")

print("\n=== specific models named (Claude trailers carry a version) ===")
for name, n in models.most_common(8):
    print(f"  {n:>5}  {name}")


def band(sel):
    k = sum(r["agent"] for r in sel)
    l, h = wilson(k, len(sel))
    return f"{100*k/len(sel):>5.1f}%  [{100*l:>4.1f}, {100*h:>5.1f}]  n={len(sel)}"


print("\n=== does agent authorship differ by language? ===")
GROUPS = [("English", lambda r: r["lang"] == "en"),
          ("non-English", lambda r: is_non_english(r["lang"])),
          ("  Chinese", lambda r: r["lang"] == "zh"),
          ("  Japanese", lambda r: r["lang"] == "ja"),
          ("  European", lambda r: r["lang"] in
           {"de", "fr", "es", "pt", "it", "ru", "nl"})]
for label, pred in GROUPS:
    sel = [r for r in recs if pred(r)]
    if len(sel) >= MIN_CELL:
        print(f"  {label:<13}{band(sel)}")

print("\n=== is it rising? ===")
byq = defaultdict(list)
for r in recs:
    byq[f"{r['created'].year}-Q{(r['created'].month - 1) // 3 + 1}"].append(r)
quarters = sorted(byq)
for q in quarters:
    if len(byq[q]) >= MIN_CELL:
        note = "  partial" if q == quarters[-1] else ""
        print(f"  {q:<9}{band(byq[q])}{note}")

print("\n=== agent-written skills: are they more or less English? ===")
for label, pred in (("agent-authored", lambda r: r["agent"]),
                    ("human-authored", lambda r: not r["agent"])):
    sel = [r for r in recs if pred(r)]
    k = sum(1 for r in sel if is_non_english(r["lang"]))
    l, h = wilson(k, len(sel))
    print(f"  {label:<16}non-English {100*k/len(sel):>5.1f}%  "
          f"[{100*l:.1f}, {100*h:.1f}]  n={len(sel)}")
