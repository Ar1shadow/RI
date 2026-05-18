-- RI index schema. Loaded by sqlite_index.SQLiteIndex on first run.

CREATE TABLE IF NOT EXISTS documents (
    doc_id      INTEGER PRIMARY KEY,
    fichier     TEXT    NOT NULL UNIQUE,
    bulletin    TEXT,
    article     TEXT,
    titre       TEXT,
    auteur      TEXT,
    date        TEXT,
    rubrique    TEXT,
    has_image   INTEGER NOT NULL DEFAULT 0,
    raw_text    TEXT
);
CREATE INDEX IF NOT EXISTS idx_documents_date     ON documents(date);
CREATE INDEX IF NOT EXISTS idx_documents_rubrique ON documents(rubrique);

CREATE TABLE IF NOT EXISTS vocabulary (
    term_id     INTEGER PRIMARY KEY,
    term        TEXT    NOT NULL UNIQUE,
    df          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_vocabulary_term ON vocabulary(term);

CREATE TABLE IF NOT EXISTS postings (
    term_id     INTEGER NOT NULL REFERENCES vocabulary(term_id),
    doc_id      INTEGER NOT NULL REFERENCES documents(doc_id),
    zone        TEXT    NOT NULL CHECK(zone IN ('titre','texte')),
    tf          INTEGER NOT NULL,
    tfidf       REAL    NOT NULL,
    PRIMARY KEY (term_id, doc_id, zone)
);
CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term_id);
CREATE INDEX IF NOT EXISTS idx_postings_doc  ON postings(doc_id);

CREATE TABLE IF NOT EXISTS doc_length (
    doc_id      INTEGER PRIMARY KEY REFERENCES documents(doc_id),
    len_titre   INTEGER NOT NULL DEFAULT 0,
    len_texte   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS idf (
    term_id     INTEGER PRIMARY KEY REFERENCES vocabulary(term_id),
    idf         REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS corpus_stats (
    key         TEXT PRIMARY KEY,
    value       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS anti_dict (
    term        TEXT PRIMARY KEY
);
