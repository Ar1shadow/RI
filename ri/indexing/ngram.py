"""N-gram index (FUTURE).

Planned: character or word n-gram postings stored in a sibling SQLite table
``ngram_postings(ngram, doc_id, tf)``. Useful for fuzzy substring matching and
language-model-style smoothing on top of the unigram index.
"""

from __future__ import annotations

from typing import Any

from ri.indexing.base import Index


class NgramIndex(Index):
    """STUB. Not implemented."""

    def add_document(self, doc: Any) -> int:
        raise NotImplementedError("NgramIndex pending — see docs/specs/")

    def get_postings(self, term: str, zone: str) -> list[tuple[int, float]]:
        raise NotImplementedError

    def get_idf(self, term: str) -> float:
        raise NotImplementedError

    def all_doc_ids(self) -> set[int]:
        raise NotImplementedError

    def get_documents(self, doc_ids):
        raise NotImplementedError
