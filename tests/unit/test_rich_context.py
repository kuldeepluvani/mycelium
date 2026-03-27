"""Tests for enriched agent context in reasoning."""
from __future__ import annotations
import pytest
from mycelium.shared.models import Entity, Relationship
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.serve.context_builder import build_agent_context


def test_context_includes_entity_details():
    graph = KnowledgeGraph()
    e1 = Entity(id="e1", name="AuthService", canonical_name="AuthService",
                entity_class="service", description="Handles authentication", confidence=0.85)
    graph.add_entity(e1)

    context = build_agent_context(graph, ["e1"])
    assert "AuthService" in context
    assert "service" in context
    assert "85%" in context
    assert "Handles authentication" in context


def test_context_includes_relationship_metadata():
    graph = KnowledgeGraph()
    e1 = Entity(id="e1", name="AuthService", canonical_name="AuthService",
                entity_class="service", confidence=0.85)
    e2 = Entity(id="e2", name="Redis", canonical_name="Redis",
                entity_class="infra", confidence=0.90)
    graph.add_entity(e1)
    graph.add_entity(e2)

    rel = Relationship(id="r1", source_id="e1", target_id="e2",
                      rel_type="depends_on", rel_category="structural",
                      rationale="Uses Redis for session token caching",
                      confidence=0.80)
    graph.add_relationship(rel)

    context = build_agent_context(graph, ["e1", "e2"])
    assert "depends_on" in context
    assert "Redis" in context
    assert "session token caching" in context
    assert "0.8" in context


def test_context_shows_direction():
    graph = KnowledgeGraph()
    e1 = Entity(id="e1", name="A", canonical_name="A", entity_class="service", confidence=0.7)
    e2 = Entity(id="e2", name="B", canonical_name="B", entity_class="service", confidence=0.7)
    graph.add_entity(e1)
    graph.add_entity(e2)

    rel = Relationship(id="r1", source_id="e1", target_id="e2",
                      rel_type="calls", rel_category="structural", confidence=0.6)
    graph.add_relationship(rel)

    context = build_agent_context(graph, ["e1", "e2"])
    assert "\u2192" in context  # outgoing from e1
    assert "\u2190" in context  # incoming to e2


def test_context_respects_limits():
    graph = KnowledgeGraph()
    for i in range(20):
        graph.add_entity(Entity(id=f"e{i}", name=f"Ent{i}", canonical_name=f"Ent{i}",
                               entity_class="service", confidence=0.5))

    context = build_agent_context(graph, [f"e{i}" for i in range(20)], max_entities=5)
    # Should only include first 5 entities
    assert "Ent0" in context
    assert "Ent4" in context
    assert "Ent5" not in context


def test_empty_node_ids():
    graph = KnowledgeGraph()
    context = build_agent_context(graph, [])
    assert context == ""
