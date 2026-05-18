"""End-to-end index builder.

Pipeline:
    1. Scrape HTML directory into Documents.
    2. Lemmatize ``titre`` and ``texte`` per Document (zone-tagged token streams).
    3. Compute document frequency per term, then ``(1+log10(tf)) * log10(N/df)``.
    4. Persist documents, vocabulary, postings, idf, doc_length, corpus_stats.
    5. Build anti-dict from per-term max TF-IDF below
       :data:`ri.config.ANTI_DICT_TFIDF_THRESHOLD` and store it.
"""

from __future__ import annotations

from collections import Counter
from math import log10
from pathlib import Path

from ri.config import (
    ANTI_DICT_PATH,
    ANTI_DICT_TFIDF_THRESHOLD,
    DB_PATH,
    RAW_HTML_DIR,
)
from ri.corpus.scraper import scrape_directory
from ri.indexing.sqlite_index import SQLiteIndex
from ri.preprocessing.antidict import load_anti_dict
from ri.preprocessing.tokenizer import lemmatize

ZONES = ("titre", "texte")


def _doc_term_counts(doc) -> dict[str, Counter[str]]:
    """Return per-zone ``Counter[term]`` for one Document."""
    return {
        "titre": Counter(lemmatize(doc.titre)),
        "texte": Counter(lemmatize(doc.text)),
    }


def build_index(
    html_dir: Path | str | None = None,
    db_path: Path | str | None = None,
    threshold: float = ANTI_DICT_TFIDF_THRESHOLD,
) -> SQLiteIndex:
    """Build the SQLite index from scratch and return a connected handle."""
    src_dir = Path(html_dir) if html_dir else RAW_HTML_DIR
    print(f"[build] scraping {src_dir}")
    docs = scrape_directory(src_dir)
    print(f"[build] {len(docs)} documents — lemmatizing")

    per_doc_zone_counts: dict[int, dict[str, Counter[str]]] = {}
    df: Counter[str] = Counter()  # doc frequency per term
    max_tfidf: dict[str, float] = {}

    index = SQLiteIndex(db_path)
    index.reset()
    for doc in docs:
        doc_id = index.add_document(doc)
        zone_counts = _doc_term_counts(doc)
        per_doc_zone_counts[doc_id] = zone_counts
        seen_terms_this_doc: set[str] = set()
        for zone in ZONES:
            seen_terms_this_doc.update(zone_counts[zone].keys())
        for term in seen_terms_this_doc:
            df[term] += 1

    n_docs = len(docs)
    print(f"[build] vocabulary size {len(df)} — computing TF-IDF")

    for term, df_val in df.items():
        term_id = index.upsert_term(term)
        index.set_df(term, df_val)
        idf = log10(n_docs / df_val) if df_val > 0 else 0.0
        index.set_idf(term_id, idf)

    idf_cache: dict[str, float] = {
        term: log10(n_docs / df_val) if df_val > 0 else 0.0
        for term, df_val in df.items()
    }
    term_id_cache: dict[str, int] = {term: index.upsert_term(term) for term in df}

    sum_len_titre = 0
    sum_len_texte = 0
    for doc_id, zone_counts in per_doc_zone_counts.items():
        len_titre = sum(zone_counts["titre"].values())
        len_texte = sum(zone_counts["texte"].values())
        sum_len_titre += len_titre
        sum_len_texte += len_texte
        index.set_doc_length(doc_id, len_titre, len_texte)
        for zone in ZONES:
            for term, tf in zone_counts[zone].items():
                idf = idf_cache.get(term, 0.0)
                tfidf = (1 + log10(tf)) * idf if idf else 0.0
                index.add_posting(term_id_cache[term], doc_id, zone, tf, tfidf)
                if tfidf > max_tfidf.get(term, float("-inf")):
                    max_tfidf[term] = tfidf

    index.set_corpus_stat("N", float(n_docs))
    index.set_corpus_stat("avg_len_titre", sum_len_titre / n_docs if n_docs else 0.0)
    index.set_corpus_stat("avg_len_texte", sum_len_texte / n_docs if n_docs else 0.0)

    seed_terms = load_anti_dict(ANTI_DICT_PATH)
    dynamic_terms = {term for term, score in max_tfidf.items() if score <= threshold}
    anti_terms = seed_terms | dynamic_terms
    index.set_anti_dict(anti_terms)
    index.commit()
    print(
        f"[build] anti-dict size {len(anti_terms)} "
        f"(seed {len(seed_terms)} + dynamic {len(dynamic_terms - seed_terms)})"
    )
    print(f"[build] wrote {db_path or DB_PATH}")
    return index
