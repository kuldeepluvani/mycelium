"""Tests for mycelium.observe.store.ObservationStore."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from mycelium.observe.store import ObservationStore


@pytest.fixture
def store(tmp_path):
    s = ObservationStore(tmp_path / "test_observe.db")
    yield s
    s.close()


def test_log_and_get_events(store: ObservationStore):
    store.log_event("TypeA", "sub.a", '{"key": "val1"}')
    store.log_event("TypeB", "sub.b", '{"key": "val2"}')
    store.log_event("TypeC", "sub.c", '{"key": "val3"}')
    events = store.get_events()
    assert len(events) == 3


def test_filter_by_type(store: ObservationStore):
    store.log_event("Alpha", "sub.alpha", '{}')
    store.log_event("Beta", "sub.beta", '{}')
    store.log_event("Alpha", "sub.alpha2", '{}')
    events = store.get_events(event_type="Alpha")
    assert len(events) == 2
    assert all(e["event_type"] == "Alpha" for e in events)


def test_log_health(store: ObservationStore):
    store.log_health("connector", "latency_ms", 42.5)
    metrics = store.get_health_metrics(module="connector")
    assert len(metrics) == 1
    assert metrics[0]["metric"] == "latency_ms"
    assert metrics[0]["value"] == 42.5


def test_vacuum(store: ObservationStore):
    # Insert an event with a timestamp far in the past directly
    old_ts = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    store._conn.execute(
        "INSERT INTO events (timestamp, event_type, subject, payload) VALUES (?, ?, ?, ?)",
        (old_ts, "OldEvent", "sub.old", "{}"),
    )
    store._conn.commit()
    # Also log a recent event
    store.log_event("NewEvent", "sub.new", "{}")
    assert store.get_event_count() == 2
    deleted = store.vacuum(keep_days=1)
    assert deleted == 1
    assert store.get_event_count() == 1


def test_event_count(store: ObservationStore):
    for i in range(5):
        store.log_event("Evt", f"sub.{i}", "{}")
    assert store.get_event_count() == 5
