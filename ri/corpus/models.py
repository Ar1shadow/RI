"""Document dataclass shared across corpus and indexing layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Document:
    """A single bulletin article ready for indexing.

    Attributes:
        fichier: Source HTML filename (or bulletin/article id).
        titre: Article title.
        date: ISO 8601 date string (YYYY-MM-DD) or empty.
        auteur: Author name or empty.
        rubrique: Section / category name.
        has_image: True if the source page references at least one image.
        text: Concatenated body text.
        images: Image URLs/paths found in the source.
        contact: Optional contact line.
        bulletin: Bulletin issue number or identifier.
    """

    fichier: str
    titre: str = ""
    date: str = ""
    auteur: str = ""
    rubrique: str = ""
    has_image: bool = False
    text: str = ""
    images: list[str] = field(default_factory=list)
    contact: str = ""
    bulletin: str = ""
