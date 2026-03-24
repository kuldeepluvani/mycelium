"""Tests for entity resolver — multi-signal deduplication pipeline."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from mycelium.brainstem.embeddings import SearchResult
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.perception.entity_resolver import EntityResolver, ResolutionResult
from mycelium.shared.models import Entity


def _make_entity(
    id: str,
    name: str,
    entity_class: str = "service",
    aliases: list[str] | None = None,
) -> Entity:
    return Entity(
        id=id,
        name=name,
        canonical_name=name,
        entity_class=entity_class,
        aliases=aliases or [],
    )


def _graph_with(*entities: Entity) -> KnowledgeGraph:
    g = KnowledgeGraph()
    for e in entities:
        g.add_entity(e)
    return g


@pytest.mark.asyncio
async def test_exact_name_match():
    graph = _graph_with(_make_entity("e1", "Kubernetes"))
    resolver = EntityResolver(graph=graph)
    result = await resolver.resolve("kubernetes", "service")
    assert result.action == "merge"
    assert result.existing_id == "e1"
    assert result.reason == "exact_name_match"


@pytest.mark.asyncio
async def test_alias_match():
    graph = _graph_with(_make_entity("e1", "Kubernetes", aliases=["k8s"]))
    resolver = EntityResolver(graph=graph)
    result = await resolver.resolve("k8s", "service")
    assert result.action == "merge"
    assert result.existing_id == "e1"
    assert result.reason == "alias_match"


@pytest.mark.asyncio
async def test_no_match_creates():
    graph = KnowledgeGraph()
    resolver = EntityResolver(graph=graph)
    result = await resolver.resolve("anything", "service")
    assert result.action == "create"
    assert result.reason == "no_match"


@pytest.mark.asyncio
async def test_embedding_similarity():
    entity = _make_entity("e1", "Kubernetes", entity_class="service")
    graph = _graph_with(entity)

    embeddings = MagicMock()
    embeddings.count = 1
    embeddings.search.return_value = [SearchResult(entity_id="e1", score=0.92)]

    resolver = EntityResolver(graph=graph, embeddings=embeddings, similarity_threshold=0.85)
    result = await resolver.resolve("K8s orchestration", "service")
    # Exact name doesn't match "K8s orchestration" != "Kubernetes", no alias,
    # so it falls through to embeddings
    assert result.action == "merge"
    assert result.existing_id == "e1"
    assert "embedding_similarity" in result.reason


@pytest.mark.asyncio
async def test_embedding_different_class_relates():
    entity = _make_entity("e1", "Kubernetes", entity_class="service")
    graph = _graph_with(entity)

    embeddings = MagicMock()
    embeddings.count = 1
    embeddings.search.return_value = [SearchResult(entity_id="e1", score=0.90)]

    resolver = EntityResolver(graph=graph, embeddings=embeddings, similarity_threshold=0.85)
    # Different entity_class → relate instead of merge
    result = await resolver.resolve("K8s orchestration", "concept")
    assert result.action == "relate"
    assert result.existing_id == "e1"
    assert result.relationship_type == "related_to"
    assert "diff_class" in result.reason


@pytest.mark.asyncio
async def test_resolve_batch():
    graph = _graph_with(
        _make_entity("e1", "Kubernetes"),
        _make_entity("e2", "Docker"),
    )
    resolver = EntityResolver(graph=graph)
    results = await resolver.resolve_batch([
        {"name": "kubernetes", "entity_class": "service"},
        {"name": "Docker", "entity_class": "service"},
        {"name": "Terraform", "entity_class": "tool"},
    ])
    assert len(results) == 3
    assert results[0].action == "merge"
    assert results[1].action == "merge"
    assert results[2].action == "create"
