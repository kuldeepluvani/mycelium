"""Learn session persistence and crash recovery."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class LearnSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: str = "running"  # running, completed, interrupted, crashed
    budget: int = 50
    spent: int = 0
    documents_processed: list[str] = field(default_factory=list)
    documents_remaining: list[str] = field(default_factory=list)
    entities_created: int = 0
    edges_created: int = 0
    agents_discovered: int = 0
    spillovers: int = 0
    last_checkpoint: str | None = None


class SessionStore:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._ensure_tables()

    def _ensure_tables(self):
        # observation.db should already have sessions table, but create if not
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                budget INTEGER NOT NULL,
                spent INTEGER NOT NULL DEFAULT 0,
                documents_processed TEXT,
                documents_remaining TEXT,
                entities_created INTEGER DEFAULT 0,
                edges_created INTEGER DEFAULT 0,
                agents_discovered INTEGER DEFAULT 0,
                spillovers INTEGER DEFAULT 0,
                last_checkpoint TEXT
            )
        """)
        self._conn.commit()

    def save(self, session: LearnSession) -> None:
        self._conn.execute("""
            INSERT OR REPLACE INTO sessions
            (id, started_at, completed_at, status, budget, spent,
             documents_processed, documents_remaining,
             entities_created, edges_created, agents_discovered, spillovers, last_checkpoint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.started_at.isoformat(),
            session.completed_at.isoformat() if session.completed_at else None,
            session.status,
            session.budget,
            session.spent,
            json.dumps(session.documents_processed),
            json.dumps(session.documents_remaining),
            session.entities_created,
            session.edges_created,
            session.agents_discovered,
            session.spillovers,
            session.last_checkpoint,
        ))
        self._conn.commit()

    def load(self, session_id: str) -> LearnSession | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def get_latest(self) -> LearnSession | None:
        row = self._conn.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def get_interrupted(self) -> LearnSession | None:
        """Find most recent session with status 'running' (likely crashed)."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def list_sessions(self, limit: int = 20) -> list[LearnSession]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def _row_to_session(self, row) -> LearnSession:
        return LearnSession(
            id=row[0],
            started_at=datetime.fromisoformat(row[1]),
            completed_at=datetime.fromisoformat(row[2]) if row[2] else None,
            status=row[3],
            budget=row[4],
            spent=row[5],
            documents_processed=json.loads(row[6]) if row[6] else [],
            documents_remaining=json.loads(row[7]) if row[7] else [],
            entities_created=row[8],
            edges_created=row[9],
            agents_discovered=row[10],
            spillovers=row[11],
            last_checkpoint=row[12],
        )

    def close(self):
        self._conn.close()
