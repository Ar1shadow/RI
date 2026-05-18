"""N-gram corrector (FUTURE).

Planned: character n-gram inverted index built over the vocabulary for
sublinear candidate retrieval; underlying storage = sibling SQLite table
``vocabulary_ngrams(ngram, term_id)``.
"""

from __future__ import annotations

from ri.correction.base import Corrector, CorrectionResult


class NgramCorrector(Corrector):
    """STUB. Not implemented."""

    def correct(self, query: str) -> CorrectionResult:
        raise NotImplementedError("NgramCorrector pending — see docs/specs/")
