"""Content-hash change detection."""

VERSION = 3

SQL = """
-- Document content hashes for change detection
CREATE TABLE IF NOT EXISTS document_hashes (
    path            TEXT PRIMARY KEY,
    content_hash    TEXT NOT NULL,
    last_processed  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doc_hashes_hash ON document_hashes(content_hash);
"""
