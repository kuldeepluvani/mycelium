"""End-to-end: cluster -> hierarchy -> route -> reason."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.network.agent_manager import AgentManager
from mycelium.network.cluster import ClusterInfo
from mycelium.serve.cortex_router import CortexRouter
from mycelium.serve.cortex_reasoner import CortexReasoner, CortexResponse
from mycelium.serve.intent import QueryIntent


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    counter = {"n": 0}

    async def smart_json(prompt, **kwargs):
        counter["n"] += 1
        return {"name": f"Agent-{counter['n']}", "domain": "backend", "description": "Specialist"}

    llm.generate_json = smart_json
    llm.generate = AsyncMock(return_value=MagicMock(content="Analysis result.", success=True))
    return llm


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    entities = {}
    for i in range(30):
        e = MagicMock()
        e.name = f"entity-{i}"
        e.entity_class = "service"
        e.domain = "backend"
        e.description = f"Entity {i}"
        entities[f"e{i}"] = e

    graph.get_entity = lambda eid: entities.get(eid)
    graph.get_neighbors = MagicMock(return_value=[])
    return graph


@pytest.mark.asyncio
async def test_full_pipeline(mock_llm, mock_graph):
    manager = AgentManager(llm=mock_llm, stability_cycles=1)
    clusters = [
        ClusterInfo(cluster_id="c1", node_ids=[f"e{i}" for i in range(15)], size=15, coherence=0.5),
        ClusterInfo(cluster_id="c2", node_ids=[f"e{i}" for i in range(15, 30)], size=15, coherence=0.5),
    ]
    await manager.process_clusters(clusters, mock_graph)

    active = manager.get_active()
    assert len(active) >= 2

    metas = manager.get_meta_agents()
    assert isinstance(metas, list)

    intent = QueryIntent(
        mentioned_entities=["e1", "e2"],
        query_type="search",
        subgraph_ids={f"e{i}" for i in range(5)},
    )
    router = CortexRouter(max_l1_agents=3)
    route = router.route(intent=intent, meta_agents=metas, l1_agents=active)

    reasoner = CortexReasoner(llm=mock_llm)
    response = await reasoner.reason(
        query="How does entity-1 work?",
        route=route,
        meta_agents={m.id: m for m in metas},
        l1_agents={a.id: a for a in active},
        graph=mock_graph,
    )

    assert isinstance(response, CortexResponse)
    # Route may hit L1s via L2 delegation or fallback depending on entity overlap.
    # With synthetic data, verify the pipeline completes without error.
    # When strategy is "self" (no entity name match), L1 responses may be empty.
    if route.strategy.mode != "self":
        assert len(response.l1_responses) >= 1
    else:
        # Verify fallback path works
        assert response.coordinated_by is not None
