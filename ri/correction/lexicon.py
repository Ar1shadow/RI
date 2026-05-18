"""Lexicon backing the default Levenshtein corrector.

A :class:`SurfaceLexicon` stores normalized surface → lemma mappings plus a
precomputed set for O(1) membership. Built from the SQLite ``surface_forms``
table, with optional metadata seeds (rubrique names, vocabulary lemmas).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ri.correction.text import normalize_token
from ri.indexing.sqlite_index import SQLiteIndex


class SurfaceLexicon:
    """Surface → lemma map with O(1) ``contains`` and stable iteration.

    Also tracks the set of valid lemmas, so a query token whose spaCy lemma
    matches a corpus lemma can be accepted as ``valide`` even if its surface
    form was never seen in the corpus.
    """

    def __init__(
        self,
        entries: dict[str, str],
        lemma_vocab: set[str] | None = None,
    ) -> None:
        self._entries: dict[str, str] = {
            normalize_token(s): l for s, l in entries.items() if normalize_token(s)
        }
        self._normalized_set: set[str] = set(self._entries.keys())
        self._normalized_words: list[str] = sorted(self._normalized_set)
        self._lemma_vocab: set[str] = {
            normalize_token(t) for t in (lemma_vocab or set()) if normalize_token(t)
        }

    @classmethod
    def from_index(cls, index: SQLiteIndex) -> SurfaceLexicon:
        """Build from ``surface_forms`` + backstop with vocabulary lemmas."""
        surface_to_lemma = dict(index.surface_form_map())
        vocab = set(index.vocabulary_terms())
        for term in vocab:
            surface_to_lemma.setdefault(term, term)
        return cls(surface_to_lemma, lemma_vocab=vocab)

    # Query control words used by the parser as literal pattern anchors.
    # Must never be auto-corrected (would break filter/title extraction).
    QUERY_CONTROL_WORDS: tuple[str, ...] = (
        "rubrique", "rubriques", "titre", "titres", "article", "articles",
        "contient", "contiennent", "contenant", "evoque", "evoquant",
        "parle", "parlent", "parlant", "parler",
        "traite", "traitent", "traitant", "traiter",
        "mentionne", "mentionnent", "mentionnant", "mentionner",
        "concerne", "concernent", "porte", "portent", "portant",
        "implique", "impliquent", "impliquant", "impliquer",
        "mot", "mots", "terme", "termes",
        "entre", "et", "ou", "sans", "non", "pas", "mais", "dont",
        "qui", "que", "des", "du", "de", "la", "le", "les", "un", "une",
        "il", "ils", "elle", "elles", "se", "son", "sa", "ses",
        "image", "images", "avec", "sur", "dans", "pour", "par",
        "veux", "voudrais", "vouloir", "afficher", "liste", "donner",
        "trouver", "chercher", "obtenir", "recuperer", "presenter",
        "datant", "publie", "publies", "publiee", "publiees", "paru", "parus",
        "annee", "annees", "mois", "jour", "jours", "an", "ans",
        "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre",
        "depuis", "apres", "avant", "partir", "date", "dates",
        "ce", "cette", "ces", "tout", "tous", "toute", "toutes",
        "comme", "ainsi", "deux", "trois", "premier", "premiere",
        "auteur", "auteurs", "redacteur", "redacteurs", "redactrice",
    )

    @classmethod
    def from_index_with_metadata(cls, index: SQLiteIndex) -> SurfaceLexicon:
        """Same as :meth:`from_index` but also seeds rubriques and authors.

        Keeps multi-word rubrique tokens like ``"focus"`` from being mis-corrected
        when the parser hasn't yet stripped the filter prefix.
        """
        surface_to_lemma = dict(index.surface_form_map())
        vocab = set(index.vocabulary_terms())
        for term in vocab:
            surface_to_lemma.setdefault(term, term)
        for col in ("rubrique", "auteur"):
            rows = index.conn.execute(
                f"SELECT DISTINCT {col} FROM documents WHERE {col} IS NOT NULL AND {col} != ''"
            ).fetchall()
            for r in rows:
                value = r[col] or ""
                for piece in value.split():
                    piece_norm = piece.strip()
                    if piece_norm:
                        surface_to_lemma.setdefault(piece_norm.lower(), piece_norm.lower())
        for w in cls.QUERY_CONTROL_WORDS:
            surface_to_lemma.setdefault(w, w)
        return cls(surface_to_lemma, lemma_vocab=vocab)

    def contains(self, token: str) -> bool:
        return normalize_token(token) in self._normalized_set

    def lemma_for(self, token: str) -> str | None:
        return self._entries.get(normalize_token(token))

    def lemma_in_vocab(self, lemma: str) -> bool:
        """Check if a lemma exists in the corpus vocabulary (O(1))."""
        return normalize_token(lemma) in self._lemma_vocab

    def iter_words(self) -> Iterator[str]:
        return iter(self._normalized_words)

    def __len__(self) -> int:
        return len(self._entries)
