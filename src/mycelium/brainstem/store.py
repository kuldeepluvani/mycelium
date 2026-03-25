"""BrainstemStore — SQLite-backed persistence for the Mycelium knowledge graph."""

from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mycelium.shared.models import Entity, Evidence, Relationship, TimeScope


_MIGRATION_MODULES = [
    "mycelium.migrations.001_initial",
    "mycelium.migrations.002_webui",
]


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_dt(val: str | None) -> datetime | None:
    if val is None:
        return None
    return datetime.fromisoformat(val)


class BrainstemStore:
    """Low-level SQLite store with WAL mode, FK enforcement, and auto-migrations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA wal_autocheckpoint = 1000")
        self._run_migrations()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def checkpoint(self) -> None:
        assert self.conn is not None
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # ── migrations ───────────────────────────────────────────────────────

    def _run_migrations(self) -> None:
        assert self.conn is not None
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        row = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current: int = row[0] if row[0] is not None else 0

        for module_path in _MIGRATION_MODULES:
            mod = importlib.import_module(module_path)
            if mod.VERSION > current:
                self.conn.executescript(mod.SQL)
                self.conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (mod.VERSION, datetime.now(timezone.utc).isoformat()),
                )
                self.conn.commit()

    # ── generic helpers ──────────────────────────────────────────────────

    def list_tables(self) -> list[str]:
        assert self.conn is not None
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        assert self.conn is not None
        return self.conn.execute(sql, params)

    # ── entity CRUD ──────────────────────────────────────────────────────

    def upsert_entity(self, entity: Entity) -> None:
        assert self.conn is not None
        self.conn.execute(
            """
            INSERT OR REPLACE INTO entities (
                id, name, canonical_name, entity_class, entity_subclass,
                domain, aliases, description, properties, provenance,
                confidence, first_seen, last_seen, last_validated,
                version, quarantined, archived
            ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?, ?,?,?)
            """,
            (
                entity.id,
                entity.name,
                entity.canonical_name,
                entity.entity_class,
                entity.entity_subclass,
                entity.domain,
                json.dumps(entity.aliases),
                entity.description,
                json.dumps(entity.properties),
                json.dumps(entity.provenance),
                entity.confidence,
                _iso(entity.first_seen),
                _iso(entity.last_seen),
                _iso(entity.last_validated),
                entity.version,
                int(entity.quarantined),
                int(entity.archived),
            ),
        )
        self.conn.commit()

    def get_entity(self, entity_id: str) -> Entity | None:
        assert self.conn is not None
        row = self.conn.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()
        if row is None:
            return None
        return Entity(
            id=row["id"],
            name=row["name"],
            canonical_name=row["canonical_name"],
            entity_class=row["entity_class"],
            entity_subclass=row["entity_subclass"],
            domain=row["domain"],
            aliases=json.loads(row["aliases"]) if row["aliases"] else [],
            description=row["description"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            provenance=json.loads(row["provenance"]) if row["provenance"] else [],
            confidence=row["confidence"],
            first_seen=_parse_dt(row["first_seen"]),
            last_seen=_parse_dt(row["last_seen"]),
            last_validated=_parse_dt(row["last_validated"]),
            version=row["version"],
            quarantined=bool(row["quarantined"]),
            archived=bool(row["archived"]),
        )

    def get_entities_by_confidence(self, below: float) -> list[Entity]:
        """Return entities with confidence strictly below the threshold."""
        assert self.conn is not None
        rows = self.conn.execute(
            "SELECT * FROM entities WHERE confidence < ? ORDER BY confidence ASC",
            (below,),
        ).fetchall()
        return [
            Entity(
                id=r["id"],
                name=r["name"],
                canonical_name=r["canonical_name"],
                entity_class=r["entity_class"],
                entity_subclass=r["entity_subclass"],
                domain=r["domain"],
                aliases=json.loads(r["aliases"]) if r["aliases"] else [],
                description=r["description"],
                properties=json.loads(r["properties"]) if r["properties"] else {},
                provenance=json.loads(r["provenance"]) if r["provenance"] else [],
                confidence=r["confidence"],
                first_seen=_parse_dt(r["first_seen"]),
                last_seen=_parse_dt(r["last_seen"]),
                last_validated=_parse_dt(r["last_validated"]),
                version=r["version"],
                quarantined=bool(r["quarantined"]),
                archived=bool(r["archived"]),
            )
            for r in rows
        ]

    # ── relationship CRUD ────────────────────────────────────────────────

    def upsert_relationship(self, rel: Relationship) -> None:
        assert self.conn is not None
        ts = rel.temporal_scope
        self.conn.execute(
            """
            INSERT OR REPLACE INTO relationships (
                id, source_id, target_id, rel_type, rel_category,
                rationale, evidence, confidence, strength, bidirectional,
                temporal_valid_from, temporal_valid_until, is_permanent,
                contradiction_of, decay_rate, version,
                created_at, last_validated, quarantined, archived
            ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?,?)
            """,
            (
                rel.id,
                rel.source_id,
                rel.target_id,
                rel.rel_type,
                rel.rel_category,
                rel.rationale,
                json.dumps([e.model_dump(mode="json") for e in rel.evidence]),
                rel.confidence,
                rel.strength,
                int(rel.bidirectional),
                _iso(ts.valid_from) if ts else None,
                _iso(ts.valid_until) if ts else None,
                int(ts.is_permanent) if ts else 0,
                rel.contradiction_of,
                rel.decay_rate,
                rel.version,
                _iso(rel.created_at),
                _iso(rel.last_validated),
                int(rel.quarantined),
                int(rel.archived),
            ),
        )
        self.conn.commit()

    def get_relationship(self, rel_id: str) -> Relationship | None:
        assert self.conn is not None
        row = self.conn.execute(
            "SELECT * FROM relationships WHERE id = ?", (rel_id,)
        ).fetchone()
        if row is None:
            return None

        evidence_raw = json.loads(row["evidence"]) if row["evidence"] else []
        evidence = [Evidence(**e) for e in evidence_raw]

        valid_from = _parse_dt(row["temporal_valid_from"])
        valid_until = _parse_dt(row["temporal_valid_until"])
        is_permanent = bool(row["is_permanent"])
        temporal_scope: TimeScope | None = None
        if valid_from or valid_until or is_permanent:
            temporal_scope = TimeScope(
                valid_from=valid_from,
                valid_until=valid_until,
                is_permanent=is_permanent,
            )

        return Relationship(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            rel_type=row["rel_type"],
            rel_category=row["rel_category"],
            rationale=row["rationale"],
            evidence=evidence,
            confidence=row["confidence"],
            strength=row["strength"],
            bidirectional=bool(row["bidirectional"]),
            temporal_scope=temporal_scope,
            contradiction_of=row["contradiction_of"],
            decay_rate=row["decay_rate"],
            version=row["version"],
            created_at=_parse_dt(row["created_at"]),
            last_validated=_parse_dt(row["last_validated"]),
            quarantined=bool(row["quarantined"]),
            archived=bool(row["archived"]),
        )
