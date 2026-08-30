"""Shared text-cleaning and language-ID setup for the natural-language cuts.

These live in one place deliberately. The cleaning SQL was duplicated across
scripts once before and the copies drifted -- one of them omitted the 'g'
flag on regexp_replace, which silently left ~85% of fenced code in the text
the analysis treated as prose. One definition, used by every script here.
"""

import os
from pathlib import Path

from py3langid.langid import MODEL_FILE, LanguageIdentifier

CONF_FLOOR = 0.80
MAX_CHARS = 4000
MIN_PROSE = 40  # below this, a doc is code/boilerplate, not identifiable text

# Restricting the model to plausible authoring languages sharpens it, but it
# also forces anything outside the set into a listed class -- so this is a
# measurement choice, not a neutral default.
NAMES = {
    "en": "English", "es": "Spanish", "pt": "Portuguese", "fr": "French",
    "de": "German", "it": "Italian", "nl": "Dutch", "ca": "Catalan",
    "ru": "Russian", "uk": "Ukrainian", "pl": "Polish", "cs": "Czech",
    "sk": "Slovak", "sl": "Slovenian", "hr": "Croatian", "sr": "Serbian",
    "bg": "Bulgarian", "ro": "Romanian", "hu": "Hungarian", "el": "Greek",
    "tr": "Turkish", "ar": "Arabic", "he": "Hebrew", "fa": "Persian",
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "ur": "Urdu", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
    "tl": "Tagalog", "fi": "Finnish", "sv": "Swedish", "da": "Danish",
    "no": "Norwegian", "nb": "Norwegian", "nn": "Norwegian",
    "is": "Icelandic", "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian",
    "sq": "Albanian", "eu": "Basque", "gl": "Galician", "cy": "Welsh",
}

_INVISIBLE = ("'[' || chr(8203) || chr(8204) || chr(8205) "
              "|| chr(65279) || chr(173) || ']'")

# Front matter, then invisible chars, then fenced code. Every regexp_replace
# carries 'g' -- DuckDB replaces only the first match without it.
PROSE_SQL = f"""
regexp_replace(
  regexp_replace(
    regexp_replace(content, '(?s)\\A---.*?---\\r?\\n?', ' ', 'g'),
    {_INVISIBLE}, '', 'g'),
  '(?s)```.*?```', ' ', 'g')
"""


def _data_dir():
    for parent in Path(__file__).resolve().parents:
        if (parent / "data").is_dir():
            return parent / "data"
    return None


def db_path() -> str:
    """Locate the sample database: GITSKILLS_DB wins, else data/."""
    override = os.environ.get("GITSKILLS_DB")
    if override:
        return override
    data = _data_dir()
    if data and (data / "agent_skills_sample.db").exists():
        return str(data / "agent_skills_sample.db")
    raise SystemExit(
        "no dataset found -- run scripts/fetch_sample.py, or set GITSKILLS_DB"
    )


def source(table: str) -> str:
    """A SQL expression naming one dataset table, whichever form is present.

    The full corpus is Parquet, one directory per table, because the Zenodo
    SQLite release is 44 GB against 13 GB for the same data in a columnar
    format that reads only the columns a query touches. The 13,000-skill
    sample stays SQLite, so both forms have to work and every script reads
    its tables through here rather than naming a file.

    Precedence: GITSKILLS_PARQUET, then data/<table>/*.parquet, then the
    sample database. Set GITSKILLS_DB to force the sample even when the full
    corpus is present, which is what you want while iterating.
    """
    if not os.environ.get("GITSKILLS_DB"):
        root = os.environ.get("GITSKILLS_PARQUET")
        base = Path(root) if root else _data_dir()
        if base and (base / table).is_dir() and any((base / table).glob("*.parquet")):
            return f"read_parquet('{base / table}/*.parquet')"
    return f"sqlite_scan('{db_path()}', '{table}')"


def scale() -> str:
    """Which corpus is in play, for scripts that print their provenance.

    Counted, not inferred from the storage format. That inference was safe
    only while Parquet implied the full release; the sample converts to
    Parquet too (scripts/sample_to_parquet.py), so format no longer implies
    size, and a guess here would misreport provenance in the one place a
    script prints it.
    """
    import duckdb

    n = connect(duckdb.connect).execute(
        f"SELECT count(*) FROM {source('artifacts')}").fetchone()[0]
    fmt = "parquet" if "read_parquet" in source("artifacts") else "sqlite"
    return f"{n:,} artifact rows ({fmt})"


def connect(con_factory):
    """Open DuckDB, loading the sqlite extension only if the source needs it.

    That extension is downloaded from DuckDB's extension repository on first
    use, so loading it unconditionally makes every script fail on a machine
    whose egress policy blocks that repository, including runs that read
    Parquet and never touch SQLite at all. Parquet needs no extension.
    """
    con = con_factory()
    if "sqlite_scan" in source("artifacts"):
        con.execute("INSTALL sqlite")
        con.execute("LOAD sqlite")
    # At full corpus a join over 3.8M artifacts and 40M+ bundled-file rows
    # does not fit in memory and DuckDB spills. Without a temp directory on
    # the volume holding the data it spills to wherever the process started,
    # which on a small root filesystem kills the run halfway through.
    tmp = _data_dir()
    if tmp:
        con.execute(f"SET temp_directory = '{tmp / 'duckdb-tmp'}'")
        con.execute("SET preserve_insertion_order = false")
    return con


def identifier():
    ident = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    ident.set_languages(sorted(NAMES))
    return ident


def classify(ident, text):
    """Return a language code, 'uncertain', or None if there is too little prose.

    Known bias: identification keys on script and function words, so CJK is
    detected reliably while a Latin-script language carrying heavy English
    technical vocabulary can be pulled toward English. Non-English share is
    therefore a lower bound.
    """
    if len(text.strip()) < MIN_PROSE:
        return None
    lang, prob = ident.classify(text)
    return lang if prob >= CONF_FLOOR else "uncertain"


def is_non_english(code) -> bool:
    """One definition of non-English, shared by every script here.

    'uncertain' is not English, but it is not evidence of any other
    language either, so it never counts toward the non-English numerator.
    It stays in the denominator: it is a classified document whose language
    we could not pin down. Cross-sectional and trend figures must use this
    same rule or they will not be comparable to each other.
    """
    return code not in ("en", "uncertain", None)


def wilson(successes: int, n: int, z: float = 1.96):
    """95% Wilson score interval -- honest about small monthly cell counts."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
