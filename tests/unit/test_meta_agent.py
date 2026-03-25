from mycelium.network.meta_agent import MetaAgent, ChildManifest, DelegationStrategy
from mycelium.network.agent import Agent


def _child(agent_id, name, domain, entities):
    return ChildManifest(
        agent_id=agent_id,
        agent_name=name,
        domain=domain,
        confidence=0.8,
        entity_count=20,
        key_entities=entities,
    )


def test_meta_agent_creation():
    child = _child("agent-abc", "K8s Specialist", "kubernetes", ["gke", "pods"])
    meta = MetaAgent(id="meta-001", name="Infra Cortex", domain="infra", children=[child])
    assert meta.id == "meta-001"
    assert len(meta.children) == 1
    assert meta.tier == 2


def test_delegation_direct_single_child():
    meta = MetaAgent(
        id="m1", name="Test", domain="test",
        children=[_child("a1", "Redis", "cache", ["redis", "cache", "ttl"])],
    )
    strategy = meta.pick_strategy({"redis", "cache"})
    assert strategy.mode == "direct"
    assert strategy.target_ids == ["a1"]


def test_delegation_fanout_multiple_children():
    meta = MetaAgent(
        id="m1", name="Test", domain="test",
        children=[
            _child("a1", "Cache", "caching", ["redis", "cache"]),
            _child("a2", "Auth", "auth", ["session", "jwt"]),
        ],
    )
    strategy = meta.pick_strategy({"redis", "session", "timeout"})
    assert strategy.mode == "fanout"
    assert set(strategy.target_ids) == {"a1", "a2"}


def test_delegation_self_when_no_match():
    meta = MetaAgent(
        id="m1", name="Test", domain="test",
        children=[_child("a1", "Cache", "caching", ["redis"])],
    )
    strategy = meta.pick_strategy({"quantum", "physics"})
    assert strategy.mode == "self"


def test_agent_parent_id():
    agent = Agent(id="a1", name="Test", domain="test", parent_id="meta-001")
    assert agent.parent_id == "meta-001"


def test_agent_parent_id_default_none():
    agent = Agent(id="a1", name="Test", domain="test")
    assert agent.parent_id is None
