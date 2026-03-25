"""Web UI support — L2 meta-agents, query history, spillover cache."""

VERSION = 2

SQL = """
-- L2 Meta-Agents
CREATE TABLE IF NOT EXISTS meta_agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    domain          TEXT,
    description     TEXT,
    status          TEXT DEFAULT 'active',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta_agent_children (
    meta_agent_id   TEXT NOT NULL REFERENCES meta_agents(id) ON DELETE CASCADE,
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    domain          TEXT,
    confidence      REAL DEFAULT 0.0,
    entity_count    INTEGER DEFAULT 0,
    key_entities    JSON DEFAULT '[]',
    knowledge_gaps  JSON DEFAULT '[]',
    PRIMARY KEY (meta_agent_id, agent_id)
);

-- Query History
CREATE TABLE IF NOT EXISTS query_history (
    id              TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    mode            TEXT NOT NULL,
    route_meta_id   TEXT,
    route_meta_name TEXT,
    route_strategy  TEXT,
    l1_agent_ids    JSON DEFAULT '[]',
    l1_agent_names  JSON DEFAULT '[]',
    answer          TEXT,
    created_at      TEXT NOT NULL
);

-- Spillover Cache
CREATE TABLE IF NOT EXISTS spillover_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_a_id       TEXT NOT NULL,
    meta_a_name     TEXT NOT NULL,
    meta_b_id       TEXT NOT NULL,
    meta_b_name     TEXT NOT NULL,
    relationships   JSON DEFAULT '[]',
    computed_at     TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_meta_children_agent ON meta_agent_children(agent_id);
CREATE INDEX IF NOT EXISTS idx_query_history_ts ON query_history(created_at);
CREATE INDEX IF NOT EXISTS idx_spillover_cache_ts ON spillover_cache(computed_at);
"""
