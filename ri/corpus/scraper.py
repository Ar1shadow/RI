"""HTML → :class:`Document` extraction.

Single-parser strategy: only :mod:`lxml.html` (the original repo used both
BeautifulSoup and lxml; lxml alone covers every selector we need).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from lxml import html as lxml_html

from ri.corpus.models import Document

_BULLETIN_RE = re.compile(r"BE\s+\w+\s+(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_ARTICLE_RE = re.compile(r"/(\d+)\.htm$")
_AUTHOR_RE = re.compile(r"-\s*(.+?)\s*-\s*email", re.IGNORECASE)


def _first_text(tree, xpath: str) -> str:
    """Return stripped text of first node matching ``xpath`` or empty string."""
    nodes = tree.xpath(xpath)
    if not nodes:
        return ""
    node = nodes[0]
    if isinstance(node, str):
        return node.strip()
    return (node.text_content() if hasattr(node, "text_content") else str(node)).strip()


def _iso_date(raw: str) -> str:
    """Normalize ``dd/mm/yyyy`` to ``YYYY-MM-DD`` (empty if not matched)."""
    m = _DATE_RE.search(raw)
    if not m:
        return ""
    d, mo, y = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


def parse_html(content: str, fichier: str) -> Document:
    """Parse a single HTML bulletin into a :class:`Document`."""
    tree = lxml_html.fromstring(content)

    title_text = _first_text(tree, "//title")
    bulletin_match = _BULLETIN_RE.search(title_text)
    bulletin = bulletin_match.group(1) if bulletin_match else ""

    article_num = ""
    date_raw = ""
    for span in tree.xpath("//span[@class='style15']"):
        text = span.text_content()
        if not article_num:
            m = _ARTICLE_RE.search(text)
            if m:
                article_num = m.group(1)
        if not date_raw:
            m = _DATE_RE.search(text)
            if m:
                date_raw = m.group(0)
    if not article_num:
        for span in tree.xpath("//span[@class='style88']"):
            m = _ARTICLE_RE.search(span.text_content())
            if m:
                article_num = m.group(1)
                break

    rubrique = ""
    for span in tree.xpath("//span[@class='style42']"):
        text = span.text_content().strip()
        if text and not _DATE_RE.match(text):
            rubrique = text
            break

    titre = _first_text(tree, "//span[@class='style17']")

    auteur = ""
    contact = ""
    for td in tree.xpath("//td"):
        labels = td.xpath(".//span[@class='style28']")
        if not labels:
            continue
        label_text = labels[0].text_content().lower()
        next_td_list = td.xpath("following-sibling::td[1]")
        if not next_td_list:
            continue
        sibling_text = next_td_list[0].text_content()
        if not auteur and "dacteur" in label_text:
            m = _AUTHOR_RE.search(sibling_text)
            if m:
                auteur = m.group(1).strip()
        elif not contact and "contact" in label_text:
            contact = sibling_text.strip()

    images: list[str] = []
    for img in tree.xpath("//img[contains(@style, 'margin-bottom:5px')]"):
        src = img.get("src", "")
        if src:
            images.append(src)

    texte_parts = tree.xpath("//p[@class='style96']//span[@class='style95']/text()")
    texte = "".join(p for p in texte_parts if p != "\n").strip()

    return Document(
        fichier=fichier,
        titre=titre,
        date=_iso_date(date_raw),
        auteur=auteur,
        rubrique=rubrique,
        has_image=bool(images),
        text=texte,
        images=images,
        contact=contact,
        bulletin=bulletin,
    )


def iter_html_files(html_dir: str | Path) -> Iterator[Path]:
    """Yield ``.htm`` files under ``html_dir`` (case-insensitive, sorted)."""
    p = Path(html_dir)
    yield from sorted(f for f in p.rglob("*") if f.suffix.lower() == ".htm")


def scrape_directory(html_dir: str | Path, emit_xml: bool = False) -> list[Document]:
    """Parse every ``.htm`` file under ``html_dir`` into Documents.

    Args:
        html_dir: Source directory; recursed.
        emit_xml: If true, also write a debug ``corpus.xml`` at
            :data:`ri.config.CORPUS_XML`.

    Returns:
        All parsed :class:`Document` objects, ordered by filename.
    """
    docs: list[Document] = []
    for path in iter_html_files(html_dir):
        content = path.read_text(encoding="utf-8", errors="replace")
        docs.append(parse_html(content, fichier=path.name))
    if emit_xml:
        from ri.corpus.xml_writer import write_corpus_xml

        write_corpus_xml(docs)
    return docs
