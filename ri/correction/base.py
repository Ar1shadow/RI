"""Corrector ABC + result dataclasses.

Concrete strategies live in sibling modules (``levenshtein``, ``ngram``,
``symspell``, ``embedding``). The ABC mandates only that a corrector turn a
raw query string into a :class:`CorrectionResult` — each strategy picks its
own lexicon storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

Status = Literal[
    "entite",
    "valide",
    "introuvable",
    "corrige-candidat-unique",
    "corrige-levenshtein",
]


@dataclass(frozen=True)
class Suggestion:
    """Minimal record for top-K consumers."""

    word: str
    distance: int


@dataclass(frozen=True)
class Candidate:
    """TD4-faithful rich candidate record."""

    word: str
    lemma: str
    prefix_len: int
    prefix_ratio: float
    distance: int


@dataclass(frozen=True)
class TokenAnalysis:
    token: str
    status: Status
    correction: str | None
    lemma: str | None
    candidates: list[Candidate] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectionResult:
    tokens: list[TokenAnalysis]
    corrected_query: str
    lemmatized_query: str


class Corrector(ABC):
    """Strategy interface for query spell correction."""

    @abstractmethod
    def correct(self, query: str) -> CorrectionResult: ...
