"""Round-trip parse on a real bulletin from the bundled corpus."""

from ri.config import RAW_HTML_DIR
from ri.corpus.scraper import parse_html


def test_parse_returns_populated_document():
    sample = RAW_HTML_DIR / "67068.htm"
    if not sample.exists():
        return
    doc = parse_html(sample.read_text(encoding="utf-8"), fichier=sample.name)
    assert doc.titre
    assert doc.date.startswith("2011")
    assert doc.rubrique
    assert len(doc.text) > 100
