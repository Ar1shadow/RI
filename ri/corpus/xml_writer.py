"""Optional debug-only writer for ``corpus.xml``.

The canonical store is SQLite. This writer exists so a human can inspect the
scraped corpus in a text editor when something looks wrong.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from ri.config import CORPUS_XML
from ri.corpus.models import Document


def _add_text(parent: ET.Element, tag: str, text: str) -> None:
    ET.SubElement(parent, tag).text = text or ""


def write_corpus_xml(docs: Iterable[Document], path: Path | None = None) -> Path:
    """Serialize ``docs`` to a pretty-printed XML file."""
    root = ET.Element("corpus")
    for doc in docs:
        node = ET.SubElement(root, "document")
        _add_text(node, "fichier", doc.fichier)
        _add_text(node, "bulletin", doc.bulletin)
        _add_text(node, "date", doc.date)
        _add_text(node, "rubrique", doc.rubrique)
        _add_text(node, "titre", doc.titre)
        _add_text(node, "auteur", doc.auteur)
        _add_text(node, "texte", doc.text)
        images_node = ET.SubElement(node, "images")
        for src in doc.images:
            _add_text(images_node, "image", src)
        _add_text(node, "contact", doc.contact)
        _add_text(node, "has_image", "1" if doc.has_image else "0")

    xml_str = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="    ")
    out_path = path or CORPUS_XML
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(pretty, encoding="utf-8")
    return out_path
