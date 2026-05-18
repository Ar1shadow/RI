"""Shared text helpers used by every concrete :class:`Corrector`."""

from __future__ import annotations

import re

from ri.preprocessing.normalize import normalize as _normalize

TOKEN_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d+(?:[.,]\d+)?"
    r"|[A-Za-zÀ-ÖØ-öø-ÿ]+(?:-[A-Za-zÀ-ÖØ-öø-ÿ]+)*"  # hyphenated OK; apostrophe splits
)
DATE_PATTERN = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})$")
NUMBER_PATTERN = re.compile(r"^\d+(?:[.,]\d+)?$")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.replace("’", "'"))


def tokenize_with_spans(text: str) -> list[tuple[str, int, int]]:
    """Tokenize and return ``(surface, start, end)`` triples into the input."""
    normalized = text.replace("’", "'")
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_PATTERN.finditer(normalized)]


def is_entity(token: str) -> bool:
    return bool(DATE_PATTERN.match(token) or NUMBER_PATTERN.match(token))


def normalize_token(token: str) -> str:
    return _normalize(token)


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
