from ri.query.parser import FrenchQueryParser


def test_simple_subject(built_index):
    parser = FrenchQueryParser(built_index)
    pq = parser.parse("Afficher la liste des articles qui parlent de Airbus")
    assert len(pq.groups) == 1
    assert pq.groups[0].content == ["airbus"]


def test_or_opens_new_group(built_index):
    parser = FrenchQueryParser(built_index)
    pq = parser.parse("Je voudrais les articles qui parlent d airbus ou du projet Taxibot")
    assert len(pq.groups) == 2
    assert pq.groups[0].content == ["airbus"]
    assert pq.groups[1].content == ["projet", "taxibot"]


def test_rubrique_filter(built_index):
    parser = FrenchQueryParser(built_index)
    pq = parser.parse("Je veux les articles de la rubrique Focus")
    assert pq.filters.rubrique == "Focus"


def test_date_range(built_index):
    parser = FrenchQueryParser(built_index)
    pq = parser.parse("Quels sont les articles parus entre le 3 mars 2013 et le 4 mai 2013")
    assert pq.filters.date is not None
    assert pq.filters.date.kind == "between_dmy"


def test_acronym_broadcast(built_index):
    parser = FrenchQueryParser(built_index)
    pq = parser.parse("Je veux les articles impliquant le CNRS")
    flat = pq.all_content_terms()
    assert "cnrs" in flat
