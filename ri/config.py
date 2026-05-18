"""Project-wide paths and constants.

All paths resolve relative to the repo root (parent of the `ri/` package).
Constants are intentionally module-level (no Settings class) — flat config
suits a single-deployment course project.
"""

from __future__ import annotations

from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = ROOT_DIR / "data"
RAW_HTML_DIR: Path = DATA_DIR / "raw_html"
CORPUS_XML: Path = DATA_DIR / "corpus.xml"
DB_PATH: Path = DATA_DIR / "index.sqlite"
ANTI_DICT_PATH: Path = DATA_DIR / "anti_dict.txt"

SPACY_MODEL: str = "fr_core_news_sm"

ANTI_DICT_TFIDF_THRESHOLD: float = 0.10

SCORE_WEIGHT_TITLE_IN_TITRE: float = 3.0
SCORE_WEIGHT_CONTENT_IN_TITRE: float = 3.0
SCORE_WEIGHT_CONTENT_IN_TEXTE: float = 1.0

BM25_K1: float = 1.5
BM25_B: float = 0.75
