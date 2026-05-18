"""Hand-annotated golden queries for evaluation.

Moved verbatim from TD6/evaluation.py so the parity check (mean F1 within
+/-2% of the TD6 baseline) is reproducible.
"""

from __future__ import annotations

GROUND_TRUTH: list[dict] = [
    {
        "id": "Q01",
        "query": "Afficher la liste des articles qui parlent des systèmes embarqués dans la rubrique Horizons Enseignement",
        "relevant_articles": {"74751"},
    },
    {
        "id": "Q02",
        "query": "Quels sont les articles parus entre le 3 mars 2013 et le 4 mai 2013",
        "relevant_articles": {
            "72629", "72630", "72631", "72632", "72633", "72634", "72635",
            "72636", "72637", "72932", "72933", "72934", "72935", "72936",
            "72937", "72938", "72939", "72940",
        },
    },
    {
        "id": "Q03",
        "query": "Je veux les articles de la rubrique Focus parlant d'innovation",
        "relevant_articles": {
            "67068", "67383", "68273", "68276", "68383", "69533", "69535",
            "70162", "71359", "72392", "72393", "72630", "72933", "73876",
            "74167", "74744", "76507",
        },
    },
    {
        "id": "Q04",
        "query": "Je veux les articles de 2014 et de la rubrique Focus et parlant de santé",
        "relevant_articles": {"75459", "76507"},
    },
    {
        "id": "Q05",
        "query": "Je veux les articles impliquant le CNRS et qui parlent de chimie",
        "relevant_articles": {
            "67068", "67071", "67558", "67800", "68278", "68280", "68388",
            "68390", "69183", "69184", "70745", "70922", "72632", "72634",
            "72940", "73189", "73436", "74173", "74750", "75066", "75067", "75070",
        },
    },
    {
        "id": "Q06",
        "query": "Je voudrais les articles qui parlent d'airbus ou du projet Taxibot",
        "relevant_articles": {"67797", "70920", "71617", "72636", "72933", "74745"},
    },
    {
        "id": "Q07",
        "query": "Quels sont les articles parlant de la Russie ou du Japon",
        "relevant_articles": {
            "67383", "67939", "67942", "67943", "68388", "68642", "69185",
            "70915", "72117", "72396", "73880", "74168", "74746", "75064",
        },
    },
    {
        "id": "Q08",
        "query": "Je voudrais les articles dont le titre contient le mot chimie",
        "relevant_articles": {"67392", "67561", "68278", "68390", "74752", "75461"},
    },
    {
        "id": "Q09",
        "query": "Je voudrais les articles de 2011 sur l'enseignement",
        "relevant_articles": {
            "67068", "67071", "67795", "67944", "68277", "68281", "68392", "68393",
        },
    },
    {
        "id": "Q10",
        "query": "Quels sont les articles dont le titre contient biocarburant ou le contenu parle des bioénergies",
        "relevant_articles": {"68385", "72121"},
    },
]
