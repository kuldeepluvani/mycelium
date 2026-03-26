"""User feedback loop with bounded confidence adjustments."""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone


class FeedbackLoop:
    def __init__(self, db_path: str | None = None, store=None):
        if store and store.conn:
            self._conn = store.conn
        elif db_path:
            self._conn = sqlite3.connect(db_path)
        else:
            self._conn = None

    def record_acceptance(self, entity_ids: list[str] = None, relationship_ids: list[str] = None) -> int:
        """Record user accepted the answer. Returns number of adjustments queued."""
        count = 0
        for eid in (entity_ids or []):
            self._queue_adjustment(entity_id=eid, adjustment=0.03, reason="user_accepted")
            count += 1
        for rid in (relationship_ids or []):
            self._queue_adjustment(relationship_id=rid, adjustment=0.03, reason="user_accepted")
            count += 1
        return count

    def record_correction(self, entity_ids: list[str] = None, relationship_ids: list[str] = None) -> int:
        """Record user corrected/rejected the answer."""
        count = 0
        for eid in (entity_ids or []):
            self._queue_adjustment(entity_id=eid, adjustment=-0.05, reason="user_corrected")
            count += 1
        for rid in (relationship_ids or []):
            self._queue_adjustment(relationship_id=rid, adjustment=-0.05, reason="user_corrected")
            count += 1
        return count

    def _queue_adjustment(self, entity_id: str = None, relationship_id: str = None, adjustment: float = 0.0, reason: str = ""):
        if not self._conn:
            return
        self._conn.execute(
            "INSERT INTO feedback_queue (entity_id, relationship_id, adjustment, reason, queued_at) VALUES (?, ?, ?, ?, ?)",
            (entity_id, relationship_id, adjustment, reason, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get_pending(self) -> list[dict]:
        if not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT id, entity_id, relationship_id, adjustment, reason FROM feedback_queue WHERE applied_at IS NULL"
        ).fetchall()
        return [{"id": r[0], "entity_id": r[1], "relationship_id": r[2], "adjustment": r[3], "reason": r[4]} for r in rows]

    def mark_applied(self, feedback_ids: list[int]):
        if not self._conn:
            return
        now = datetime.now(timezone.utc).isoformat()
        for fid in feedback_ids:
            self._conn.execute("UPDATE feedback_queue SET applied_at = ? WHERE id = ?", (now, fid))
        self._conn.commit()

    def apply_pending(self, store, graph, decay_engine) -> int:
        """Apply all pending feedback adjustments to store and graph. Returns count applied."""
        pending = self.get_pending()
        if not pending:
            return 0

        applied_ids = []
        for fb in pending:
            if fb["entity_id"]:
                entity = graph.get_entity(fb["entity_id"])
                if entity:
                    if fb["adjustment"] > 0:
                        new_conf = decay_engine.feedback_boost(entity.confidence)
                    else:
                        new_conf = decay_engine.feedback_penalty(entity.confidence)
                    entity.confidence = new_conf
                    store.update_entity_confidence(entity.id, new_conf)

            if fb["relationship_id"]:
                rel = graph.get_relationship(fb["relationship_id"])
                if rel:
                    if fb["adjustment"] > 0:
                        new_conf = decay_engine.feedback_boost(rel.confidence)
                    else:
                        new_conf = decay_engine.feedback_penalty(rel.confidence)
                    rel.confidence = new_conf
                    store.update_relationship_confidence(rel.id, new_conf)

            applied_ids.append(fb["id"])

        self.mark_applied(applied_ids)
        return len(applied_ids)
