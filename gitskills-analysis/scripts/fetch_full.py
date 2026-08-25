#!/usr/bin/env python3
"""Fetch the full GitSkills corpus as Parquet, into data/.

The Zenodo release is a single 44 GB SQLite file. The HuggingFace mirror is
the same data as Parquet, which is columnar, so a query reads only the
columns it touches. That makes the full corpus about 13 GB on disk instead
of 44, and much faster to scan.

    uv run scripts/fetch_full.py               # artifacts + repos (6.5 GB)
    uv run scripts/fetch_full.py --all         # adds artifact_siblings (13.4 GB)
    uv run scripts/fetch_full.py --table repos

Resumable: a file already present at the expected size is skipped, so an
interrupted run continues where it stopped.

Streaming these over `hf://` without downloading also works and needs no
disk, but sustained anonymous reads hit HTTP 429 partway through a full
scan. Downloading once removes that as a failure mode.

Stdlib only, so it runs before any environment is set up.
"""

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = "mvaccargiu/gitskills"
REV = "refs%2Fconvert%2Fparquet"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/{REV}"
RESOLVE = f"https://huggingface.co/datasets/{REPO}/resolve/{REV}"
DATA = Path(__file__).resolve().parent.parent / "data"

# artifacts carries the skill text and commit history: everything article 01
# needs. artifact_siblings is only for the bundled-file measures (which
# programming language a skill actually ships code in), so it is opt-in.
DEFAULT = ("artifacts", "repos")
OPTIONAL = ("artifact_siblings",)


def listing(table):
    with urllib.request.urlopen(f"{API}/{table}/train", timeout=60) as r:
        return [(f["path"].split("/")[-1], f.get("size", 0))
                for f in json.load(r) if f["path"].endswith(".parquet")]


def fetch(table, name, size, dest):
    out = dest / name
    if out.exists() and out.stat().st_size == size:
        return f"  skip {table}/{name}"
    url = f"{RESOLVE}/{table}/train/{name}"
    tmp = out.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    tmp.rename(out)
    return f"  got  {table}/{name}  {out.stat().st_size / 1e6:.0f} MB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="also fetch artifact_siblings (about 7 GB more)")
    ap.add_argument("--table", action="append",
                    help="fetch only this table; repeatable")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    tables = args.table or list(DEFAULT) + (list(OPTIONAL) if args.all else [])
    plan = {t: listing(t) for t in tables}
    total = sum(s for files in plan.values() for _, s in files)
    have = sum(s for t, files in plan.items() for n, s in files
               if (DATA / t / n).exists() and (DATA / t / n).stat().st_size == s)
    print(f"{len(tables)} table(s), {sum(len(f) for f in plan.values())} files, "
          f"{total / 1e9:.2f} GB total, {have / 1e9:.2f} GB already present")

    jobs = []
    for table, files in plan.items():
        dest = DATA / table
        dest.mkdir(parents=True, exist_ok=True)
        jobs += [(table, name, size, dest) for name, size in files]

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, *j): j for j in jobs}
        for fut in as_completed(futures):
            table, name, size, _ = futures[fut]
            try:
                print(fut.result(), flush=True)
            except Exception as exc:
                print(f"  FAIL {table}/{name}: {exc}", flush=True)
                continue
            done += 1

    print(f"\n{done}/{len(jobs)} files in place")
    for table in tables:
        d = DATA / table
        n = len(list(d.glob("*.parquet"))) if d.exists() else 0
        gb = sum(f.stat().st_size for f in d.glob("*.parquet")) / 1e9 if n else 0
        print(f"  {table:<20}{n:>3} files  {gb:>6.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
