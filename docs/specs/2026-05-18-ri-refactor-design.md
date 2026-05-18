# RI Refactor — Implementation Plan

## 1. Context

The LO17 course repo at `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval` was grown TD-by-TD (TD1→TD6) by two collaborators. It accumulated:

- Parallel reimplementations (TD2 vs TD3/2_1; TD4 vs TD4_myself)
- Dead code (TD3/1_1 has 3 unused functions, only reads pre-existing artifacts; TD5 loads `tf-idf.pkl` that is never used since commit 4fd1b05)
- Stale root-level artifacts (`anti_dict.txt`, `inverse_index_full.txt`, `tf-idf.txt`, `corpus_filtre.xml`) diverged from `TD3/` copies and unreferenced by any code
- Heavy `.txt`/`.pkl`/`.xml` flat-file coupling for the index/anti-dict/lemma cache
- 100+-line functions with deep nesting (`traiter_filtres_structurels` 115 L, `traiter_mots_cles` 108 L, `evaluer_metadonnees` 223 L)
- Unused deps (`nltk` only feeds dead Snowball path; `beautifulsoup4` duplicates `lxml`)

**Outcome.** Fresh repo `RI` (Recherche sur Indexation) at `/Users/lipengcheng/Programming/py/RI`, pushed to user's own GitHub. Layered architecture (corpus → preprocessing → indexing → query → ranking → retrieval → evaluation). SQLite as canonical store; `corpus.xml` retained only as debug artifact. ABC interfaces for `Scorer` / `Index` / `QueryParser` with default VSM impl + empty stubs for BM25, n-grams, embeddings, index compression, web UI. Minimal deps (`spacy`, `lxml`, `matplotlib`). English Google-style docstrings; bilingual EN/FR README. MIT license. Source HTML bundle committed for reproducibility. End-to-end smoke test + golden-set parity against TD6 baseline must pass before declaring complete.

## 2. Target Directory Structure

```
/Users/lipengcheng/Programming/py/RI/
├── README.md                       # bilingual EN + FR
├── LICENSE                         # MIT
├── pyproject.toml
├── .gitignore                      # __pycache__, *.pkl, build/, dist/, .venv/, data/cache/, data/corpus.xml, data/index.sqlite
├── .python-version                 # 3.11
│
├── ri/                             # main package
│   ├── __init__.py
│   ├── config.py                   # paths, constants (DATA_DIR, DB_PATH, score weights)
│   ├── cli.py                      # `python -m ri` entry — subcommands: scrape, build, query, eval
│   │
│   ├── corpus/
│   │   ├── __init__.py
│   │   ├── scraper.py              # ex-TD1: HTML → Document
│   │   ├── xml_writer.py           # debug artifact corpus.xml (optional --emit-xml)
│   │   └── models.py               # @dataclass Document(id, fichier, titre, date, auteur, rubrique, has_image, raw_text)
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── tokenizer.py            # spaCy fr_core_news_sm wrapper (segment + lemma, cached nlp object)
│   │   ├── antidict.py             # build & apply stop-word list
│   │   └── normalize.py            # single source of truth: accent strip + casefold
│   │
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── base.py                 # ABC Index
│   │   ├── sqlite_index.py         # default impl — read/write postings, vocabulary, idf
│   │   ├── builder.py              # orchestrates Document stream → SQLite rows (no .pkl)
│   │   └── ngram.py                # STUB: NgramIndex(Index) — raises NotImplementedError
│   │
│   ├── query/
│   │   ├── __init__.py
│   │   ├── base.py                 # ABC QueryParser
│   │   ├── spell.py                # ex-TD4: Levenshtein + Lexicon (reads SQLite vocabulary)
│   │   ├── parser.py               # ex-TD5: global filters → split logical → DNF → lemmatize
│   │   └── ast_nodes.py            # @dataclass Term, And, Or, Not, FilterDate, FilterRubric, FilterImage
│   │
│   ├── ranking/
│   │   ├── __init__.py
│   │   ├── base.py                 # ABC Scorer
│   │   ├── vsm.py                  # default — TF-IDF hybrid (title 3× titre, content 3× titre + 1× texte)
│   │   ├── bm25.py                 # STUB
│   │   └── embeddings.py           # STUB
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── engine.py               # SearchService: parser AST + Scorer + Index + snippet/highlight
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py              # P / R / F1 / timing (numeric only)
│   │   ├── golden_set.py           # 10-query GROUND_TRUTH moved from TD6
│   │   └── plot.py                 # matplotlib PNG output
│   │
│   ├── compression/                # FUTURE
│   │   ├── __init__.py
│   │   └── base.py                 # ABC PostingCodec (gamma/vbyte placeholders)
│   │
│   └── web/                        # FUTURE
│       ├── __init__.py
│       └── app.py                  # STUB: FastAPI/Streamlit skeleton, commented imports
│
├── data/
│   ├── raw_html/                   # FULL bundle of .htm bulletins, committed
│   ├── corpus.xml                  # debug artifact (gitignored)
│   ├── index.sqlite                # canonical store (gitignored)
│   └── anti_dict.txt               # small curated stop list, committed
│
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_preprocessing.py
│   ├── test_indexing.py
│   ├── test_query_parser.py
│   ├── test_ranking_vsm.py
│   ├── test_engine_end_to_end.py
│   └── test_golden_set.py          # parity with TD6
│
└── scripts/
    ├── build_index.py
    └── run_eval.py
```

## 3. SQLite Schema

`ri/indexing/sqlite_index.py` creates on first run:

```sql
CREATE TABLE documents (
    doc_id      INTEGER PRIMARY KEY,
    fichier     TEXT    NOT NULL UNIQUE,
    titre       TEXT,
    auteur      TEXT,
    date        TEXT,                          -- ISO YYYY-MM-DD
    rubrique    TEXT,
    has_image   INTEGER NOT NULL DEFAULT 0,    -- 0/1
    raw_text    TEXT                           -- joined body for snippet/debug
);
CREATE INDEX idx_documents_date     ON documents(date);
CREATE INDEX idx_documents_rubrique ON documents(rubrique);

CREATE TABLE vocabulary (
    term_id     INTEGER PRIMARY KEY,
    term        TEXT    NOT NULL UNIQUE,
    df          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_vocabulary_term ON vocabulary(term);

CREATE TABLE postings (
    term_id     INTEGER NOT NULL REFERENCES vocabulary(term_id),
    doc_id      INTEGER NOT NULL REFERENCES documents(doc_id),
    zone        TEXT    NOT NULL CHECK(zone IN ('titre','texte')),
    tf          INTEGER NOT NULL,
    tfidf       REAL    NOT NULL,              -- (1+log10(tf)) * log10(N/df)
    PRIMARY KEY (term_id, doc_id, zone)
);
CREATE INDEX idx_postings_term ON postings(term_id);
CREATE INDEX idx_postings_doc  ON postings(doc_id);

CREATE TABLE doc_length (                       -- pre-reserved for BM25
    doc_id      INTEGER PRIMARY KEY REFERENCES documents(doc_id),
    len_titre   INTEGER NOT NULL DEFAULT 0,
    len_texte   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE idf (
    term_id     INTEGER PRIMARY KEY REFERENCES vocabulary(term_id),
    idf         REAL NOT NULL
);

CREATE TABLE corpus_stats (                     -- N, avg_len_titre, avg_len_texte
    key         TEXT PRIMARY KEY,
    value       REAL NOT NULL
);
```

`postings.zone` discriminator subsumes the old triple-nested defaultdict in TD3/3_1.py. `doc_length` + `corpus_stats` + `idf` pre-reserved so BM25 needs no schema migration.

## 4. Module-by-Module Migration

| Source | Target | Simplifications |
|---|---|---|
| `TD1/TD1.py` extraire_infos + Creer_Corpus | `ri/corpus/scraper.py` + `ri/corpus/xml_writer.py` | Drop bs4 (lxml.html only). Return `Document` dataclass. `.htm` glob param-configurable. Split per-file parse from corpus assembly. |
| `TD1/BULLETINS/` | `data/raw_html/` (committed) | Bulk move. |
| `TD2/TD2.py` | — | DELETE. Fully superseded by TD3/2_1. |
| `TD3/1_1.py` | — | DELETE. 3 unused functions + dead nltk Snowball path. |
| `TD3/2_1.py` segmente_lemma | `ri/preprocessing/tokenizer.py` | spaCy wrapper, cached nlp object. |
| `TD3/2_1.py` tf_idf | `ri/indexing/builder.py` | Same formula `(1+log10(tf))*log10(N/df)`. Write directly to `postings.tfidf` + `idf` table. No `.pkl`. |
| `TD3/2_1.py` anti_dict + creer_xml_filtre | `ri/preprocessing/antidict.py` + `ri/corpus/xml_writer.py` | Drop unused `substitue` (keep `substitue_dict`). xml_writer is optional debug. |
| `TD3/3_1.py` | `ri/indexing/builder.py` | Eliminate triple-nested defaultdict. Direct SQLite writes. Drop unused `re` import. Zones: `titre`, `texte` only; auteur/date/rubrique/has_image go to `documents` columns, not postings. |
| `TD3/mot_lemma_list.txt` | regenerated via `SELECT term, df FROM vocabulary` | No flat file to maintain. |
| `TD4/query_analyzer.py` | `ri/query/spell.py` | Single normalize source (`preprocessing/normalize.py`); remove duplicate `_strip_accents` that lives in TD5. Lexicon reads SQLite. |
| `TD4_myself/` | — | DELETE entirely. |
| `TD5/traitement_requete.py` extraire_filtres_globaux | `ri/query/parser.py::extract_global_filters` | One-pass `(remaining_query, FilterSet)` build. Stop rewriting query 3×. |
| `TD5` split_logical | `ri/query/parser.py::split_logical` | Recursive descent. Emit `ast_nodes.And/Or/Not`. |
| `TD5` traiter_filtres_structurels (115 L) | `ri/query/parser.py::structural_dnf` | Extract 3 closures into module helpers. Replace 11-branch if/elif with dispatch dict `{operator: handler}`. Target ≤40 L. |
| `TD5` traiter_mots_cles (108 L) | `ri/query/parser.py::lemmatize_keywords` | Reuse `Tokenizer`. Inline accent strip via `normalize`. Target ≤40 L. |
| `TD5/*.pkl` | — | DELETE. Rebuild from SQLite on-demand. tf-idf.pkl already unused. |
| `TD5` 4-tuple return `title_keywords` legacy | drop legacy flat field; keep only `key_word_groups` DNF + filter set | Update engine accordingly. |
| `TD5` typo `load_lemmatisatioin_file` | function replaced by SQLite read | — |
| `TD6/moteur.py` evaluer_metadonnees (223 L) | `ri/retrieval/engine.py::apply_filters` | Decompose 6-level nested if/elif into per-filter `matches(doc_row) -> bool`. Filters built into AST at parse time. Orchestrator ≤50 L. |
| `TD6/moteur.py` scoring | `ri/ranking/vsm.py::VSMScorer(Scorer)` | Same hybrid weights from config (title 3× titre + content 3× titre + 1× texte). Set algebra on doc_id sets (OR between DNF groups, AND within). |
| `TD6/moteur.py` CLI | `ri/cli.py` | argparse subcommands: `ri scrape`, `ri build`, `ri query`, `ri eval`. Interactive REPL inside `ri query` keeps `/mode booleen`, `/mode classe`, `/quitter`. |
| `TD6/moteur.py` charger_corpus + charger_corpus_articles (duplicated) | folded into engine via SQLite lookups | No duplicate XML parsing. |
| `TD6/evaluation.py` GROUND_TRUTH | `ri/evaluation/golden_set.py` | Move dict as-is. |
| `TD6/evaluation.py` metrics + plot | `ri/evaluation/metrics.py` + `ri/evaluation/plot.py` | Split numeric from plotting (testability). |
| Root: `anti_dict.txt`, `inverse_index_full.txt`, `tf-idf.txt`, `corpus_filtre.xml` | — | DELETE (stale, unreferenced). |
| All `__pycache__/` | — | Gitignored in fresh repo. |

## 5. Future-Hook Stub Files (deliberate empty interfaces)

Each is one ABC subclass file with module docstring + `raise NotImplementedError`:

- `ri/ranking/bm25.py` — `class BM25Scorer(Scorer)`; reads `doc_length`, `corpus_stats.avg_len_*`; params `k1`, `b` from config
- `ri/ranking/embeddings.py` — `class EmbeddingScorer(Scorer)`; placeholder for sentence-transformers
- `ri/indexing/ngram.py` — `class NgramIndex(Index)`; character/word n-gram postings
- `ri/compression/base.py` — `class PostingCodec(ABC)` with `encode(list[int]) -> bytes` / `decode(bytes) -> list[int]`; future gamma/vbyte
- `ri/web/app.py` — module-level commented FastAPI skeleton + `# TODO: pip install fastapi uvicorn`

Real ABC parents (not stubs):
- `ri/indexing/base.py::Index` — `add_document`, `get_postings(term, zone)`, `get_idf(term)`, `get_doc_ids_matching_filter(filter)`
- `ri/query/base.py::QueryParser` — `parse(raw) -> ParsedQuery`
- `ri/ranking/base.py::Scorer` — `score(parsed_query, index) -> list[(doc_id, score)]`

## 6. Dependency Manifest

```toml
[project]
name = "ri"
version = "0.1.0"
description = "Recherche sur Indexation — FR information retrieval pipeline"
requires-python = ">=3.11"
dependencies = [
    "spacy>=3.7,<4",
    "lxml>=5",
    "matplotlib>=3.8",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-cov", "ruff", "mypy"]

[project.scripts]
ri = "ri.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Post-install: `python -m spacy download fr_core_news_sm`.

Dropped vs current: `nltk`, `beautifulsoup4`.

## 7. README Structure (bilingual EN+FR)

```
# RI — Recherche sur Indexation

## EN — Overview                          ## FR — Présentation
- Pipeline: scrape → preprocess → index → query → rank → retrieve
- ASCII architecture diagram

## EN — Installation                      ## FR — Installation
    git clone … && cd RI
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    python -m spacy download fr_core_news_sm

## EN — Quick start                       ## FR — Démarrage rapide
    ri scrape data/raw_html/
    ri build
    ri query "intelligence artificielle et rubrique:industrie"
    ri eval

## EN — Project layout                    ## FR — Structure du projet
(abbreviated tree)

## EN — Extending                         ## FR — Extension
- Add a Scorer: subclass ranking.base.Scorer
- Add an Index backend: subclass indexing.base.Index
- Stubs ready: BM25, embeddings, n-grams, compression, web UI

## EN — Course context                    ## FR — Contexte académique
- Origin: LO17 UTC course, refactored to standalone repo

## License — MIT
```

## 8. Cleanup List — Deleted Entirely

- `TD2/` (whole dir)
- `TD3/1_1.py`
- `TD4_myself/` (whole dir)
- `TD5/lemma_dict.pkl`, `TD5/anti_list.pkl`, `TD5/tf-idf.pkl`
- Root: `anti_dict.txt`, `inverse_index_full.txt`, `tf-idf.txt`, `corpus_filtre.xml`
- All `__pycache__/` dirs
- `nltk` + `beautifulsoup4` from deps

## 9. Verification Plan

All four must pass before declaring complete.

**9.1 Unit tests** — `pytest tests/ -v`
- `test_scraper.py`: fixture .htm → Document fields assertions
- `test_preprocessing.py`: known sample lemmatize + antidict filter
- `test_indexing.py`: 3-doc fixture → vocabulary/postings/idf row counts
- `test_query_parser.py`: golden queries → expected AST (DNF + filters)
- `test_ranking_vsm.py`: hand-computed score for 1-term query on 2-doc fixture

**9.2 End-to-end smoke**
```
ri scrape data/raw_html/sample/
ri build
ri query "intelligence artificielle"
```
Expect: ranked list ≥1 hit, scores monotonically decreasing.

**9.3 Golden-set parity vs TD6**
Before refactor, capture baseline:
```
cd /Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval
python TD6/evaluation.py > /tmp/td6_baseline.txt
```
After refactor:
```
ri eval --golden-set data/golden_set.json --report data/eval_report.json
```
Pass criterion: mean F1 within ±2% of TD6 baseline.

**9.4 Static** — `ruff check ri/ && mypy ri/ --strict`

## 10. Git / GitHub Steps

1. Capture TD6 baseline (one-time, in old repo) — see 9.3
2. `mkdir -p /Users/lipengcheng/Programming/py/RI && cd $_ && git init -b main`
3. Scaffold dirs, pyproject.toml, .gitignore, README, ABC base classes, empty `__init__.py`
4. Commit scaffold: `git commit -m "chore: initial RI scaffold (layered pipeline + ABC stubs)"`
5. Migrate module-by-module (cadence in §11). One commit per module, tests green each commit.
6. Publish:
```
gh repo create RI --public --source=. --remote=origin \
    --description "FR information retrieval — refactor of LO17 course project"
git push -u origin main
```
7. Post-refactor: dispatch `cavecrew-reviewer` per-module + `cavecrew-builder` for cleanup deltas.

## 11. Effort Breakdown

Total ≈ 18–24 h.

| Phase | Effort |
|---|---|
| Scaffolding (dirs, pyproject, .gitignore, ABCs, config, cli skeleton, READMEs) | 1.5 h |
| `corpus/` (scraper + Document + xml_writer; drop bs4) | 1.5 h |
| `preprocessing/` (tokenizer, normalize, antidict) | 1.5 h |
| `indexing/` (SQLite schema, builder one-pass postings+idf+doc_length, base.py) | 3 h |
| `query/spell.py` (port TD4 with SQLite lexicon) | 1.5 h |
| `query/parser.py` (one-pass global filters, structural_dnf ≤40 L, lemmatize_keywords ≤40 L, AST emit) | 3.5 h |
| `ranking/` (VSM scorer, Scorer ABC, BM25+embeddings stubs) | 2 h |
| `retrieval/engine.py` (decompose evaluer_metadonnees 223 L → matches() + orchestrator ≤50 L) | 2 h |
| `evaluation/` (golden_set move, metrics/plot split) | 1 h |
| `tests/` (6 unit + 1 e2e + 1 golden parity) | 2.5 h |
| Verification + golden-set diagnosis (if F1 drifts) | 1.5 h |
| GitHub create + push + README polish | 0.5 h |

Commit cadence: one commit per row, each leaves pytest green.

## Critical Files Referenced (current repo)

- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD1/TD1.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD3/2_1.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD3/3_1.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD4/query_analyzer.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD5/traitement_requete.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD6/moteur.py`
- `/Users/lipengcheng/Programming/py/LO17/Indexing-and-Information-Retrieval/TD6/evaluation.py`
