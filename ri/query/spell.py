"""Spell correction by common-prefix + Levenshtein distance.

Ported from TD4. The lexicon comes from the index ``vocabulary`` table; no
external TSV file is needed.

Wire this in front of :class:`FrenchQueryParser` when you want OOV tokens to
be corrected before parsing. Not currently used by the default search path —
queries in the golden set are already clean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ri.indexing.sqlite_index import SQLiteIndex
from ri.preprocessing.normalize import normalize as nfd_normalize

TOKEN_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d+(?:[.,]\d+)?"
    r"|[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
)
DATE_PATTERN = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})$")
NUMBER_PATTERN = re.compile(r"^\d+(?:[.,]\d+)?$")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.replace("’", "'"))


def is_entity(token: str) -> bool:
    return bool(DATE_PATTERN.match(token) or NUMBER_PATTERN.match(token))


def common_prefix_length(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@dataclass
class Suggestion:
    word: str
    distance: int


class Lexicon:
    """Read-only word list backed by the index ``vocabulary`` table."""

    def __init__(self, words: set[str]) -> None:
        self.words = words

    @classmethod
    def from_index(cls, index: SQLiteIndex) -> Lexicon:
        return cls(set(index.vocabulary_terms()))

    def contains(self, token: str) -> bool:
        return nfd_normalize(token) in {nfd_normalize(w) for w in self.words}

    def candidates(
        self,
        token: str,
        max_distance: int = 3,
        min_prefix: int = 2,
        proximity_ratio: float = 0.4,
    ) -> list[Suggestion]:
        token_n = nfd_normalize(token)
        out: list[Suggestion] = []
        for w in self.words:
            w_n = nfd_normalize(w)
            if abs(len(w_n) - len(token_n)) > max_distance:
                continue
            if common_prefix_length(token_n, w_n) < min_prefix:
                continue
            d = levenshtein(token_n, w_n)
            if d <= max_distance and d / max(len(token_n), 1) <= proximity_ratio + 1e-9:
                out.append(Suggestion(word=w, distance=d))
        out.sort(key=lambda s: (s.distance, s.word))
        return out


def correct_query(raw: str, lexicon: Lexicon) -> str:
    """Apply per-token correction, preserving entities and known words."""
    parts: list[str] = []
    for token in tokenize(raw):
        if is_entity(token) or lexicon.contains(token):
            parts.append(token)
            continue
        cands = lexicon.candidates(token)
        parts.append(cands[0].word if cands else token)
    return " ".join(parts)
