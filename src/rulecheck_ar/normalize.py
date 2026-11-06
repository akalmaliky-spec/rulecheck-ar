"""Light Arabic text normalization used for matching only (never shown to users)."""

from __future__ import annotations

import re
import unicodedata

_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ـ": "",
        "\u2019": "'",
    }
)


def normalize_ar(text: str) -> str:
    """Remove diacritics and tatweel, unify letter variants, collapse whitespace, lowercase."""
    text = unicodedata.normalize("NFKC", text)
    text = _DIACRITICS.sub("", text)
    text = text.translate(_TRANSLATION)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()
