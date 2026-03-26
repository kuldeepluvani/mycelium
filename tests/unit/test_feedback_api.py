"""Tests for feedback API endpoints."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from mycelium.serve.api import create_app


def _mock_orch():
    orch = MagicMock()
    orch.graph = MagicMock()
    orch.graph.node_count.return_value = 10
    orch.graph.edge_count.return_value = 5
    orch.graph.all_entity_ids.return_value = []
    orch.agent_manager = MagicMock()
    orch.agent_manager.agents = []
    orch.agent_manager.get_active.return_value = []
    orch.agent_manager.get_meta_agents.return_value = []
    orch.observation_store = MagicMock()
    orch.store = MagicMock()
    orch.store.conn = MagicMock()  # FeedbackLoop needs store.conn
    orch.session_store = MagicMock()
    orch.session_store.get_latest.return_value = None
    orch.connector_registry = MagicMock()
    orch.connector_registry.source_types.return_value = []
    orch.config = MagicMock()
    orch.config.data_dir = "/tmp/test"
    orch.decay = MagicMock()
    return orch


def test_feedback_accept_endpoint():
    orch = _mock_orch()
    app = create_app(orch=orch)
    client = TestClient(app)

    resp = client.post("/api/feedback/accept", json={
        "entity_ids": ["e1", "e2"],
        "relationship_ids": ["r1"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["queued"] == 3


def test_feedback_correct_endpoint():
    orch = _mock_orch()
    app = create_app(orch=orch)
    client = TestClient(app)

    resp = client.post("/api/feedback/correct", json={
        "entity_ids": ["e1"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["queued"] == 1
