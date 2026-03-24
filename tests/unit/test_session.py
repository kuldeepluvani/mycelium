"""Tests for learn session persistence."""
from __future__ import annotations
import tempfile
import os
from datetime import datetime, timedelta, timezone

import pytest

from mycelium.orchestrator.session import LearnSession, SessionStore


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = SessionStore(path)
    yield s
    s.close()
    os.unlink(path)


def test_create_and_save(store):
    session = LearnSession(budget=50, spent=5, documents_processed=["a.md", "b.md"])
    store.save(session)
    loaded = store.load(session.id)
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.budget == 50
    assert loaded.spent == 5
    assert loaded.documents_processed == ["a.md", "b.md"]
    assert loaded.status == "running"


def test_get_latest(store):
    s1 = LearnSession(started_at=datetime.now(timezone.utc) - timedelta(hours=2))
    s2 = LearnSession(started_at=datetime.now(timezone.utc))
    store.save(s1)
    store.save(s2)
    latest = store.get_latest()
    assert latest is not None
    assert latest.id == s2.id


def test_get_interrupted(store):
    s1 = LearnSession(status="completed")
    s2 = LearnSession(status="running")
    store.save(s1)
    store.save(s2)
    interrupted = store.get_interrupted()
    assert interrupted is not None
    assert interrupted.id == s2.id
    assert interrupted.status == "running"


def test_list_sessions(store):
    for i in range(3):
        store.save(LearnSession(budget=10 + i))
    sessions = store.list_sessions()
    assert len(sessions) == 3
