def test_index_built(built_index):
    assert built_index.doc_count() == 326
    assert len(built_index.vocabulary_terms()) > 1000


def test_anti_dict_present(built_index):
    anti = built_index.get_anti_dict()
    assert "le" in anti
    assert "de" in anti
    assert len(anti) >= 30


def test_postings_for_known_term(built_index):
    postings = built_index.get_postings("airbus", "texte")
    assert postings, "airbus should appear in texte zone"
