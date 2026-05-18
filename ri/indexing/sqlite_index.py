"""Default SQLite-backed :class:`Index` implementation."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ri.config import DB_PATH
from ri.corpus.models import Document
from ri.indexing.base import Index, Posting

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class SQLiteIndex(Index):
    """SQLite-backed inverted index. Owns its connection lifecycle."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> SQLiteIndex:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def reset(self) -> None:
        """Drop and recreate all tables (used by builder before a fresh build)."""
        cur = self.conn.cursor()
        for tbl in ("postings", "idf", "doc_length", "vocabulary",
                    "anti_dict", "corpus_stats", "surface_forms", "documents"):
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")
        self.conn.commit()
        self._init_schema()

    def add_document(self, doc: Document) -> int:
        cur = self.conn.cursor()
        article_id = Path(doc.fichier).stem
        cur.execute(
            """INSERT INTO documents (fichier, bulletin, article, titre, auteur,
                                       date, rubrique, has_image, raw_text)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (doc.fichier, doc.bulletin, article_id, doc.titre, doc.auteur,
             doc.date, doc.rubrique, int(doc.has_image), doc.text),
        )
        assert cur.lastrowid is not None
        return cur.lastrowid

    def upsert_term(self, term: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO vocabulary(term) VALUES (?)", (term,))
        row = cur.execute("SELECT term_id FROM vocabulary WHERE term = ?", (term,)).fetchone()
        return int(row["term_id"])

    def add_posting(self, term_id: int, doc_id: int, zone: str, tf: int, tfidf: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO postings(term_id, doc_id, zone, tf, tfidf) VALUES (?,?,?,?,?)",
            (term_id, doc_id, zone, tf, tfidf),
        )

    def set_df(self, term: str, df: int) -> None:
        self.conn.execute("UPDATE vocabulary SET df = ? WHERE term = ?", (df, term))

    def set_idf(self, term_id: int, idf: float) -> None:
        self.conn.execute("INSERT OR REPLACE INTO idf(term_id, idf) VALUES (?,?)", (term_id, idf))

    def set_doc_length(self, doc_id: int, len_titre: int, len_texte: int) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO doc_length(doc_id, len_titre, len_texte) VALUES (?,?,?)",
            (doc_id, len_titre, len_texte),
        )

    def set_corpus_stat(self, key: str, value: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO corpus_stats(key, value) VALUES (?,?)", (key, value)
        )

    def set_anti_dict(self, terms: Iterable[str]) -> None:
        self.conn.execute("DELETE FROM anti_dict")
        self.conn.executemany("INSERT INTO anti_dict(term) VALUES (?)", [(t,) for t in terms])

    def commit(self) -> None:
        self.conn.commit()

    def get_postings(self, term: str, zone: str) -> list[Posting]:
        row = self.conn.execute(
            "SELECT term_id FROM vocabulary WHERE term = ?", (term,)
        ).fetchone()
        if not row:
            return []
        rows = self.conn.execute(
            "SELECT doc_id, tfidf FROM postings WHERE term_id = ? AND zone = ?",
            (row["term_id"], zone),
        ).fetchall()
        return [(int(r["doc_id"]), float(r["tfidf"])) for r in rows]

    def get_idf(self, term: str) -> float:
        row = self.conn.execute(
            """SELECT idf.idf FROM idf
               JOIN vocabulary v ON v.term_id = idf.term_id
               WHERE v.term = ?""",
            (term,),
        ).fetchone()
        return float(row["idf"]) if row else 0.0

    def all_doc_ids(self) -> set[int]:
        rows = self.conn.execute("SELECT doc_id FROM documents").fetchall()
        return {int(r["doc_id"]) for r in rows}

    def get_documents(self, doc_ids: Iterable[int]) -> list[dict[str, Any]]:
        ids = list(doc_ids)
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"""SELECT doc_id, fichier, bulletin, article, titre, auteur, date, rubrique,
                       has_image, raw_text
                FROM documents WHERE doc_id IN ({placeholders})""",
            ids,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_anti_dict(self) -> set[str]:
        rows = self.conn.execute("SELECT term FROM anti_dict").fetchall()
        return {r["term"] for r in rows}

    def vocabulary_terms(self) -> list[str]:
        rows = self.conn.execute("SELECT term FROM vocabulary ORDER BY term").fetchall()
        return [r["term"] for r in rows]

    def doc_count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"])

    def add_surface_forms(self, triples: Iterable[tuple[str, str, int]]) -> None:
        """Bulk upsert ``(surface, lemma, freq)`` triples into ``surface_forms``.

        On collision (same surface+lemma), the freq is incremented.
        """
        self.conn.executemany(
            """INSERT INTO surface_forms(surface, lemma, freq) VALUES (?, ?, ?)
               ON CONFLICT(surface, lemma) DO UPDATE SET freq = freq + excluded.freq""",
            list(triples),
        )

    def surface_form_map(self) -> dict[str, str]:
        """Return ``{surface: best_lemma}`` picking max-freq lemma per surface."""
        rows = self.conn.execute(
            """SELECT surface, lemma, freq FROM surface_forms
               ORDER BY surface, freq DESC, lemma"""
        ).fetchall()
        best: dict[str, str] = {}
        for r in rows:
            s = r["surface"]
            if s not in best:
                best[s] = r["lemma"]
        return best
