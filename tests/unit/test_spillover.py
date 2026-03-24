"""Tests for cross-domain spillover engine."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity, Relationship
from mycelium.network.agent import Agent
from mycelium.network.spillover import SpilloverEngine


def _make_entity(eid: str) -> Entity:
    return Entity(
        id=eid,
        name=eid,
        canonical_name=eid.lower(),
        entity_class="concept",
    )


def _make_rel(source: str, target: str) -> Relationship:
    return Relationship(
        id=f"r-{source}-{target}",
        source_id=source,
        target_id=target,
        rel_type="related_to",
        rel_category="semantic",
    )


@pytest.mark.asyncio
async def test_insufficient_edges_skipped():
    llm = MagicMock()
    graph = KnowledgeGraph()

    # Two agents with only 2 cross-edges (threshold is 5)
    a_ids = [f"a-{i}" for i in range(5)]
    b_ids = [f"b-{i}" for i in range(5)]
    for eid in a_ids + b_ids:
        graph.add_entity(_make_entity(eid))

    # Only 2 cross-edges
    graph.add_relationship(_make_rel("a-0", "b-0"))
    graph.add_relationship(_make_rel("a-1", "b-1"))

    agent_a = Agent(id="aa", name="A", domain="d1", node_ids=a_ids)
    agent_b = Agent(id="bb", name="B", domain="d2", node_ids=b_ids)

    engine = SpilloverEngine(llm=llm, edge_threshold=5)
    result = await engine.analyze_pair(agent_a, agent_b, graph)

    assert result.skipped is True
    assert "insufficient_edges" in result.skip_reason


@pytest.mark.asyncio
async def test_analyze_pair_creates_relationships():
    llm = MagicMock()
    llm.generate_json = AsyncMock(
        return_value={
            "missing_connections": [
                {
                    "source": "a-0",
                    "target": "b-2",
                    "rel_type": "depends_on",
                    "rationale": "shared config",
                    "spillover_type": "dependency_chain",
                }
            ]
        }
    )

    graph = KnowledgeGraph()
    a_ids = [f"a-{i}" for i in range(5)]
    b_ids = [f"b-{i}" for i in range(5)]
    for eid in a_ids + b_ids:
        graph.add_entity(_make_entity(eid))

    # 5 cross-edges to meet threshold
    for i in range(5):
        graph.add_relationship(_make_rel(f"a-{i}", f"b-{i}"))

    agent_a = Agent(id="aa", name="A", domain="d1", node_ids=a_ids)
    agent_b = Agent(id="bb", name="B", domain="d2", node_ids=b_ids)

    engine = SpilloverEngine(llm=llm, edge_threshold=5)
    result = await engine.analyze_pair(agent_a, agent_b, graph)

    assert result.skipped is False
    assert len(result.new_relationships) == 1
    assert result.new_relationships[0].rel_type == "depends_on"
    assert result.call_cost == 1


@pytest.mark.asyncio
async def test_llm_failure():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=None)

    graph = KnowledgeGraph()
    a_ids = [f"a-{i}" for i in range(5)]
    b_ids = [f"b-{i}" for i in range(5)]
    for eid in a_ids + b_ids:
        graph.add_entity(_make_entity(eid))

    for i in range(5):
        graph.add_relationship(_make_rel(f"a-{i}", f"b-{i}"))

    agent_a = Agent(id="aa", name="A", domain="d1", node_ids=a_ids)
    agent_b = Agent(id="bb", name="B", domain="d2", node_ids=b_ids)

    engine = SpilloverEngine(llm=llm, edge_threshold=5)
    result = await engine.analyze_pair(agent_a, agent_b, graph)

    assert result.skipped is False
    assert len(result.new_relationships) == 0
    assert result.call_cost == 1
