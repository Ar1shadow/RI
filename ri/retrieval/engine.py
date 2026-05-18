"""SearchService — glues parser, scorer, filters, and result rendering.

The 223-line ``evaluer_metadonnees`` in TD6 is broken into:
    - one helper per filter axis (rubrique / date / image / exclusions)
    - an orchestrator (``SearchService.run``) under 50 lines.

Doc-level set algebra:
    1. Score with VSM (or any pluggable :class:`Scorer`).
    2. Intersect with filter sets.
    3. Subtract exclusion-matching doc set.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date as date_t
from datetime import datetime
from typing import Any

from ri.config import DB_PATH
from ri.indexing.sqlite_index import SQLiteIndex
from ri.query.ast_nodes import DateFilter, ParsedQuery
from ri.query.parser import FrenchQueryParser
from ri.ranking.base import Scorer
from ri.ranking.vsm import VSMScorer

_MOIS_FR = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12,
}


def _parse_dmy(raw: str) -> date_t | None:
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %m %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw, re.IGNORECASE)
    if m:
        month = _MOIS_FR.get(m.group(2).lower())
        if month:
            try:
                return date_t(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass
    return None


def _parse_my(raw: str) -> tuple[int, int] | None:
    raw = raw.strip()
    for fmt in ("%m/%Y", "%m-%Y", "%m %Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.month, dt.year
        except ValueError:
            continue
    m = re.match(r"(\w+)\s+(\d{4})", raw, re.IGNORECASE)
    if m:
        month = _MOIS_FR.get(m.group(1).lower())
        if month:
            return month, int(m.group(2))
    return None


def _docs_for_rubric(index: SQLiteIndex, rubrique: str) -> set[int]:
    rows = index.conn.execute(
        "SELECT doc_id FROM documents WHERE lower(rubrique) = lower(?)", (rubrique,)
    ).fetchall()
    return {int(r["doc_id"]) for r in rows}


def _docs_for_date(index: SQLiteIndex, df: DateFilter) -> set[int]:
    rows = index.conn.execute("SELECT doc_id, date FROM documents WHERE date != ''").fetchall()
    out: set[int] = set()
    if df.kind == "y" and df.value:
        target = df.value
        for r in rows:
            if r["date"][:4] == target:
                out.add(int(r["doc_id"]))
        return out
    if df.kind == "between_y" and df.start and df.end:
        start, end = int(df.start), int(df.end)
        for r in rows:
            try:
                y = int(r["date"][:4])
                if start <= y <= end:
                    out.add(int(r["doc_id"]))
            except ValueError:
                continue
        return out
    if df.kind == "dmy" and df.value:
        target = _parse_dmy(df.value)
        if target is None:
            return out
        target_iso = target.isoformat()
        for r in rows:
            if r["date"] == target_iso:
                out.add(int(r["doc_id"]))
        return out
    if df.kind == "between_dmy" and df.start and df.end:
        start, end = _parse_dmy(df.start), _parse_dmy(df.end)
        if not (start and end):
            return out
        for r in rows:
            try:
                d = date_t.fromisoformat(r["date"])
                if start <= d <= end:
                    out.add(int(r["doc_id"]))
            except ValueError:
                continue
        return out
    if df.kind == "my" and df.value:
        my = _parse_my(df.value)
        if my is None:
            return out
        month, year = my
        for r in rows:
            try:
                d = date_t.fromisoformat(r["date"])
                if d.year == year and d.month == month:
                    out.add(int(r["doc_id"]))
            except ValueError:
                continue
        return out
    if df.kind == "between_my" and df.start and df.end:
        s_my, e_my = _parse_my(df.start), _parse_my(df.end)
        if not (s_my and e_my):
            return out
        start = date_t(s_my[1], s_my[0], 1)
        end_month = e_my[0]
        end_year = e_my[1]
        end_day = 31 if end_month in {1, 3, 5, 7, 8, 10, 12} else (29 if end_month == 2 else 30)
        end = date_t(end_year, end_month, end_day)
        for r in rows:
            try:
                d = date_t.fromisoformat(r["date"])
                if start <= d <= end:
                    out.add(int(r["doc_id"]))
            except ValueError:
                continue
        return out
    return out


def _docs_for_image(index: SQLiteIndex, has_image: bool) -> set[int]:
    rows = index.conn.execute(
        "SELECT doc_id FROM documents WHERE has_image = ?", (1 if has_image else 0,)
    ).fetchall()
    return {int(r["doc_id"]) for r in rows}


def _docs_matching_exclusions(index: SQLiteIndex, exclusions: Sequence[str]) -> set[int]:
    out: set[int] = set()
    for term in exclusions:
        row = index.conn.execute(
            "SELECT term_id FROM vocabulary WHERE term = ?", (term,)
        ).fetchone()
        if not row:
            continue
        rows = index.conn.execute(
            "SELECT DISTINCT doc_id FROM postings WHERE term_id = ?", (row["term_id"],)
        ).fetchall()
        out.update(int(r["doc_id"]) for r in rows)
    return out


class SearchService:
    """Search facade — owns an Index, a parser, and a scorer."""

    def __init__(
        self,
        index: SQLiteIndex | None = None,
        scorer: Scorer | None = None,
    ) -> None:
        self.index = index or SQLiteIndex(DB_PATH)
        self.parser = FrenchQueryParser(self.index)
        self.scorer = scorer or VSMScorer()

    def close(self) -> None:
        self.index.close()

    def run(self, raw_query: str, mode: str = "classe") -> list[dict[str, Any]]:
        """Return matching documents ordered by ``mode`` (``classe``: score; ``booleen``: date desc)."""
        parsed = self.parser.parse(raw_query)
        ranked = self.scorer.score(parsed, self.index)
        scored = dict(ranked)
        candidates = set(scored.keys()) if scored else self.index.all_doc_ids()

        for keep in self._filter_sets(parsed):
            candidates &= keep

        if parsed.exclusions:
            candidates -= _docs_matching_exclusions(self.index, parsed.exclusions)

        if not candidates:
            return []

        docs = self.index.get_documents(candidates)
        for d in docs:
            d["score"] = float(scored.get(int(d["doc_id"]), 0.0))
        if mode == "booleen":
            docs.sort(key=lambda d: d.get("date", ""), reverse=True)
        else:
            docs.sort(key=lambda d: (-d["score"], d.get("date", "")), reverse=False)
            docs.sort(key=lambda d: d["score"], reverse=True)
        return docs

    def _filter_sets(self, parsed: ParsedQuery) -> list[set[int]]:
        out: list[set[int]] = []
        f = parsed.filters
        if f.rubrique:
            out.append(_docs_for_rubric(self.index, f.rubrique))
        if f.date:
            out.append(_docs_for_date(self.index, f.date))
        if f.has_image is not None:
            out.append(_docs_for_image(self.index, f.has_image))
        return out


def run_single_query(raw: str, mode: str = "classe") -> None:
    """Print results for one query (used by ``ri query <text>``)."""
    svc = SearchService()
    try:
        docs = svc.run(raw, mode=mode)
        if not docs:
            print("(aucun résultat)")
            return
        for d in docs[:20]:
            print(f"[{d['score']:6.2f}] {d['article']:>8}  {d['date']}  {d['rubrique']:<20} | {d['titre']}")
    finally:
        svc.close()


def run_query_repl() -> None:
    """Interactive REPL — ``/mode booleen``, ``/mode classe``, ``/quitter``."""
    svc = SearchService()
    mode = "classe"
    print("RI search REPL — /mode booleen | /mode classe | /quitter")
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line == "/quitter":
                break
            if line.startswith("/mode "):
                mode = line.split()[1] if len(line.split()) > 1 else mode
                print(f"(mode = {mode})")
                continue
            docs = svc.run(line, mode=mode)
            if not docs:
                print("(aucun résultat)")
                continue
            for d in docs[:10]:
                print(f"[{d['score']:6.2f}] {d['article']:>8}  {d['date']}  {d['rubrique']:<20} | {d['titre']}")
    finally:
        svc.close()
