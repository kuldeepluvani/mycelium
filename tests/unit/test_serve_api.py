"""Tests for mycelium.serve.api."""
from __future__ import annotations
from fastapi.testclient import TestClient
from mycelium.serve.api import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ask_placeholder():
    app = create_app()
    client = TestClient(app)
    resp = client.post("/ask", json={"query": "what is kubernetes"})
    assert resp.status_code == 200
    data = resp.json()
    assert "not yet initialized" in data["answer"]
