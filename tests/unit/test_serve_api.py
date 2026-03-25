"""Tests for mycelium.serve.api."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from mycelium.serve.api import create_app


@pytest.fixture
def mock_orch():
    orch = MagicMock()
    orch.graph = MagicMock()
    orch.graph.node_count = MagicMock(return_value=10)
    orch.graph.edge_count = MagicMock(return_value=5)
    orch.graph.all_entity_ids = MagicMock(return_value=["e1"])

    entity = MagicMock()
    entity.model_dump = MagicMock(return_value={
        "id": "e1",
        "name": "test",
        "entity_class": "service",
        "domain": "backend",
        "confidence": 0.8,
    })
    orch.graph.get_entity = MagicMock(return_value=entity)
    orch.graph.all_relationships = MagicMock(return_value=[])
    orch.graph.get_neighbors = MagicMock(return_value=set())

    orch.agent_manager = MagicMock()
    orch.agent_manager.agents = []
    orch.agent_manager.get_active = MagicMock(return_value=[])
    orch.agent_manager.get_meta_agents = MagicMock(return_value=[])

    orch.session_store = MagicMock()
    orch.session_store.get_latest = MagicMock(return_value=None)
    orch.session_store.list_sessions = MagicMock(return_value=[])

    orch.observation_store = MagicMock()
    orch.observation_store.get_events = MagicMock(return_value=[])
    orch.observation_store.get_health_metrics = MagicMock(return_value=[])
    orch.observation_store.get_event_count = MagicMock(return_value=0)

    orch.connector_registry = MagicMock()
    orch.connector_registry.source_types = MagicMock(return_value=["vault"])

    orch.store = MagicMock()
    orch.store.execute = MagicMock(
        return_value=MagicMock(fetchall=MagicMock(return_value=[]))
    )
    orch.store.conn = MagicMock()

    return orch


@pytest.fixture
def client(mock_orch):
    app = create_app(orch=mock_orch)
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["graph"]["nodes"] == 10
    assert data["graph"]["edges"] == 5


def test_graph_nodes(client):
    resp = client.get("/api/graph/nodes")
    assert resp.status_code == 200
    assert len(resp.json()["nodes"]) == 1


def test_graph_edges(client):
    resp = client.get("/api/graph/edges")
    assert resp.status_code == 200
    assert "edges" in resp.json()


def test_graph_entity_found(client):
    resp = client.get("/api/graph/entity/e1")
    assert resp.status_code == 200
    data = resp.json()
    assert "entity" in data
    assert "neighbor_ids" in data
    assert "relationships" in data


def test_graph_entity_not_found(client, mock_orch):
    mock_orch.graph.get_entity = MagicMock(return_value=None)
    app = create_app(orch=mock_orch)
    c = TestClient(app)
    resp = c.get("/api/graph/entity/missing")
    assert resp.status_code == 404


def test_agents_list(client):
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    assert "agents" in resp.json()


def test_agents_hierarchy(client):
    resp = client.get("/api/agents/hierarchy")
    assert resp.status_code == 200
    assert "meta_agents" in resp.json()


def test_agents_spillover(client):
    resp = client.get("/api/agents/spillover")
    assert resp.status_code == 200
    assert "spillover" in resp.json()


def test_learn_sessions(client):
    resp = client.get("/api/learn/sessions")
    assert resp.status_code == 200
    assert "sessions" in resp.json()


def test_observe_events(client):
    resp = client.get("/api/observe/events")
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_observe_health(client):
    resp = client.get("/api/observe/health")
    assert resp.status_code == 200
    assert "metrics" in resp.json()


def test_ask_history(client):
    resp = client.get("/api/ask/history")
    assert resp.status_code == 200
    assert "queries" in resp.json()


def test_no_orch_health():
    """Health always works even without orchestrator."""
    app = create_app(orch=None)
    c = TestClient(app)
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_no_orch_status():
    """Status returns zeros when no orchestrator."""
    app = create_app(orch=None)
    c = TestClient(app)
    resp = c.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["graph"]["nodes"] == 0
    assert data["graph"]["edges"] == 0


def test_no_orch_graph_nodes():
    app = create_app(orch=None)
    c = TestClient(app)
    resp = c.get("/api/graph/nodes")
    assert resp.status_code == 200
    assert resp.json()["nodes"] == []
