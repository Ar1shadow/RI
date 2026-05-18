"""Embedding-based corrector (FUTURE).

Planned: char-CNN or fastText subword vectors per vocabulary lemma; rank by
cosine similarity over a numpy matrix. Vectors file referenced from
``corpus_stats``; no SQLite schema change required.
"""

from __future__ import annotations

from ri.correction.base import Corrector, CorrectionResult


class EmbeddingCorrector(Corrector):
    """STUB. Not implemented."""

    def correct(self, query: str) -> CorrectionResult:
        raise NotImplementedError("EmbeddingCorrector pending — see docs/specs/")
