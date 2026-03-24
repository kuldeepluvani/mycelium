"""Initial Mycelium schema — all core tables and indexes."""

VERSION = 1

SQL = """
-- ── Entities ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    entity_class    TEXT NOT NULL,
    entity_subclass TEXT,
    domain          TEXT,
    aliases         JSON DEFAULT '[]',
    description     TEXT,
    properties      JSON DEFAULT '{}',
    provenance      JSON DEFAULT '[]',
    confidence      REAL DEFAULT 0.5,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    last_validated  TEXT,
    version         INTEGER DEFAULT 1,
    quarantined     INTEGER DEFAULT 0,
    archived        INTEGER DEFAULT 0
);

-- ── Relationships ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS relationships (
    id                  TEXT PRIMARY KEY,
    source_id           TEXT NOT NULL REFERENCES entities(id),
    target_id           TEXT NOT NULL REFERENCES entities(id),
    rel_type            TEXT NOT NULL,
    rel_category        TEXT NOT NULL,
    rationale           TEXT,
    evidence            JSON DEFAULT '[]',
    confidence          REAL DEFAULT 0.5,
    strength            REAL DEFAULT 0.5,
    bidirectional       INTEGER DEFAULT 0,
    temporal_valid_from TEXT,
    temporal_valid_until TEXT,
    is_permanent        INTEGER DEFAULT 0,
    contradiction_of    TEXT,
    decay_rate          REAL DEFAULT 0.05,
    version             INTEGER DEFAULT 1,
    created_at          TEXT NOT NULL,
    last_validated      TEXT,
    quarantined         INTEGER DEFAULT 0,
    archived            INTEGER DEFAULT 0
);

-- ── Documents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    path            TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    last_ingested   TEXT NOT NULL,
    entity_count    INTEGER DEFAULT 0,
    edge_count      INTEGER DEFAULT 0,
    incomplete      INTEGER DEFAULT 0
);

-- ── Agents ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    domain            TEXT,
    description       TEXT,
    seed_nodes        JSON DEFAULT '[]',
    status            TEXT CHECK(status IN ('candidate','active','mature','retired')) DEFAULT 'candidate',
    queries_answered  INTEGER DEFAULT 0,
    avg_confidence    REAL DEFAULT 0.0,
    discovered_at     TEXT NOT NULL,
    last_active       TEXT,
    pinned            INTEGER DEFAULT 0
);

-- ── Agent Nodes (junction) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_nodes (
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    cycle_assigned  INTEGER NOT NULL,
    PRIMARY KEY (agent_id, entity_id)
);

-- ── Concepts ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS concepts (
    id                TEXT PRIMARY KEY,
    entity_id         TEXT REFERENCES entities(id),
    label             TEXT NOT NULL,
    description       TEXT,
    member_entities   JSON DEFAULT '[]',
    confidence        REAL DEFAULT 0.5,
    formed_at         TEXT NOT NULL,
    version           INTEGER DEFAULT 1
);

-- ── Document Chunks ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_chunks (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    start_offset    INTEGER NOT NULL,
    end_offset      INTEGER NOT NULL,
    content_hash    TEXT NOT NULL,
    UNIQUE(document_id, chunk_index)
);

-- ── Feedback Queue ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id       TEXT,
    relationship_id TEXT,
    adjustment      REAL NOT NULL,
    reason          TEXT,
    queued_at       TEXT NOT NULL,
    applied_at      TEXT
);

-- ── Staging Entities ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staging_entities (
    id              TEXT PRIMARY KEY,
    document_id     TEXT,
    layer           INTEGER NOT NULL,
    data            JSON NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_entities_canonical     ON entities(canonical_name);
CREATE INDEX IF NOT EXISTS idx_entities_class         ON entities(entity_class);
CREATE INDEX IF NOT EXISTS idx_entities_domain        ON entities(domain);
CREATE INDEX IF NOT EXISTS idx_entities_confidence    ON entities(confidence);
CREATE INDEX IF NOT EXISTS idx_entities_quarantined   ON entities(quarantined);
CREATE INDEX IF NOT EXISTS idx_entities_archived      ON entities(archived);

CREATE INDEX IF NOT EXISTS idx_rel_source             ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target             ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_type               ON relationships(rel_type);
CREATE INDEX IF NOT EXISTS idx_rel_category           ON relationships(rel_category);
CREATE INDEX IF NOT EXISTS idx_rel_confidence         ON relationships(confidence);
CREATE INDEX IF NOT EXISTS idx_rel_quarantined        ON relationships(quarantined);

CREATE INDEX IF NOT EXISTS idx_docs_path              ON documents(path);
CREATE INDEX IF NOT EXISTS idx_docs_content_hash      ON documents(content_hash);

CREATE INDEX IF NOT EXISTS idx_agents_status          ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_domain          ON agents(domain);

CREATE INDEX IF NOT EXISTS idx_concepts_entity        ON concepts(entity_id);

CREATE INDEX IF NOT EXISTS idx_chunks_document        ON document_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_feedback_entity        ON feedback_queue(entity_id);
CREATE INDEX IF NOT EXISTS idx_feedback_relationship  ON feedback_queue(relationship_id);
CREATE INDEX IF NOT EXISTS idx_feedback_pending       ON feedback_queue(applied_at) WHERE applied_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_staging_document       ON staging_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_staging_status         ON staging_entities(status);
"""
