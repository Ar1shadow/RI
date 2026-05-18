# RI — Recherche sur Indexation

French information retrieval pipeline. Refactor of the UTC LO17 course project
into a standalone, layered codebase.

---

## EN — Overview

End-to-end pipeline: `scrape → preprocess → index → query → rank → retrieve`.

```
┌─ corpus/          HTML → Document
├─ preprocessing/   tokenize + lemmatize (spaCy fr) + anti-dict
├─ indexing/        SQLite inverted index (postings, vocabulary, idf)
├─ query/           spell-correct + parse DNF + extract filters
├─ ranking/         pluggable Scorer (VSM default, BM25/embeddings stubs)
├─ retrieval/       SearchService — combines parser + scorer + index
└─ evaluation/      precision / recall / F1 / timing
```

## FR — Présentation

Chaîne complète : `extraction → prétraitement → indexation → requête → score → recherche`.

Même schéma que ci-dessus, en français : extraction HTML, lemmatisation spaCy,
index inverse SQLite, analyse de requête (DNF + filtres), scoreur enfichable
(VSM par défaut, BM25/embeddings en réserve), moteur, évaluation P/R/F1.

---

## EN — Installation

```sh
git clone https://github.com/<user>/RI.git
cd RI
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download fr_core_news_sm
```

## FR — Installation

Identique à la section EN. Nécessite Python ≥ 3.11 et le modèle spaCy
`fr_core_news_sm`.

---

## EN — Quick start

```sh
ri scrape data/raw_html/
ri build
ri query "intelligence artificielle et rubrique:industrie"
ri eval
```

## FR — Démarrage rapide

Mêmes commandes. `ri query` ouvre un REPL interactif (`/mode booleen`,
`/mode classe`, `/quitter`).

---

## EN — Project layout

```
ri/
  corpus/         HTML → Document dataclass
  preprocessing/  tokenizer, normalize, anti-dict
  indexing/       SQLite schema + builder + ABC Index
  query/          spell, parser, AST nodes, ABC QueryParser
  ranking/        VSM (default), BM25 stub, embeddings stub, ABC Scorer
  retrieval/      SearchService
  evaluation/     metrics, golden set, plots
  compression/    posting codec ABC (future: gamma, vbyte)
  web/            FastAPI / Streamlit skeleton (future)
data/             raw_html (committed), corpus.xml (ignored), index.sqlite (ignored)
tests/            pytest suite
scripts/          build_index.py, run_eval.py
```

## FR — Structure du projet

Voir l'arborescence ci-dessus.

---

## EN — Extending

- Add a scorer: subclass `ri.ranking.base.Scorer`, register in `ri/ranking/__init__.py`.
- Add an index backend: subclass `ri.indexing.base.Index`.
- Posting compression: implement `ri.compression.base.PostingCodec`.
- Stubs ready (raise `NotImplementedError`): BM25, embeddings, n-grams, web UI.

## FR — Extension

Mêmes points d'extension. Sous-classer les ABC dans `ri.indexing.base`,
`ri.query.base`, `ri.ranking.base`, `ri.compression.base`.

---

## EN — Course context

Originates from LO17 (UTC), refactored from per-TD scripts into a single
layered package. See `docs/specs/` for the design history.

## FR — Contexte académique

Issu du cours LO17 (UTC). Refonte du dépôt original
`Indexing-and-Information-Retrieval` en un package unique structuré par couches.

---

## License

MIT — see `LICENSE`.
