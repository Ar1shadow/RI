"""Default VSM scorer.

Matches the TD6 hybrid weighting:
    title clause:   ``3 * tf(titre)``
    content clause: ``3 * tf(titre) + 1 * tf(texte)``
    AND within a DNF group, OR (sum) between groups.

Implementation: build per-term per-zone ``{doc_id: tf}`` maps from postings,
combine via set intersection for AND and dict union for OR.
"""

from __future__ import annotations

from ri.config import (
    SCORE_WEIGHT_CONTENT_IN_TEXTE,
    SCORE_WEIGHT_CONTENT_IN_TITRE,
    SCORE_WEIGHT_TITLE_IN_TITRE,
)
from ri.indexing.base import Index
from ri.indexing.sqlite_index import SQLiteIndex
from ri.query.ast_nodes import KeywordGroup, ParsedQuery
from ri.ranking.base import ScoredDoc, Scorer


def _tf_map(index: SQLiteIndex, term: str, zone: str) -> dict[int, int]:
    """Return ``{doc_id: tf}`` for ``term`` in ``zone`` (empty if absent)."""
    row = index.conn.execute(
        "SELECT term_id FROM vocabulary WHERE term = ?", (term,)
    ).fetchone()
    if not row:
        return {}
    rows = index.conn.execute(
        "SELECT doc_id, tf FROM postings WHERE term_id = ? AND zone = ?",
        (row["term_id"], zone),
    ).fetchall()
    return {int(r["doc_id"]): int(r["tf"]) for r in rows}


def _score_title_clause(index: SQLiteIndex, term: str) -> dict[int, float]:
    titre = _tf_map(index, term, "titre")
    return {d: SCORE_WEIGHT_TITLE_IN_TITRE * tf for d, tf in titre.items() if tf > 0}


def _score_content_clause(index: SQLiteIndex, term: str) -> dict[int, float]:
    titre = _tf_map(index, term, "titre")
    texte = _tf_map(index, term, "texte")
    out: dict[int, float] = {}
    for d, tf in titre.items():
        out[d] = SCORE_WEIGHT_CONTENT_IN_TITRE * tf
    for d, tf in texte.items():
        out[d] = out.get(d, 0.0) + SCORE_WEIGHT_CONTENT_IN_TEXTE * tf
    return out


def _and_combine(running: dict[int, float] | None, term_scores: dict[int, float]) -> dict[int, float]:
    if running is None:
        return dict(term_scores)
    return {d: running[d] + term_scores[d] for d in running if d in term_scores}


def _score_group(index: SQLiteIndex, group: KeywordGroup) -> dict[int, float]:
    running: dict[int, float] | None = None
    for kw in group.title:
        running = _and_combine(running, _score_title_clause(index, kw))
    for kw in group.content:
        running = _and_combine(running, _score_content_clause(index, kw))
    return running or {}


class VSMScorer(Scorer):
    """Weighted-frequency scorer matching the TD6 baseline."""

    def score(self, query: ParsedQuery, index: Index) -> list[ScoredDoc]:
        if not isinstance(index, SQLiteIndex):
            raise TypeError("VSMScorer requires SQLiteIndex")
        if not query.groups:
            return []
        accum: dict[int, float] = {}
        for group in query.groups:
            for d, s in _score_group(index, group).items():
                accum[d] = accum.get(d, 0.0) + s
        return sorted(accum.items(), key=lambda x: (-x[1], x[0]))
