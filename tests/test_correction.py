import time

import pytest

from ri.correction import (
    Candidate,
    CorrectionResult,
    LevenshteinCorrector,
    SurfaceLexicon,
    TokenAnalysis,
)
from ri.correction.text import (
    common_prefix_length,
    is_entity,
    levenshtein,
    tokenize,
)
from ri.retrieval.engine import SearchService


# ---------- text helpers ----------------------------------------------------


def test_tokenize_handles_dates_numbers_words():
    toks = tokenize("Le 15/03/2024, 3.14 et Saint-Étienne")
    assert "15/03/2024" in toks
    assert "3.14" in toks
    assert "Saint-Étienne" in toks


def test_is_entity_detects_dates_and_numbers():
    assert is_entity("2024-03-15")
    assert is_entity("15/03/2024")
    assert is_entity("3.14")
    assert not is_entity("airbus")


def test_common_prefix_length():
    assert common_prefix_length("airbis", "airbus") == 4
    assert common_prefix_length("airbus", "airbus") == 6
    assert common_prefix_length("xyz", "abc") == 0


def test_levenshtein_edge_cases():
    assert levenshtein("airbis", "airbus") == 1
    assert levenshtein("same", "same") == 0
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3


# ---------- SurfaceLexicon --------------------------------------------------


def test_surface_lexicon_basic_lookup():
    lex = SurfaceLexicon({"avion": "avion", "avions": "avion", "airbus": "airbus"})
    assert lex.contains("Avions")
    assert lex.lemma_for("avions") == "avion"
    assert lex.lemma_for("AVION") == "avion"
    assert lex.lemma_for("inconnu") is None


def test_surface_lexicon_perf_contains_o1():
    pairs = {f"word{i:05d}": f"lemma{i:05d}" for i in range(5000)}
    lex = SurfaceLexicon(pairs)
    start = time.perf_counter()
    for _ in range(10_000):
        lex.contains("word02500")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.2, f"10k contains() took {elapsed:.3f}s — should be O(1)"


def test_surface_lexicon_lemma_in_vocab_check():
    lex = SurfaceLexicon({"a": "a"}, lemma_vocab={"vouloir", "airbus"})
    assert lex.lemma_in_vocab("vouloir")
    assert lex.lemma_in_vocab("VOULOIR")
    assert not lex.lemma_in_vocab("inconnu")


# ---------- LevenshteinCorrector status matrix ------------------------------


def _lex(*surface_lemma_pairs: tuple[str, str]) -> SurfaceLexicon:
    return SurfaceLexicon(dict(surface_lemma_pairs), lemma_vocab=set())


def test_corrector_entite_status():
    c = LevenshteinCorrector(_lex(("avion", "avion")))
    r = c.correct("2024-03-15")
    assert r.tokens[0].status == "entite"
    assert r.tokens[0].correction == "2024-03-15"


def test_corrector_valide_status():
    c = LevenshteinCorrector(_lex(("airbus", "airbus")))
    r = c.correct("airbus")
    assert r.tokens[0].status == "valide"
    assert r.tokens[0].lemma == "airbus"


def test_corrector_introuvable_status():
    c = LevenshteinCorrector(_lex(("airbus", "airbus")))
    r = c.correct("xyzqq")
    assert r.tokens[0].status == "introuvable"
    assert r.tokens[0].correction is None


def test_corrector_single_candidate_status():
    c = LevenshteinCorrector(_lex(("avion", "avion")))
    r = c.correct("avian")
    assert r.tokens[0].status == "corrige-candidat-unique"
    assert r.tokens[0].correction == "avion"


def test_corrector_levenshtein_tie_break_with_prefix():
    # zabcd vs zabcz: distance 1, prefix_len 4
    # aabcz vs zabcz: distance 1, prefix_len 0
    # TD4 sort key (distance, -prefix_len, word) picks "zabcd"; pure alphabetical would pick "aabcz"
    c = LevenshteinCorrector(_lex(("aabcz", "aabcz"), ("zabcd", "zabcd")))
    r = c.correct("zabcz")
    assert r.tokens[0].correction == "zabcd"


# ---------- filter formula regression ---------------------------------------


def test_filter_rejects_too_short_prefix():
    # token "a" (len 1) vs "avion" (len 5): prefix_ratio = 1/min(1,5) = 1.0
    # passes proximity but seuil_min=2 must reject (need prefix_len >= 2).
    c = LevenshteinCorrector(_lex(("avion", "avion")), seuil_min=2)
    r = c.correct("a")
    assert r.tokens[0].status == "introuvable"


# ---------- parameter semantics --------------------------------------------


def test_seuil_proximite_filter():
    # token "ab" vs "abcde": prefix_len=2, min(2,5)=2, ratio=1.0; seuil_proximite=0.4 passes.
    # token "z"  vs "zabcd": prefix_len=1, min(1,5)=1, ratio=1.0 passes seuil_proximite,
    #   but seuil_min=2 should still reject (independent check).
    c = LevenshteinCorrector(_lex(("zabcd", "zabcd")), seuil_min=2, seuil_proximite=0.4)
    assert c.correct("z").tokens[0].status == "introuvable"


def test_seuil_max_length_diff_filter():
    # "ab" (len 2) vs "abcdefgh" (len 8): diff = 6 > 3, rejected.
    c = LevenshteinCorrector(_lex(("abcdefgh", "abcdefgh")), seuil_max=3)
    assert c.correct("ab").tokens[0].status == "introuvable"


def test_max_distance_caps_corrections():
    # rubrique vs rubis: distance ~5, length diff = 3, prefix_len = 3.
    # With max_distance=2 (default), no correction should fire.
    c = LevenshteinCorrector(_lex(("rubis", "rubis")), max_distance=2)
    assert c.correct("rubrique").tokens[0].status in ("introuvable", "valide")


# ---------- output strings --------------------------------------------------


def test_corrected_query_preserves_valid_token_surface():
    """Surface (with accents/case) preserved for valid tokens."""
    lex = SurfaceLexicon({"systèmes": "système", "embarqués": "embarquer"})
    c = LevenshteinCorrector(lex)
    r = c.correct("systèmes embarqués")
    assert "systèmes" in r.corrected_query
    assert "embarqués" in r.corrected_query


def test_corrected_query_inlines_correction_for_typo():
    c = LevenshteinCorrector(_lex(("avion", "avion")))
    r = c.correct("avian autre")
    assert "avion" in r.corrected_query
    assert r.corrected_query.startswith("avion")


# ---------- integration: built_index + corrector ----------------------------


def test_lexicon_from_built_index_nonempty(built_index):
    lex = SurfaceLexicon.from_index_with_metadata(built_index)
    assert len(lex) > 1000


def test_corrector_recognizes_corpus_term(built_index):
    lex = SurfaceLexicon.from_index_with_metadata(built_index)
    corrector = LevenshteinCorrector(lex)
    r = corrector.correct("airbus")
    assert r.tokens[0].status == "valide"
    assert r.tokens[0].lemma is not None


@pytest.mark.parametrize(
    "typo,expected_correction",
    [
        ("airbis", "airbus"),
        ("airbu", "airbus"),
        ("enseignment", "enseignement"),
    ],
)
def test_corrector_fixes_known_typos(built_index, typo, expected_correction):
    lex = SurfaceLexicon.from_index_with_metadata(built_index)
    corrector = LevenshteinCorrector(lex)
    r = corrector.correct(typo)
    assert r.tokens[0].correction == expected_correction
    assert r.tokens[0].status.startswith("corrige")


# ---------- integration: SearchService --------------------------------------


def test_engine_corrects_typo(built_index):
    svc = SearchService(index=built_index)
    docs = svc.run("Je voudrais les articles qui parlent d'airbis ou du projet Taxibot")
    assert "71617" in {d["article"] for d in docs[:6]}
    corrected_tokens = [
        (t.token, t.correction)
        for t in svc.last_correction.tokens
        if t.status.startswith("corrige")
    ]
    assert ("airbis", "airbus") in corrected_tokens


def test_engine_disabled_corrector_skips_correction(built_index):
    svc = SearchService(index=built_index, corrector=None)
    svc.run("Je voudrais les articles qui parlent d'airbis")
    assert svc.last_correction is None
