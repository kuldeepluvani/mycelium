"""Tests for batch entity deduplication."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from mycelium.shared.models import Entity, Relationship
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.perception.entity_resolver import EntityResolver


@pytest.fixture
def graph():
    return KnowledgeGraph()


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "test.db")
    s.initialize()
    return s


def test_batch_scan_finds_exact_name_duplicates(graph, store):
    """Entities with same canonical_name (case-insensitive) are flagged as duplicates."""
    e1 = Entity(id="e1", name="Kubernetes", canonical_name="kubernetes", entity_class="infra", confidence=0.8)
    e2 = Entity(id="e2", name="kubernetes", canonical_name="kubernetes", entity_class="infra", confidence=0.5)
    graph.add_entity(e1)
    graph.add_entity(e2)
    store.upsert_entity(e1)
    store.upsert_entity(e2)

    resolver = EntityResolver(graph, embeddings=None, llm=MagicMock())
    merge_pairs = resolver.batch_find_duplicates()

    assert len(merge_pairs) == 1
    assert set(merge_pairs[0]) == {"e1", "e2"}


def test_batch_scan_finds_alias_duplicates(graph, store):
    """Entity whose name matches another entity's alias should be flagged."""
    e1 = Entity(id="e1", name="K8s", canonical_name="K8s", entity_class="infra", aliases=["kubernetes", "k8s"], confidence=0.8)
    e2 = Entity(id="e2", name="Kubernetes", canonical_name="Kubernetes", entity_class="infra", confidence=0.5)
    graph.add_entity(e1)
    graph.add_entity(e2)

    resolver = EntityResolver(graph, embeddings=None, llm=MagicMock())
    merge_pairs = resolver.batch_find_duplicates()

    assert len(merge_pairs) == 1


def test_batch_merge_combines_entities(graph, store):
    """Merging two entities should combine provenance, keep higher confidence, transfer edges."""
    e1 = Entity(id="e1", name="Redis", canonical_name="Redis", entity_class="infra",
                confidence=0.8, provenance=["doc-1"])
    e2 = Entity(id="e2", name="redis", canonical_name="redis", entity_class="infra",
                confidence=0.5, provenance=["doc-2"])
    e3 = Entity(id="e3", name="AuthService", canonical_name="AuthService", entity_class="service")
    graph.add_entity(e1)
    graph.add_entity(e2)
    graph.add_entity(e3)
    store.upsert_entity(e1)
    store.upsert_entity(e2)
    store.upsert_entity(e3)

    # e2 has a relationship to e3
    rel = Relationship(id="r1", source_id="e2", target_id="e3",
                       rel_type="depends_on", rel_category="structural")
    graph.add_relationship(rel)
    store.upsert_relationship(rel)

    resolver = EntityResolver(graph, embeddings=None, llm=MagicMock())
    merged = resolver.merge_entities("e1", "e2", store)

    assert merged is not None
    assert merged.confidence == 0.8  # kept higher
    assert "doc-1" in merged.provenance
    assert "doc-2" in merged.provenance
    assert not graph.has_entity("e2")  # removed
    assert graph.has_entity("e1")  # survivor
