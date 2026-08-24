#!/usr/bin/env python3
"""Fetch the GitSkills sample database into data/.

The sample holds 13,000 distinct SKILL.md contents and is schema-identical
to the full 44 GB dataset (Zenodo 10.5281/zenodo.21875637), so every query
developed against it runs unchanged at full scale. ~83 MB download,
~278 MB unzipped.
"""

import zipfile
from pathlib import Path
from urllib.request import urlretrieve

URL = (
    "https://github.com/giuseppedestefanis/gitskills-sample/raw/main/"
    "agent_skills_sample.zip"
)

dest = Path(__file__).resolve().parent.parent / "data"
dest.mkdir(parents=True, exist_ok=True)
zip_path = dest / "agent_skills_sample.zip"

print(f"downloading {URL} ...")
urlretrieve(URL, zip_path)
with zipfile.ZipFile(zip_path) as zf:
    zf.extract("agent_skills_sample.db", dest)
zip_path.unlink()
print(f"ok: {dest / 'agent_skills_sample.db'}")
