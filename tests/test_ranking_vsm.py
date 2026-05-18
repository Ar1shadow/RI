from ri.query.parser import FrenchQueryParser
from ri.ranking.vsm import VSMScorer


def test_vsm_ranks_relevant_doc_first(built_index):
    parser = FrenchQueryParser(built_index)
    scorer = VSMScorer()
    pq = parser.parse("Afficher la liste des articles qui parlent des systèmes embarqués dans la rubrique Horizons Enseignement")
    results = scorer.score(pq, built_index)
    assert results, "should rank at least one doc"
    top_doc_id = results[0][0]
    top_doc = built_index.get_documents([top_doc_id])[0]
    assert top_doc["article"] == "74751"
