"""Posting list compression interface (FUTURE).

Planned codecs: gamma, delta, variable-byte (vbyte), Simple-9. Used to shrink
the ``postings`` table on disk and to speed up postings-list iteration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PostingCodec(ABC):
    """Encode/decode an integer posting list."""

    @abstractmethod
    def encode(self, values: list[int]) -> bytes:
        ...

    @abstractmethod
    def decode(self, blob: bytes) -> list[int]:
        ...
