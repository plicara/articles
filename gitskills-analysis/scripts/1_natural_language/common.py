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


def db_path() -> str:
    """Locate the dataset: GITSKILLS_DB wins, else data/ at the repo root."""
    override = os.environ.get("GITSKILLS_DB")
    if override:
        return override
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "agent_skills_sample.db"
        if candidate.exists():
            return str(candidate)
    raise SystemExit(
        "no dataset found -- run scripts/fetch_sample.py, or set GITSKILLS_DB"
    )


def connect(con_factory):
    """Open DuckDB with the sqlite extension loaded."""
    con = con_factory()
    con.execute("INSTALL sqlite")
    con.execute("LOAD sqlite")
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
