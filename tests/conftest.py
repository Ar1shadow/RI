"""Shared pytest fixtures.

The full corpus index is expensive to build (~30 s, 326 docs). Build once
per session and share via a session-scoped fixture.
"""

from __future__ import annotations

import pytest

from ri.config import RAW_HTML_DIR
from ri.indexing.builder import build_index
from ri.indexing.sqlite_index import SQLiteIndex


@pytest.fixture(scope="session")
def built_index(tmp_path_factory) -> SQLiteIndex:
    db = tmp_path_factory.mktemp("index") / "ri.sqlite"
    index = build_index(html_dir=RAW_HTML_DIR, db_path=db)
    yield index
    index.close()
