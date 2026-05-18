"""Natural-language query parser.

Pipeline (matches TD5):
    1. Normalize text (compact whitespace, extract upper-case acronyms).
    2. Extract global filters: rubrique, date, image.
    3. Strip "les articles ..." prefix.
    4. Split on logical operators (et / ou / sans / mais pas / non pas), recursive.
    5. Classify each fragment into title group, content group, exclusion, or
       leftover. Build DNF groups; ``ou`` opens a fresh group.
    6. Lemmatize content fragments (titles stay raw — they target the index
       ``titre`` zone which keeps surface lemmas).
"""

from __future__ import annotations

import re

from ri.indexing.sqlite_index import SQLiteIndex
from ri.preprocessing.normalize import strip_accents
from ri.preprocessing.tokenizer import lemmatize
from ri.query.ast_nodes import DateFilter, FilterSet, KeywordGroup, ParsedQuery
from ri.query.base import QueryParser
from ri.query.patterns import (
    BETWEEN_DMY,
    BETWEEN_MY,
    BETWEEN_Y,
    DMY_NUM_RAW_RE,
    DMY_NUM_RE,
    DMY_TXT_RAW_RE,
    DMY_TXT_RE,
    IMAGE,
    LOGICAL_OP,
    MY_NUM_RAW_RE,
    MY_NUM_RE,
    MY_TXT_RAW_RE,
    MY_TXT_RE,
    NEGATIVE_THEME,
    RUBRIQUE,
    THEME_TRIGGER,
    TITLE_CONTAINS,
    WITHOUT_IMAGE,
    Y_RAW_RE,
    Y_RE,
)


def normalize_query(source: str) -> tuple[str, list[str]]:
    """Compact whitespace, strip ``?``, extract upper-case acronym list."""
    cleaned = re.sub(r"\s+", " ", source.replace("?", " ")).strip()
    words = re.findall(r"\b\w+\b", cleaned)
    acronyms = [w for w in words if any(c.isalpha() for c in w) and w.isupper()]
    return cleaned, acronyms


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" ,\"'")).strip()


def _strip_theme_prefix(theme: str) -> str:
    """Drop leading articles and ``les mots/termes`` markers."""
    theme = _clean_value(theme)
    theme = re.sub(r"^(?:les?\s+mots?\b|les?\s+termes?\b)\s*", "", theme, flags=re.IGNORECASE)
    theme = re.sub(
        r"^(des|du|de la|de l['']|d['']|de|les|la|le|l[''])\s*",
        "",
        theme,
        flags=re.IGNORECASE,
    )
    theme = re.sub(r"\bles?\s+mots?\s+|\bles?\s+termes?\s+", " ", theme, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", theme).strip()


def _strip_articles_prefix(source: str) -> str:
    """Drop everything up to and including the first ``article(s)`` token."""
    m = re.search(r"\barticles?\b", source, re.IGNORECASE)
    return source[m.end():].strip(" ,") if m else source.strip()


def _mask_date_ranges(source: str) -> str:
    """Blank out date ranges to keep ``entre X et Y`` from being split."""
    masked = source
    for pattern in (BETWEEN_DMY, BETWEEN_MY, BETWEEN_Y):
        masked = pattern.sub(lambda m: " " * (m.end() - m.start()), masked)
    return masked


def _is_temporal(part: str) -> bool:
    text = _clean_value(part.lower())
    if not text:
        return False
    if BETWEEN_DMY.search(text) or BETWEEN_MY.search(text) or BETWEEN_Y.search(text):
        return True
    if DMY_NUM_RE.search(text) or DMY_TXT_RE.search(text):
        return True
    if MY_NUM_RE.search(text) or MY_TXT_RE.search(text):
        return True
    if Y_RE.search(text):
        markers = ("mois", "annee", "an", "apres", "avant", "depuis", "partir", "date", "publie")
        if any(re.search(r"\b" + m + r"\b", text) for m in markers):
            return True
    return False


_DATE_PRIORITY = [
    (BETWEEN_DMY, lambda m: DateFilter("between_dmy", start=m.group("start"), end=m.group("end"))),
    (BETWEEN_MY, lambda m: DateFilter("between_my", start=m.group("start"), end=m.group("end"))),
    (BETWEEN_Y, lambda m: DateFilter("between_y", start=m.group("start"), end=m.group("end"))),
    (DMY_NUM_RAW_RE, lambda m: DateFilter("dmy", value=m.group(0))),
    (DMY_TXT_RAW_RE, lambda m: DateFilter("dmy", value=m.group(0))),
    (MY_NUM_RAW_RE, lambda m: DateFilter("my", value=m.group(0))),
    (MY_TXT_RAW_RE, lambda m: DateFilter("my", value=m.group(0))),
    (Y_RAW_RE, lambda m: DateFilter("y", value=m.group(0))),
]


def extract_global_filters(
    source: str, known_rubrics: list[str]
) -> tuple[str, FilterSet]:
    """Pull rubrique, date, and image filters from ``source`` in a single sweep."""
    filters = FilterSet()

    m = WITHOUT_IMAGE.search(source)
    if m:
        filters.has_image = False
        source = source[:m.start()] + source[m.end():]
    else:
        m = IMAGE.search(source)
        if m:
            filters.has_image = True
            source = source[:m.start()] + source[m.end():]

    for pattern, builder in _DATE_PRIORITY:
        m = pattern.search(source)
        if m:
            filters.date = builder(m)
            break

    m = RUBRIQUE.search(source)
    if m:
        raw = _clean_value(m.group("rubrique")).lower()
        if raw:
            raw_norm = strip_accents(raw)
            matched: str | None = None
            for r in known_rubrics:
                if raw_norm.startswith(strip_accents(r).lower()):
                    matched = r
                    break
            filters.rubrique = matched or raw
        source = RUBRIQUE.sub("", source)

    source = re.sub(r"\s+", " ", source).strip()
    return source, filters


def split_logical(source: str) -> tuple[list[str], list[str]]:
    """Recursive descent: split on ``et|ou|sans|mais pas|non pas``."""
    text = source.strip()
    if not text:
        return [], []
    masked = _mask_date_ranges(text)
    m = LOGICAL_OP.search(masked)
    if m is None:
        return [text.strip()], []
    left, right = text[:m.start()].strip(" ,"), text[m.end():].strip(" ,")
    operator = m.group(0).lower()
    parts_l, ops_l = split_logical(left)
    parts_r, ops_r = split_logical(right)
    return parts_l + parts_r, ops_l + [operator] + ops_r


def _extract_theme(part: str, prev_kind: str | None) -> str | None:
    if _is_temporal(part):
        return None
    part = re.sub(r"^(?:non\s+pas|pas)\s+", "", part.strip(), flags=re.IGNORECASE)
    m = THEME_TRIGGER.search(part)
    if m:
        theme = _strip_theme_prefix(m.group("theme"))
        return theme or None
    if prev_kind in {"theme", "theme_exclu"}:
        m2 = re.search(r"\b(?:des|de l[''']|de la|de|du|d['''])\s*(.+)$", part, re.IGNORECASE)
        if m2:
            theme = _strip_theme_prefix(m2.group(1))
            return theme or None
    return _clean_value(part)


def _extract_negative_theme(part: str) -> str | None:
    m = NEGATIVE_THEME.search(part.strip())
    if not m:
        return None
    theme = _strip_theme_prefix(m.group("theme"))
    return theme or None


def _clean_title_suite(part: str) -> str:
    part = _clean_value(part)
    part = re.sub(r"^(?:et|ou)\s+", "", part, flags=re.IGNORECASE)
    part = re.sub(r"^(?:le|les)\s+(?:mot|mots|terme|termes)\s*", "", part, flags=re.IGNORECASE)
    return _clean_value(part)


def _clean_theme_suite(part: str) -> str:
    part = _clean_value(part)
    part = re.sub(r"^(?:et|ou)\s+", "", part, flags=re.IGNORECASE)
    return _clean_value(_strip_theme_prefix(part))


def build_dnf(parts: list[str], ops: list[str]) -> tuple[list[KeywordGroup], list[str]]:
    """Classify parts into DNF groups + exclusion list.

    Returns ``(groups, exclusions)``. A new group opens whenever the operator
    preceding a positive clause is ``ou``.
    """
    groups: list[KeywordGroup] = []
    current = KeywordGroup()
    exclusions: list[str] = []
    prev_kind: str | None = None

    def flush() -> None:
        nonlocal current
        if not current.is_empty():
            groups.append(current)
            current = KeywordGroup()

    def maybe_flush_for_or(is_or: bool) -> None:
        if is_or and not current.is_empty():
            flush()

    for i, raw_part in enumerate(parts):
        part = raw_part.strip()
        if not part:
            continue
        prev_op = ops[i - 1] if 0 < i <= len(ops) else None
        is_negative = prev_op in {"sans", "mais pas", "non pas", "et non pas"}
        is_or = prev_op == "ou"

        if _is_temporal(part):
            prev_kind = None
            continue

        tc = TITLE_CONTAINS.search(part)
        if tc:
            title = _clean_value(tc.group("value"))
            if title:
                maybe_flush_for_or(is_or)
                current.title.append(title)
            prev_kind = "title"
            continue

        neg = _extract_negative_theme(part)
        if neg:
            exclusions.append(neg)
            prev_kind = "theme_exclu"
            continue

        theme = _extract_theme(part, prev_kind)
        if theme and theme != part:
            if is_negative:
                exclusions.append(theme)
                prev_kind = "theme_exclu"
            else:
                maybe_flush_for_or(is_or)
                current.content.append(theme)
                prev_kind = "theme"
            continue

        if prev_kind == "title" and prev_op in {"et", "ou"}:
            cont = _clean_title_suite(part)
            if cont:
                maybe_flush_for_or(is_or)
                current.title.append(cont)
                continue
            prev_kind = None

        if prev_kind == "theme" and prev_op in {"et", "ou"}:
            cont = _clean_theme_suite(part)
            if cont:
                maybe_flush_for_or(is_or)
                current.content.append(cont)
                continue
            prev_kind = None

        if prev_kind == "theme_exclu" and prev_op in {"et", "ou"}:
            cont = _clean_theme_suite(part)
            if cont:
                exclusions.append(cont)
                continue
            prev_kind = None

        if theme and is_negative:
            exclusions.append(theme)
            prev_kind = "theme_exclu"
        else:
            prev_kind = None

    flush()
    return groups, exclusions


def _lemmatize_filtered(text: str, anti: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for w in lemmatize(text):
        if len(w) <= 1 or w in anti or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def finalize_groups(
    groups: list[KeywordGroup],
    exclusions: list[str],
    upper_acronyms: list[str],
    anti: set[str],
) -> tuple[list[KeywordGroup], list[str]]:
    """Lemmatize content clauses, leave title clauses raw, distribute acronyms."""
    upper_norm: list[str] = []
    seen_u: set[str] = set()
    for w in upper_acronyms:
        wn = w.lower()
        if len(wn) <= 1 or wn in seen_u:
            continue
        seen_u.add(wn)
        upper_norm.append(wn)

    final: list[KeywordGroup] = []
    for g in groups:
        title_kws: list[str] = []
        seen_t: set[str] = set()
        for raw in g.title:
            t = raw.lower().strip()
            if t and t not in seen_t:
                seen_t.add(t)
                title_kws.append(t)

        content_kws: list[str] = []
        seen_c: set[str] = set()
        for theme in g.content:
            for w in _lemmatize_filtered(theme, anti):
                if w not in seen_c:
                    seen_c.add(w)
                    content_kws.append(w)

        if title_kws or content_kws:
            final.append(KeywordGroup(title=title_kws, content=content_kws))

    if upper_norm:
        if not final:
            final = [KeywordGroup(title=[], content=list(upper_norm))]
        else:
            for g in final:
                seen = set(g.content)
                for w in upper_norm:
                    if w not in seen:
                        g.content.append(w)
                        seen.add(w)

    excl_out: list[str] = []
    seen_e: set[str] = set()
    for theme in exclusions:
        for w in _lemmatize_filtered(theme, anti):
            if w not in seen_e:
                seen_e.add(w)
                excl_out.append(w)

    return final, excl_out


class FrenchQueryParser(QueryParser):
    """Default parser. Reads anti-dict and known rubrics from a SQLiteIndex."""

    def __init__(self, index: SQLiteIndex) -> None:
        self.index = index
        self._anti: set[str] | None = None
        self._rubrics: list[str] | None = None

    def _anti_dict(self) -> set[str]:
        if self._anti is None:
            self._anti = self.index.get_anti_dict()
        return self._anti

    def _known_rubrics(self) -> list[str]:
        if self._rubrics is None:
            rows = self.index.conn.execute(
                "SELECT DISTINCT rubrique FROM documents WHERE rubrique IS NOT NULL"
            ).fetchall()
            self._rubrics = [r["rubrique"] for r in rows if r["rubrique"]]
        return self._rubrics

    def parse(self, raw: str) -> ParsedQuery:
        cleaned, acronyms = normalize_query(raw)
        rest, filters = extract_global_filters(cleaned, self._known_rubrics())
        rest = _strip_articles_prefix(rest)
        parts, ops = split_logical(rest)
        if not parts:
            parts = [rest]
        groups, exclusions = build_dnf(parts, ops)
        final_groups, final_exclusions = finalize_groups(
            groups, exclusions, acronyms, self._anti_dict()
        )
        return ParsedQuery(groups=final_groups, exclusions=final_exclusions, filters=filters)
