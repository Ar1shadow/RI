from ri.preprocessing.normalize import normalize, strip_accents


def test_strip_accents_removes_diacritics():
    assert strip_accents("café") == "cafe"
    assert strip_accents("éàïü") == "eaiu"
    assert strip_accents("plain") == "plain"


def test_normalize_lowercases_and_compacts():
    assert normalize("Café   Théâtre") == "cafe theatre"
    assert normalize("  HELLO  WORLD  ") == "hello world"
    assert normalize("") == ""
    assert normalize(None) == ""
