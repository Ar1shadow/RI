"""AST node dataclasses for a parsed query.

Shape:
    ParsedQuery
      ├── groups: list[KeywordGroup]   # DNF — groups OR'd, within each AND
      ├── exclusions: list[str]        # lemmatized excluded terms
      └── filters: FilterSet
            ├── rubrique: str | None
            ├── date: DateFilter | None
            └── has_image: bool | None
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KeywordGroup:
    """One AND-clause inside the top-level DNF."""

    title: list[str] = field(default_factory=list)
    content: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.title and not self.content


@dataclass
class DateFilter:
    """Date constraint.

    ``kind`` is one of ``"y" | "my" | "dmy" | "between_y" | "between_my" | "between_dmy"``.
    Single-value forms set ``value``; range forms set ``start``/``end``.
    """

    kind: str
    value: str | None = None
    start: str | None = None
    end: str | None = None


@dataclass
class FilterSet:
    rubrique: str | None = None
    date: DateFilter | None = None
    has_image: bool | None = None


@dataclass
class ParsedQuery:
    groups: list[KeywordGroup] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    filters: FilterSet = field(default_factory=FilterSet)

    def all_content_terms(self) -> list[str]:
        """Deduplicated union of all groups' content lemmas (insertion order)."""
        seen: set[str] = set()
        out: list[str] = []
        for g in self.groups:
            for t in g.content:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
        return out

    def all_title_terms(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for g in self.groups:
            for t in g.title:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
        return out
