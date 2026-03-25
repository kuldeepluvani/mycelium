import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.serve.cortex_reasoner import CortexReasoner, CortexResponse
from mycelium.serve.cortex_router import CortexRoute
from mycelium.network.meta_agent import MetaAgent, ChildManifest, DelegationStrategy
from mycelium.network.agent import Agent


def _mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=MagicMock(
        content="Analysis based on domain knowledge.", success=True,
    ))
    return llm


def _mock_graph():
    graph = MagicMock()
    entity = MagicMock()
    entity.name = "redis"
    entity.entity_class = "service"
    graph.get_entity = MagicMock(return_value=entity)
    graph.get_neighbors = MagicMock(return_value=["e2"])
    return graph


@pytest.mark.asyncio
async def test_direct_delegation():
    l1 = Agent(id="a1", name="Cache Expert", domain="caching",
               node_ids=["e1"], status="active", parent_id="m1")
    meta = MetaAgent(
        id="m1", name="Backend Cortex", domain="backend",
        children=[ChildManifest(
            agent_id="a1", agent_name="Cache Expert", domain="caching",
            confidence=0.9, entity_count=10, key_entities=["redis"],
        )],
    )
    route = CortexRoute(
        meta_agent_id="m1", meta_agent_name="Backend Cortex",
        strategy=DelegationStrategy(mode="direct", target_ids=["a1"]),
    )
    reasoner = CortexReasoner(llm=_mock_llm())
    resp = await reasoner.reason(
        query="Redis TTL?",
        route=route,
        meta_agents={"m1": meta},
        l1_agents={"a1": l1},
        graph=_mock_graph(),
    )
    assert isinstance(resp, CortexResponse)
    assert resp.coordinated_by == "Backend Cortex"
    assert len(resp.l1_responses) == 1
    assert resp.synthesis == ""  # No synthesis on direct


@pytest.mark.asyncio
async def test_fanout_produces_synthesis():
    l1_a = Agent(id="a1", name="Cache", domain="caching",
                 node_ids=["e1"], status="active", parent_id="m1")
    l1_b = Agent(id="a2", name="Auth", domain="auth",
                 node_ids=["e2"], status="active", parent_id="m1")
    meta = MetaAgent(
        id="m1", name="Backend Cortex", domain="backend",
        children=[
            ChildManifest(agent_id="a1", agent_name="Cache", domain="caching",
                          confidence=0.9, entity_count=10, key_entities=["redis"]),
            ChildManifest(agent_id="a2", agent_name="Auth", domain="auth",
                          confidence=0.7, entity_count=8, key_entities=["session"]),
        ],
    )
    route = CortexRoute(
        meta_agent_id="m1", meta_agent_name="Backend Cortex",
        strategy=DelegationStrategy(mode="fanout", target_ids=["a1", "a2"]),
    )
    reasoner = CortexReasoner(llm=_mock_llm())
    resp = await reasoner.reason(
        query="Session caching?",
        route=route,
        meta_agents={"m1": meta},
        l1_agents={"a1": l1_a, "a2": l1_b},
        graph=_mock_graph(),
    )
    assert len(resp.l1_responses) == 2
    assert resp.synthesis != ""  # L2 synthesized


@pytest.mark.asyncio
async def test_fallback_no_meta():
    l1 = Agent(id="a1", name="Orphan", domain="misc",
               node_ids=["e1"], status="active")
    route = CortexRoute(fallback_agent_ids=["a1"])
    reasoner = CortexReasoner(llm=_mock_llm())
    resp = await reasoner.reason(
        query="Test?",
        route=route,
        meta_agents={},
        l1_agents={"a1": l1},
        graph=_mock_graph(),
    )
    assert resp.coordinated_by == "System"
    assert len(resp.l1_responses) == 1
