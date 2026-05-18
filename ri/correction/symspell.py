"""SymSpell corrector (FUTURE).

Planned: Garbe-style symmetric-delete dictionary mapping each delete variant
to the original word. Lookup cost O(query_deletes); storage in a SQLite
``delete_variants(variant, lemma)`` table or in-memory dict loaded once.
"""

from __future__ import annotations

from ri.correction.base import Corrector, CorrectionResult


class SymSpellCorrector(Corrector):
    """STUB. Not implemented."""

    def correct(self, query: str) -> CorrectionResult:
        raise NotImplementedError("SymSpellCorrector pending — see docs/specs/")
