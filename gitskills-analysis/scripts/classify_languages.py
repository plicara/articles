#!/usr/bin/env python3
"""Classify every skill's natural language once, and cache it.

Articles 02 and 03 both cross their measure against the language a skill is
written in, and article 01 already published that column. Re-deriving it per
script means running language identification over the whole corpus three
times, which at full scale is the slowest thing in the project, and it means
three chances for the definitions to drift apart.

So it is computed once, here, using article 01's cleaning SQL, identifier
and confidence floor unchanged, and written to a Parquet file the other
scripts join against. Nothing downstream may re-implement it.

    uv run scripts/classify_languages.py

Writes data/derived/skill_language.parquet with one row per deduplication
representative carrying content: repo_full_name, path, code, group.

`code` is the raw language code or 'uncertain'; `group` is the coarse
grouping the articles report (English, Chinese, Japanese, Korean, European,
other non-English), with 'uncertain' preserved so it can be excluded from
both sides of a comparison rather than silently counted as non-English.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (MAX_CHARS, PROSE_SQL, classify, connect, identifier,
                    scale, source, _data_dir)

BATCH = 50_000
EUROPEAN = {"de", "fr", "es", "pt", "it", "ru", "nl"}
NAMED = {"zh": "Chinese", "ja": "Japanese", "ko": "Korean"}


def group(code):
    if code == "en":
        return "English"
    if code in NAMED:
        return NAMED[code]
    if code in EUROPEAN:
        return "European"
    if code == "uncertain":
        return "uncertain"
    return "other non-English"


def main():
    out_dir = (_data_dir() or Path("data")) / "derived"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "skill_language.parquet"

    con = connect(duckdb.connect)
    print(f"=== classifying, {scale()} ===")

    # Row-numbered so it can be paged. Writing to the same connection while a
    # read cursor is open invalidates that cursor, so the loop below reads a
    # range at a time and accumulates; the output is four short strings per
    # row, small enough to hold even at full corpus.
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE src AS
        SELECT row_number() OVER () AS rn, repo_full_name, path,
               substr({PROSE_SQL}, 1, {MAX_CHARS}) AS prose
        FROM {source('artifacts')}
        WHERE dedup_primary = 1 AND content IS NOT NULL
    """)
    total = con.execute("SELECT count(*) FROM src").fetchone()[0]
    print(f"  representatives with content: {total:,}")

    ident = identifier()
    con.execute("CREATE OR REPLACE TEMP TABLE out "
                "(repo_full_name VARCHAR, path VARCHAR, code VARCHAR, \"group\" VARCHAR)")

    acc = []
    done = skipped = 0
    for start in range(0, total, BATCH):
        rows = con.execute(
            "SELECT repo_full_name, path, prose FROM src "
            f"WHERE rn > {start} AND rn <= {start + BATCH}").fetchall()
        for repo, path, prose in rows:
            code = classify(ident, prose or "")
            if code is None:
                skipped += 1
                continue
            acc.append((repo, path, code, group(code)))
        done += len(rows)
        print(f"  {done:,} / {total:,}", flush=True)

    for i in range(0, len(acc), BATCH):
        con.executemany("INSERT INTO out VALUES (?, ?, ?, ?)", acc[i:i + BATCH])

    con.execute(f"COPY out TO '{out}' (FORMAT parquet)")
    n = con.execute("SELECT count(*) FROM out").fetchone()[0]
    print(f"\n  classified : {n:,}")
    print(f"  too little prose to identify: {skipped:,}")
    print("\n  " + "\n  ".join(
        f"{g:<20}{c:>10,}" for g, c in con.execute(
            'SELECT "group", count(*) c FROM out GROUP BY 1 ORDER BY c DESC').fetchall()))
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
