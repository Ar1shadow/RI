"""Single source of truth for text normalization.

Used by the scraper, tokenizer, anti-dict, query parser, and spell-checker.
"""

from __future__ import annotations

import unicodedata


def strip_accents(text: str) -> str:
    """Remove all combining diacritics (NFD-decompose then drop marks)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def normalize(text: str) -> str:
    """Casefold + strip accents + collapse internal whitespace.

    Returns an empty string for ``None`` input.
    """
    if not text:
        return ""
    return " ".join(strip_accents(text).casefold().split())
