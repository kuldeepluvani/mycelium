"""Tests for feedback + decay integration in learn cycle."""
from __future__ import annotations

import sqlite3
import tempfile
import os
import pytest

from mycelium.shared.models import Entity, Relationship
from mycelium.shared.config import DecayConfig
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.brainstem.decay import DecayEngine
from mycelium.serve.feedback import FeedbackLoop


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "brainstem.db")
    s.initialize()
    return s


@pytest.fixture
def graph():
    return KnowledgeGraph()


@pytest.fixture
def decay():
    return DecayEngine(DecayConfig())


def test_update_entity_confidence(store):
    """BrainstemStore.update_entity_confidence writes to SQLite."""
    entity = Entity(id="e1", name="Test", canonical_name="Test", entity_class="service", confidence=0.5)
    store.upsert_entity(entity)
    store.update_entity_confidence("e1", 0.85)
    reloaded = store.get_entity("e1")
    assert reloaded.confidence == 0.85


def test_feedback_apply_pending_boosts(store, graph, decay):
    """Positive feedback boosts entity confidence."""
    entity = Entity(id="e1", name="Test", canonical_name="Test", entity_class="service", confidence=0.5)
    graph.add_entity(entity)
    store.upsert_entity(entity)

    fb = FeedbackLoop(store=store)
    fb.record_acceptance(entity_ids=["e1"])

    applied = fb.apply_pending(store, graph, decay)
    assert applied == 1
    assert graph.get_entity("e1").confidence == 0.53  # 0.5 + 0.03
    assert store.get_entity("e1").confidence == 0.53


def test_feedback_apply_pending_penalizes(store, graph, decay):
    """Negative feedback penalizes entity confidence."""
    entity = Entity(id="e1", name="Test", canonical_name="Test", entity_class="service", confidence=0.5)
    graph.add_entity(entity)
    store.upsert_entity(entity)

    fb = FeedbackLoop(store=store)
    fb.record_correction(entity_ids=["e1"])

    applied = fb.apply_pending(store, graph, decay)
    assert applied == 1
    assert graph.get_entity("e1").confidence == 0.45  # 0.5 - 0.05
    assert store.get_entity("e1").confidence == 0.45


def test_decay_applied_to_all_entities(store, graph, decay):
    """Decay reduces confidence on all entities per category."""
    e1 = Entity(id="e1", name="A", canonical_name="A", entity_class="service", confidence=0.80)
    graph.add_entity(e1)
    store.upsert_entity(e1)

    # Simulate decay pass — semantic category = 0.10 decay rate
    for eid in graph.all_entity_ids():
        entity = graph.get_entity(eid)
        if entity:
            new_conf = decay.apply_decay(entity.confidence, "semantic")
            entity.confidence = new_conf
            store.update_entity_confidence(entity.id, new_conf)

    assert graph.get_entity("e1").confidence == pytest.approx(0.72, abs=0.01)
