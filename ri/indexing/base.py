"""Abstract Index interface.

Concrete backends implement read/write paths over postings, IDF, and document
metadata. The default backend is :class:`ri.indexing.sqlite_index.SQLiteIndex`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

Posting = tuple[int, float]


class Index(ABC):
    """Interface for an inverted index backend."""

    @abstractmethod
    def add_document(self, doc: Any) -> int:
        """Insert a document; returns assigned ``doc_id``."""

    @abstractmethod
    def get_postings(self, term: str, zone: str) -> list[Posting]:
        """Return ``(doc_id, tfidf)`` postings for ``term`` in ``zone``."""

    @abstractmethod
    def get_idf(self, term: str) -> float:
        """IDF for ``term``; 0.0 if absent from vocabulary."""

    @abstractmethod
    def all_doc_ids(self) -> set[int]:
        """Set of all document ids in the index."""

    @abstractmethod
    def get_documents(self, doc_ids: Iterable[int]) -> list[dict[str, Any]]:
        """Fetch document rows by id (titre, auteur, date, rubrique, has_image, raw_text)."""
