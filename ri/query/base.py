"""Abstract QueryParser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ri.query.ast_nodes import ParsedQuery


class QueryParser(ABC):
    """Interface for natural-language query parsers."""

    @abstractmethod
    def parse(self, raw: str) -> ParsedQuery:
        """Tokenize, normalize, split logical ops, extract filters; return AST."""
