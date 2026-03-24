"""Tests for mycelium.serve.feedback."""
from __future__ import annotations
import sqlite3
import tempfile
import os
from mycelium.serve.feedback import FeedbackLoop


def _create_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE feedback_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT,
            relationship_id TEXT,
            adjustment REAL,
            reason TEXT,
            queued_at TEXT,
            applied_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    return path


def test_record_acceptance():
    path = _create_db()
    try:
        fb = FeedbackLoop(db_path=path)
        count = fb.record_acceptance(entity_ids=["e1", "e2"])
        assert count == 2
        pending = fb.get_pending()
        assert len(pending) == 2
        assert all(p["adjustment"] == 0.03 for p in pending)
    finally:
        os.unlink(path)


def test_record_correction():
    path = _create_db()
    try:
        fb = FeedbackLoop(db_path=path)
        count = fb.record_correction(entity_ids=["e1"])
        assert count == 1
        pending = fb.get_pending()
        assert pending[0]["adjustment"] == -0.05
    finally:
        os.unlink(path)


def test_get_pending():
    path = _create_db()
    try:
        fb = FeedbackLoop(db_path=path)
        fb.record_acceptance(entity_ids=["e1"])
        fb.record_correction(relationship_ids=["r1"])
        pending = fb.get_pending()
        assert len(pending) == 2
    finally:
        os.unlink(path)


def test_mark_applied():
    path = _create_db()
    try:
        fb = FeedbackLoop(db_path=path)
        fb.record_acceptance(entity_ids=["e1", "e2"])
        pending = fb.get_pending()
        assert len(pending) == 2
        fb.mark_applied([p["id"] for p in pending])
        assert len(fb.get_pending()) == 0
    finally:
        os.unlink(path)
