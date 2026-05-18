"""Compiled regex patterns for query parsing.

Ported verbatim from TD5 so the parser keeps the exact extraction surface that
the golden-set evaluation expects.
"""

from __future__ import annotations

import re

MONTH = r"janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"

DMY_NUM = r"\b(?P<day>\d{1,2})[/\-\s]+(?P<month>\d{1,2})[/\-\s]+(?P<year>\d{4})\b"
DMY_TXT = rf"\b(?P<day>\d{{1,2}})\s+(?P<month_name>{MONTH})\s+(?P<year>\d{{4}})\b"
MY_NUM = r"\b(?P<month>\d{1,2})[/\-\s]+(?P<year>\d{4})\b"
MY_TXT = rf"\b(?P<month_name>{MONTH})\s+(?P<year>\d{{4}})\b"
Y = r"\b(?P<year>19\d{2}|20\d{2})\b"

DMY_NUM_RAW = r"\b\d{1,2}[/\-\s]+\d{1,2}[/\-\s]+\d{4}\b"
DMY_TXT_RAW = rf"\b\d{{1,2}}\s+(?:{MONTH})\s+\d{{4}}\b"
MY_NUM_RAW = r"\b\d{1,2}[/\-\s]+\d{4}\b"
MY_TXT_RAW = rf"\b(?:{MONTH})\s+\d{{4}}\b"
Y_RAW = r"\b(?:19\d{2}|20\d{2})\b"

DE_VARIANTS = r"(?:de la|de l[''']|de|du|des|d['''])"

RUBRIQUE = re.compile(
    r"\b(?:(?:dans|sur|pour|provenant|de|du|des|d[''])\s+)?(?:la|le|les|l[''])?\s*\brubrique\s+"
    r"(?:est\s+|se\s+nomme\s+)?(?P<rubrique>.+?)"
    r"(?=$|\b(?:et|ou|sans|mais|dont|qui|parlant|traitant|mentionnant|contenant|évoquant"
    r"|impliquant|portant|provenant|datant)\b)",
    re.IGNORECASE,
)
BETWEEN_DMY = re.compile(
    rf"\bentre\s+(?:le\s+)?(?P<start>{DMY_NUM_RAW}|{DMY_TXT_RAW})"
    rf"\s+et\s+(?:le\s+)?(?P<end>{DMY_NUM_RAW}|{DMY_TXT_RAW})\b",
    re.IGNORECASE,
)
BETWEEN_MY = re.compile(
    rf"\bentre\s+(?P<start>{MY_NUM_RAW}|{MY_TXT_RAW})\s+et\s+(?P<end>{MY_NUM_RAW}|{MY_TXT_RAW})\b",
    re.IGNORECASE,
)
BETWEEN_Y = re.compile(
    rf"\bentre\s+(?P<start>{Y_RAW})\s+et\s+(?P<end>{Y_RAW})\b",
    re.IGNORECASE,
)
LOGICAL_OP = re.compile(
    r"\bet\s+non\s+pas\b|\bnon\s+pas\b|\bmais\s+pas\b|\bsans\b|\bet\b|\bou\b",
    re.IGNORECASE,
)
TITLE_CONTAINS = re.compile(
    r"\bdont\s+le\s+titre\s+(?:contient|évoque)\s+(?:le\s+mot|les\s+mots|le\s+terme)?\s*"
    r"\"?(?P<value>[^\"]+?)\"?(?:$|\b(?:et|ou|mais\s+pas|sans)\b)",
    re.IGNORECASE,
)
IMAGE = re.compile(
    r"\bavec\s+des?\s+images?\b|\bavec\s+image\b|\bcontenant\s+une?\s+image\b"
    r"|\bqui\s+ont\s+des?\s+images?\b",
    re.IGNORECASE,
)
WITHOUT_IMAGE = re.compile(r"\bsans\s+image\b|\bsans\s+images\b", re.IGNORECASE)
NEGATIVE_THEME = re.compile(
    rf"\bn['']?e?\s*(?:parl(?:e|ent|ait|aient|ant|er)|trait(?:e|ent|ait|aient|ant|er)"
    rf"|évoqu(?:e|ent|ait|aient|ant|er)|mentionn(?:e|ent|ait|aient|ant|er)"
    rf"|concern(?:e|ent|ait|aient)|port(?:e|ent|ait|aient|ant|er))\s+pas\s+"
    rf"{DE_VARIANTS}(?P<theme>.+)",
    re.IGNORECASE,
)
THEME_TRIGGER = re.compile(
    rf"\b(?:parl(?:e|ent|ant|er)(?:\s+{DE_VARIANTS})?|trait(?:e|ant|er)\s+{DE_VARIANTS}"
    rf"|sur|a\s+propos\s+{DE_VARIANTS}|évoqu(?:e|ent|ant|er)|mentionn(?:e|ent|ant|er)"
    rf"|port(?:e|ent|ant|er)\s+sur|li(?:e|es)\s+a|concern(?:e|ent)|contien(?:t|nent)"
    rf"|contenant|possèd[e]?(?:nt)?|possédant|impliqu(?:e|ent|ant|er)"
    rf"|comport(?:e|ent|ant|er))\b\s*(?P<theme>.+)",
    re.IGNORECASE,
)
DMY_NUM_RE = re.compile(DMY_NUM, re.IGNORECASE)
DMY_TXT_RE = re.compile(DMY_TXT, re.IGNORECASE)
MY_NUM_RE = re.compile(MY_NUM, re.IGNORECASE)
MY_TXT_RE = re.compile(MY_TXT, re.IGNORECASE)
Y_RE = re.compile(Y, re.IGNORECASE)
DMY_NUM_RAW_RE = re.compile(DMY_NUM_RAW, re.IGNORECASE)
DMY_TXT_RAW_RE = re.compile(DMY_TXT_RAW, re.IGNORECASE)
MY_NUM_RAW_RE = re.compile(MY_NUM_RAW, re.IGNORECASE)
MY_TXT_RAW_RE = re.compile(MY_TXT_RAW, re.IGNORECASE)
Y_RAW_RE = re.compile(Y_RAW, re.IGNORECASE)
