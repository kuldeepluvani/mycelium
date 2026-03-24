"""Tests for concept builder — higher-order concept formation."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.perception.concept_builder import ConceptBuilder, ConceptResult
from mycelium.shared.models import Entity


def _make_llm(return_value):
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=return_value)
    return llm


def _populated_graph(n: int) -> tuple[KnowledgeGraph, list[str]]:
    """Create a graph with n entities and return (graph, entity_ids)."""
    g = KnowledgeGraph()
    ids = []
    for i in range(n):
        eid = f"e{i}"
        g.add_entity(Entity(
            id=eid,
            name=f"Entity_{i}",
            canonical_name=f"Entity_{i}",
            entity_class="service",
            description=f"Description for entity {i}",
        ))
        ids.append(eid)
    return g, ids


@pytest.mark.asyncio
async def test_skip_small_cluster():
    llm = _make_llm(None)
    builder = ConceptBuilder(llm=llm, min_cluster_size=5)
    graph, ids = _populated_graph(3)

    result = await builder.build_concept(ids, graph)
    assert result.skipped is True
    assert "cluster_too_small" in result.skip_reason
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_build_concept():
    llm = _make_llm({
        "label": "Container Orchestration Stack",
        "description": "A set of tools for managing containerized workloads",
        "domain": "infrastructure",
    })
    builder = ConceptBuilder(llm=llm, min_cluster_size=5)
    graph, ids = _populated_graph(5)

    result = await builder.build_concept(ids, graph)
    assert result.skipped is False
    assert result.entity is not None
    assert result.entity.name == "Container Orchestration Stack"
    assert result.entity.entity_class == "concept"
    assert result.entity.entity_subclass == "synthesized"
    assert result.entity.domain == "infrastructure"
    assert result.call_cost == 1


@pytest.mark.asyncio
async def test_llm_failure():
    llm = _make_llm(None)
    builder = ConceptBuilder(llm=llm, min_cluster_size=5)
    graph, ids = _populated_graph(5)

    result = await builder.build_concept(ids, graph)
    assert result.skipped is True
    assert result.skip_reason == "llm_failed"
    assert result.call_cost == 1


@pytest.mark.asyncio
async def test_concept_has_members():
    llm = _make_llm({
        "label": "Test Concept",
        "description": "A test",
        "domain": "test",
    })
    builder = ConceptBuilder(llm=llm, min_cluster_size=5)
    graph, ids = _populated_graph(6)

    result = await builder.build_concept(ids, graph)
    assert result.member_entity_ids == ids
    assert len(result.member_entity_ids) == 6
