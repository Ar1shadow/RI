from ri.ranking.vsm import VSMScorer
from ri.retrieval.engine import SearchService


def test_engine_returns_known_article(built_index):
    svc = SearchService(index=built_index, scorer=VSMScorer())
    docs = svc.run("Afficher la liste des articles qui parlent des systèmes embarqués dans la rubrique Horizons Enseignement")
    assert {d["article"] for d in docs} == {"74751"}
