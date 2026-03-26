"""Tests for catch-all agent that covers unclustered entities."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.shared.models import Entity
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.network.agent_manager import AgentManager
from mycelium.network.cluster import ClusterInfo


@pytest.fixture
def graph():
    g = KnowledgeGraph()
    for i in range(10):
        g.add_entity(Entity(
            id=f"e{i}", name=f"Entity{i}", canonical_name=f"Entity{i}",
            entity_class="service", confidence=0.7,
        ))
    return g


@pytest.fixture
def llm():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={
        "name": "Test Agent", "domain": "testing", "description": "test agent",
    })
    return llm


@pytest.mark.asyncio
async def test_ensure_catchall_creates_agent_for_orphans(graph, llm):
    """After clustering, orphan entities should be assigned to a catch-all agent."""
    mgr = AgentManager(llm=llm, stability_cycles=1)
    clusters = [ClusterInfo(cluster_id="cluster-0", node_ids=[f"e{i}" for i in range(5)], size=5, coherence=0.5)]
    await mgr.process_clusters(clusters, graph)
    mgr.ensure_catchall(graph)

    all_covered = set()
    for a in mgr.agents:
        all_covered.update(a.node_ids)
    assert len(all_covered) == 10
    assert all_covered == set(graph.all_entity_ids())


@pytest.mark.asyncio
async def test_catchall_agent_is_named_general_knowledge(graph, llm):
    """Catch-all agent should have a recognizable name."""
    mgr = AgentManager(llm=llm, stability_cycles=1)
    clusters = [ClusterInfo(cluster_id="cluster-0", node_ids=["e0", "e1", "e2"], size=3, coherence=0.5)]
    await mgr.process_clusters(clusters, graph)
    mgr.ensure_catchall(graph)

    catchall = [a for a in mgr.agents if a.name == "General Knowledge"]
    assert len(catchall) == 1


@pytest.mark.asyncio
async def test_catchall_updates_existing_on_rerun(graph, llm):
    """Running ensure_catchall again should update the existing catch-all, not create a second."""
    mgr = AgentManager(llm=llm, stability_cycles=1)
    clusters = [ClusterInfo(cluster_id="cluster-0", node_ids=["e0", "e1"], size=2, coherence=0.5)]
    await mgr.process_clusters(clusters, graph)
    mgr.ensure_catchall(graph)
    mgr.ensure_catchall(graph)

    catchalls = [a for a in mgr.agents if a.name == "General Knowledge"]
    assert len(catchalls) == 1


@pytest.mark.asyncio
async def test_no_catchall_when_all_covered(graph, llm):
    """If all entities are in clusters, no catch-all should be created."""
    mgr = AgentManager(llm=llm, stability_cycles=1)
    all_ids = graph.all_entity_ids()
    clusters = [ClusterInfo(cluster_id="cluster-0", node_ids=all_ids, size=len(all_ids), coherence=0.5)]
    await mgr.process_clusters(clusters, graph)
    mgr.ensure_catchall(graph)

    catchalls = [a for a in mgr.agents if a.name == "General Knowledge"]
    assert len(catchalls) == 0
