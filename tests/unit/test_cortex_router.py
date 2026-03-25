from mycelium.serve.cortex_router import CortexRouter
from mycelium.serve.intent import QueryIntent
from mycelium.network.agent import Agent
from mycelium.network.meta_agent import MetaAgent, ChildManifest


def _child(agent_id, name, domain, entities):
    return ChildManifest(
        agent_id=agent_id, agent_name=name, domain=domain,
        confidence=0.8, entity_count=20, key_entities=entities,
    )


def _meta(id, name, domain, children):
    return MetaAgent(id=id, name=name, domain=domain, children=children)


def _agent(id, name, domain, node_ids, parent_id=None):
    return Agent(
        id=id, name=name, domain=domain,
        node_ids=node_ids, status="active", parent_id=parent_id,
    )


def test_routes_via_l2_to_l1():
    meta = _meta("m1", "Infra Cortex", "infra", [
        _child("a1", "K8s Expert", "k8s", ["pods", "nodes"]),
    ])
    l1 = _agent("a1", "K8s Expert", "k8s", ["e1", "e2"], parent_id="m1")
    intent = QueryIntent(
        mentioned_entities=["e1"],
        query_type="search",
        subgraph_ids={"e1", "e2"},
    )
    router = CortexRouter(max_l1_agents=3)
    route = router.route(intent, meta_agents=[meta], l1_agents=[l1])
    assert route.meta_agent_id == "m1"


def test_fallback_to_orphan_l1():
    orphan = _agent("a-orphan", "Lone", "misc", ["e1", "e2"])
    intent = QueryIntent(
        mentioned_entities=[],
        query_type="general",
        subgraph_ids={"e1"},
    )
    router = CortexRouter(max_l1_agents=3)
    route = router.route(intent, meta_agents=[], l1_agents=[orphan])
    assert route.meta_agent_id is None
    assert "a-orphan" in route.fallback_agent_ids


def test_no_match_returns_empty():
    intent = QueryIntent(
        mentioned_entities=[],
        query_type="general",
        subgraph_ids=set(),
    )
    router = CortexRouter()
    route = router.route(intent, meta_agents=[], l1_agents=[])
    assert route.meta_agent_id is None
    assert route.fallback_agent_ids == []
