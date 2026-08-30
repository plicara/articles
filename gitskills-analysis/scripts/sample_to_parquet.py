#!/usr/bin/env python3
"""Convert the SQLite sample to per-table Parquet, the shape the full corpus has.

Two reasons this exists. The full 3.8M release is queried as Parquet (13 GB
against 44 GB for the same data as SQLite), so a script proven against
Parquet locally is proven against the form it will actually run in. And
DuckDB reads local Parquet with no extension at all, while `sqlite_scan`
needs the `sqlite` extension downloaded at runtime, which fails on any
machine whose egress policy blocks DuckDB's extension repository.

Output lands in data/parquet/<table>/<table>.parquet, which is the layout
common.source() looks for. Point scripts at it with:

    GITSKILLS_PARQUET=data/parquet uv run scripts/<script>.py

Leaving GITSKILLS_PARQUET unset keeps the SQLite path, so nothing that ran
before runs differently now.
"""

import sqlite3
import sys
from pathlib import Path

import duckdb

from common import db_path

BATCH = 5000


def convert(src: str, dest: Path) -> None:
    lite = sqlite3.connect(src)
    tables = [r[0] for r in lite.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

    for table in tables:
        cols = [r[1] for r in lite.execute(f"PRAGMA table_info({table})")]
        out = dest / table
        out.mkdir(parents=True, exist_ok=True)

        # Types must match what sqlite_scan would have produced, or a script
        # that runs on the SQLite sample fails on the Parquet one: an
        # all-VARCHAR schema breaks the first COALESCE against an integer.
        decl = {r[1]: (r[2] or "").upper() for r in lite.execute(f"PRAGMA table_info({table})")}
        types = {c: "BIGINT" if "INT" in decl[c]
                 else "DOUBLE" if decl[c] in ("REAL", "FLOAT", "DOUBLE")
                 else "VARCHAR" for c in cols}

        con = duckdb.connect()
        con.execute(f"CREATE TABLE t ({', '.join(f'\"{c}\" {types[c]}' for c in cols)})")
        placeholders = ", ".join("?" * len(cols))
        n = 0
        cur = lite.execute(f"SELECT {', '.join(cols)} FROM {table}")
        while rows := cur.fetchmany(BATCH):
            con.executemany(f"INSERT INTO t VALUES ({placeholders})", rows)
            n += len(rows)
        con.execute(f"COPY t TO '{out / (table + '.parquet')}' (FORMAT parquet)")
        con.close()
        print(f"  {table:<20}{n:>7} rows")


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(db_path()).parent / "parquet"
    print(f"converting {db_path()} -> {dest}")
    convert(db_path(), dest)
    print(f"ok: GITSKILLS_PARQUET={dest} uv run scripts/<script>.py")
