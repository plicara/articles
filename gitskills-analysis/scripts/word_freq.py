"""Word frequencies across GitSkills sample (representative skills only).

Copies are excluded so mass-verbatim templates don't dominate the
vocabulary; every distinct content counts exactly once.
"""

import os
from pathlib import Path

from common import source

import duckdb


con = duckdb.connect()
con.execute("INSTALL sqlite")
con.execute("LOAD sqlite")

# Minimal function-word stoplist: articles, prepositions, pronouns,
# auxiliaries only. Domain words (file, test, git, code...) are kept --
# they ARE the signal here.
STOPWORDS = """the a an and or but if then else of to in on at by for with from
as is are was were be been being this that these those it its you your we our
they their he she his her i me my do does did not no so such than too very can
will just now into over under out up down when where all any each few more most
other some only own same here there what which who because while during before
after also""".split()

con.execute("CREATE OR REPLACE TEMP TABLE stops(word VARCHAR)")
con.executemany("INSERT INTO stops VALUES (?)", [(w,) for w in STOPWORDS])

con.execute(f"""
    CREATE OR REPLACE TEMP TABLE docs AS
    SELECT ROW_NUMBER() OVER () AS did,
           -- analysis view: drop YAML front matter, zero-width/soft-hyphen
           -- artifacts, and fenced code blocks. Every regexp_replace needs
           -- the 'g' flag -- DuckDB replaces only the first match without it.
           regexp_replace(
            lower(regexp_replace(content, '(?s)\\A---.*?---\\r?\\n?', ' ')),
             '[' || chr(8203) || chr(8204) || chr(8205) || chr(65279) || chr(173) || ']',
             '', 'g') AS prose,
           content AS raw
    FROM {source('artifacts')}
    WHERE dedup_primary = 1 AND content IS NOT NULL
""")

# keep fenced-code stripping as its own pass so front-matter removal
# above doesn't interact with ``` spans
con.execute("UPDATE docs SET prose = regexp_replace(prose, '(?s)```.*?```', ' ', 'g')")

n_docs = con.sql("SELECT COUNT(*), ROUND(SUM(length(raw))/1048576.0, 1) FROM docs").fetchall()[0]
print(f"corpus: {n_docs[0]} distinct skills, {n_docs[1]} MB of text\n")

invisible = con.sql("""
    SELECT ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM docs), 1)
    FROM docs
    WHERE regexp_matches(raw, chr(8203) || '|' || chr(8204) || '|'
                               || chr(8205) || '|' || chr(65279) || '|'
                               || chr(173))
""").fetchone()[0]
print(f"skills containing invisible chars (ZWSP/ZWNJ/ZWJ/BOM/SHY): {invisible}%\n")


def top_words(column: str, limit: int, exclude_stops: bool):
    sql = f"""
        WITH tok AS (
            SELECT UNNEST(regexp_extract_all(d.{column}, '[a-z][a-z0-9]{{1,23}}', 0)) AS word,
                   d.did AS did
            FROM docs d
        )
        SELECT word,
               COUNT(*) AS freq,
               ROUND(100.0 * COUNT(DISTINCT did) / (SELECT COUNT(*) FROM docs), 1) AS pct_docs
        FROM tok
        {'WHERE word NOT IN (SELECT word FROM stops)' if exclude_stops else ''}
        GROUP BY word ORDER BY freq DESC LIMIT {limit}
    """
    return con.sql(sql)


print("== raw tokens (code fences included), top 15 ==")
print(top_words("raw", 15, exclude_stops=False))
print("\n== prose tokens (code stripped + stopwords removed), top 25 ==")
print(top_words("prose", 25, exclude_stops=True))
