"""Tests for cross-document relationship enrichment."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.shared.models import Entity, Relationship
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.perception.relationship_builder import RelationshipBuilder


@pytest.fixture
def graph():
    g = KnowledgeGraph()
    # Two entities from different documents, same class
    g.add_entity(Entity(id="e1", name="AuthService", canonical_name="AuthService",
                        entity_class="service", provenance=["doc-1"], confidence=0.8))
    g.add_entity(Entity(id="e2", name="UserService", canonical_name="UserService",
                        entity_class="service", provenance=["doc-2"], confidence=0.8))
    # Entity from same doc as e1 (should not be a candidate with e1)
    g.add_entity(Entity(id="e3", name="SessionStore", canonical_name="SessionStore",
                        entity_class="service", provenance=["doc-1"], confidence=0.7))
    return g


@pytest.fixture
def store(tmp_path, graph):
    s = BrainstemStore(tmp_path / "test.db")
    s.initialize()
    # Persist entities so FK constraints are satisfied
    for eid in graph.all_entity_ids():
        e = graph.get_entity(eid)
        if e:
            s.upsert_entity(e)
    return s


def _make_llm(return_value):
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=return_value)
    return llm


@pytest.mark.asyncio
async def test_finds_cross_doc_candidates(graph, store):
    """Should find relationship between entities from different documents."""
    llm = _make_llm({
        "relationships": [
            {
                "source": "AuthService",
                "target": "UserService",
                "rel_type": "communicates_with",
                "rel_category": "structural",
                "rationale": "Auth delegates user lookup",
                "confidence": 0.7,
            }
        ]
    })

    builder = RelationshipBuilder(llm, batch_size=15)
    new_count = await builder.enrich_cross_document(graph, store, budget=3)

    # Should have found the cross-doc pair and created an edge
    assert new_count >= 1
    # The relationship should exist in the graph now
    assert graph.edge_count() >= 1


@pytest.mark.asyncio
async def test_skips_same_doc_entities(graph, store):
    """Should NOT create relationships between entities from the same document."""
    # Remove e2 so only e1 and e3 remain (both from doc-1)
    graph.remove_entity("e2")

    llm = _make_llm({"relationships": []})
    builder = RelationshipBuilder(llm, batch_size=15)

    new_count = await builder.enrich_cross_document(graph, store, budget=3)
    assert new_count == 0
    # LLM should not even be called since e1 and e3 share doc-1
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_skips_existing_edges(graph, store):
    """Should not duplicate edges that already exist."""
    # Pre-add an edge between e1 and e2
    existing_rel = Relationship(
        id="r-existing", source_id="e1", target_id="e2",
        rel_type="depends_on", rel_category="structural",
        confidence=0.9,
    )
    graph.add_relationship(existing_rel)

    llm = _make_llm({"relationships": []})
    builder = RelationshipBuilder(llm, batch_size=15)

    new_count = await builder.enrich_cross_document(graph, store, budget=3)
    # e1-e2 already connected, e1-e3 share doc-1, e2-e3 are cross-doc same class
    # so there may be candidates for e2-e3 but LLM returns nothing
    assert new_count == 0


@pytest.mark.asyncio
async def test_no_candidates_returns_zero():
    """Empty graph should return 0 without LLM calls."""
    g = KnowledgeGraph()
    llm = _make_llm({"relationships": []})
    store = MagicMock()

    builder = RelationshipBuilder(llm, batch_size=15)
    new_count = await builder.enrich_cross_document(g, store, budget=3)

    assert new_count == 0
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_domain_match_cross_doc():
    """Entities with same domain but different docs should be candidates."""
    g = KnowledgeGraph()
    g.add_entity(Entity(id="e1", name="APIGateway", canonical_name="APIGateway",
                        entity_class="infrastructure", domain="networking",
                        provenance=["doc-a"], confidence=0.8))
    g.add_entity(Entity(id="e2", name="LoadBalancer", canonical_name="LoadBalancer",
                        entity_class="resource", domain="networking",
                        provenance=["doc-b"], confidence=0.8))

    llm = _make_llm({
        "relationships": [
            {
                "source": "APIGateway",
                "target": "LoadBalancer",
                "rel_type": "routes_through",
                "rel_category": "structural",
                "rationale": "API gateway routes via load balancer",
                "confidence": 0.75,
            }
        ]
    })

    store = MagicMock()
    store.upsert_relationship = MagicMock()

    builder = RelationshipBuilder(llm, batch_size=15)
    new_count = await builder.enrich_cross_document(g, store, budget=3)

    assert new_count == 1
    store.upsert_relationship.assert_called_once()
