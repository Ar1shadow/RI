"""Abstract Scorer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ri.indexing.base import Index
from ri.query.ast_nodes import ParsedQuery

ScoredDoc = tuple[int, float]


class Scorer(ABC):
    """Compute a relevance score per matching document for a parsed query."""

    @abstractmethod
    def score(self, query: ParsedQuery, index: Index) -> list[ScoredDoc]:
        """Return ``(doc_id, score)`` pairs, descending by score."""
