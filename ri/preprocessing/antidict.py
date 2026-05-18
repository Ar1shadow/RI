"""Anti-dictionary (stop-word list) construction and application.

Selection rule: any lemma whose max-over-documents TF-IDF score is at or below
:data:`ri.config.ANTI_DICT_TFIDF_THRESHOLD` is treated as noise. Matches the
TD3/2_1 behavior; values are produced once at index-build time.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ri.config import ANTI_DICT_PATH, ANTI_DICT_TFIDF_THRESHOLD


def select_anti_terms(tfidf_max: dict[str, float], threshold: float | None = None) -> set[str]:
    """Return the set of lemmas whose max TF-IDF score is at or below the threshold."""
    cutoff = ANTI_DICT_TFIDF_THRESHOLD if threshold is None else threshold
    return {term for term, score in tfidf_max.items() if score <= cutoff}


def write_anti_dict(terms: Iterable[str], path: Path | None = None) -> Path:
    """Write the anti-dictionary one term per line."""
    out = path or ANTI_DICT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    sorted_terms = sorted(set(terms))
    out.write_text("\n".join(sorted_terms) + "\n", encoding="utf-8")
    return out


def load_anti_dict(path: Path | None = None) -> set[str]:
    """Read an anti-dictionary file; returns empty set if file is missing."""
    src = path or ANTI_DICT_PATH
    if not src.exists():
        return set()
    return {line.strip() for line in src.read_text(encoding="utf-8").splitlines() if line.strip()}


def filter_terms(terms: Iterable[str], anti: set[str]) -> list[str]:
    """Drop terms that appear in ``anti``."""
    return [t for t in terms if t not in anti]
