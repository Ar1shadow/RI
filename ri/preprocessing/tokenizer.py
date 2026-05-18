"""Tokenization and lemmatization wrapper over spaCy.

The spaCy model is loaded lazily and cached at module level so callers don't
need to think about pipeline cost.
"""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language

from ri.config import SPACY_MODEL


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Return a cached spaCy fr pipeline (downloads model if missing is left to user)."""
    return spacy.load(SPACY_MODEL)


def lemmatize(text: str) -> list[str]:
    """Return lower-cased lemmas of ``text`` (drops punctuation and whitespace)."""
    if not text:
        return []
    nlp = get_nlp()
    return [
        token.lemma_.lower()
        for token in nlp(text)
        if not token.is_space and not token.is_punct
    ]


def lemmatize_keep_text(text: str) -> list[tuple[str, str]]:
    """Return ``(surface, lemma)`` pairs (alpha tokens only)."""
    if not text:
        return []
    nlp = get_nlp()
    return [
        (token.text.lower(), token.lemma_.lower())
        for token in nlp(text)
        if token.is_alpha
    ]
