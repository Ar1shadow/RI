"""BM25 scorer (FUTURE).

Reads ``doc_length.len_titre/len_texte`` and ``corpus_stats.avg_len_*`` from
the index. Parameters ``k1`` and ``b`` come from :mod:`ri.config`. Multi-zone
extension: compute BM25F by weighting per-zone term frequencies before the
saturation function.
"""

from __future__ import annotations

from ri.indexing.base import Index
from ri.query.ast_nodes import ParsedQuery
from ri.ranking.base import ScoredDoc, Scorer


class BM25Scorer(Scorer):
    """STUB. Not implemented."""

    def score(self, query: ParsedQuery, index: Index) -> list[ScoredDoc]:
        raise NotImplementedError("BM25 pending — see docs/specs/")
