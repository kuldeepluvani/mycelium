"""Observation store — persists events, sessions, calls, health metrics."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


class ObservationStore:
    def __init__(self, db_path: Path | str):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._initialize()

    def _initialize(self):
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                payload TEXT NOT NULL,
                module TEXT
            );
            CREATE TABLE IF NOT EXISTS health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_health_module ON health(module, timestamp);
        """)
        self._conn.commit()

    def log_event(self, event_type: str, subject: str, payload: str, module: str | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events (timestamp, event_type, subject, payload, module) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), event_type, subject, payload, module),
        )
        self._conn.commit()

    def log_health(self, module: str, metric: str, value: float) -> None:
        self._conn.execute(
            "INSERT INTO health (timestamp, module, metric, value) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), module, metric, value),
        )
        self._conn.commit()

    def get_events(self, event_type: str | None = None, limit: int = 100, since: str | None = None) -> list[dict]:
        query = "SELECT id, timestamp, event_type, subject, payload, module FROM events"
        params: list = []
        conditions: list[str] = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [
            {"id": r[0], "timestamp": r[1], "event_type": r[2], "subject": r[3], "payload": r[4], "module": r[5]}
            for r in rows
        ]

    def get_event_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def get_health_metrics(self, module: str | None = None, limit: int = 100) -> list[dict]:
        if module:
            rows = self._conn.execute(
                "SELECT timestamp, module, metric, value FROM health WHERE module = ? ORDER BY id DESC LIMIT ?",
                (module, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT timestamp, module, metric, value FROM health ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"timestamp": r[0], "module": r[1], "metric": r[2], "value": r[3]} for r in rows]

    def vacuum(self, keep_days: int = 90) -> int:
        """Remove events older than keep_days. Returns count deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        cursor = self._conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
        self._conn.execute("DELETE FROM health WHERE timestamp < ?", (cutoff,))
        self._conn.commit()
        self._conn.execute("VACUUM")
        return cursor.rowcount

    def close(self):
        self._conn.close()
