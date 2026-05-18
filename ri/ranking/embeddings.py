"""Embedding-based scorer (FUTURE).

Planned: store sentence-transformer vectors in a sibling table; rank by cosine
similarity between query and document embeddings. Compose with VSM by linear
interpolation: ``score = alpha * lex + (1 - alpha) * semantic``.
"""

from __future__ import annotations

from ri.indexing.base import Index
from ri.query.ast_nodes import ParsedQuery
from ri.ranking.base import ScoredDoc, Scorer


class EmbeddingScorer(Scorer):
    """STUB. Not implemented."""

    def score(self, query: ParsedQuery, index: Index) -> list[ScoredDoc]:
        raise NotImplementedError("Embedding scorer pending — see docs/specs/")
