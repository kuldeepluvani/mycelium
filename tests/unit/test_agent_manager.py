"""Tests for agent lifecycle management."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity
from mycelium.network.agent import Agent
from mycelium.network.agent_manager import AgentManager
from mycelium.network.cluster import ClusterInfo


def _make_entity(eid: str) -> Entity:
    return Entity(
        id=eid,
        name=eid,
        canonical_name=eid.lower(),
        entity_class="concept",
    )


def _make_graph_with_entities(ids: list[str]) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for eid in ids:
        graph.add_entity(_make_entity(eid))
    return graph


@pytest.mark.asyncio
async def test_process_clusters_creates_agents():
    llm = MagicMock()
    llm.generate_json = AsyncMock(
        return_value={"name": "TestAgent", "domain": "testing", "description": "A test agent"}
    )

    node_ids = [f"n-{i}" for i in range(12)]
    graph = _make_graph_with_entities(node_ids)
    cluster = ClusterInfo(
        cluster_id="cluster-0",
        node_ids=node_ids,
        size=12,
        coherence=0.5,
        cycles_stable=1,
    )

    manager = AgentManager(llm=llm)
    new_agents = await manager.process_clusters([cluster], graph)

    assert len(new_agents) == 1
    assert new_agents[0].name == "TestAgent"
    assert new_agents[0].domain == "testing"
    assert new_agents[0].status == "active"
    assert len(manager.agents) == 1


def test_merge_agents():
    llm = MagicMock()
    manager = AgentManager(llm=llm)

    a = Agent(id="agent-aaa", name="A", domain="d1", node_ids=["n1", "n2"])
    b = Agent(id="agent-bbb", name="B", domain="d2", node_ids=["n3", "n4"])
    manager._agents["agent-aaa"] = a
    manager._agents["agent-bbb"] = b

    merged = manager.merge("agent-aaa", "agent-bbb")

    assert merged is not None
    assert set(merged.node_ids) == {"n1", "n2", "n3", "n4"}
    assert b.status == "retired"


def test_rename_agent():
    llm = MagicMock()
    manager = AgentManager(llm=llm)

    agent = Agent(id="agent-xxx", name="OldName", domain="d")
    manager._agents["agent-xxx"] = agent

    assert manager.rename("agent-xxx", "NewName") is True
    assert agent.name == "NewName"
    assert manager.rename("nonexistent", "X") is False


def test_pin_prevents_retirement():
    llm = MagicMock()
    manager = AgentManager(llm=llm)

    agent = Agent(id="agent-pin", name="Pinned", domain="d", status="active")
    manager._agents["agent-pin"] = agent

    assert manager.pin("agent-pin") is True
    assert agent.pinned is True

    # Retirement should be blocked
    assert manager.retire("agent-pin") is False
    assert agent.status == "active"


def test_unpin_agent():
    llm = MagicMock()
    manager = AgentManager(llm=llm)

    agent = Agent(id="a1", name="Test", domain="test", status="active", pinned=True)
    manager._agents["a1"] = agent

    assert manager.unpin("a1") is True
    assert agent.pinned is False
    assert manager.unpin("nonexistent") is False
