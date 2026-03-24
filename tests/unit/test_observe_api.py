"""Tests for mycelium.observe.api — FastAPI endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from mycelium.observe.store import ObservationStore
from mycelium.observe.api import create_observation_app


@pytest.fixture
def store(tmp_path):
    s = ObservationStore(tmp_path / "test_api.db")
    yield s
    s.close()


@pytest.fixture
def client(store):
    app = create_observation_app(store)
    return TestClient(app)


def test_get_events(client: TestClient, store: ObservationStore):
    store.log_event("TestEvt", "sub.test", '{"x": 1}')
    resp = client.get("/observe/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert data["count"] == 1


def test_get_health(client: TestClient, store: ObservationStore):
    store.log_health("mod", "cpu", 55.0)
    resp = client.get("/observe/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert len(data["metrics"]) == 1


def test_get_stats(client: TestClient, store: ObservationStore):
    store.log_event("A", "s.a", "{}")
    store.log_event("B", "s.b", "{}")
    resp = client.get("/observe/stats")
    assert resp.status_code == 200
    assert resp.json()["total_events"] == 2
