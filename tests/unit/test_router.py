"""Tests for mycelium.serve.router."""
from __future__ import annotations
from types import SimpleNamespace
from mycelium.serve.intent import QueryIntent
from mycelium.serve.router import AgentRouter


def _agent(aid: str, name: str, node_ids: list[str], status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(id=aid, name=name, node_ids=node_ids, status=status)


def test_select_top_agents():
    intent = QueryIntent(
        mentioned_entities=["a"],
        query_type="search",
        subgraph_ids={"a", "b", "c", "d"},
    )
    agents = [
        _agent("ag1", "Agent1", ["a", "b", "c"]),  # 3/4 overlap
        _agent("ag2", "Agent2", ["a"]),              # 1/4 overlap
        _agent("ag3", "Agent3", ["a", "b"]),         # 2/4 overlap
    ]
    router = AgentRouter(max_agents=2)
    result = router.select(intent, agents)
    assert len(result) == 2
    assert result[0].agent_id == "ag1"
    assert result[1].agent_id == "ag3"


def test_no_agents_empty():
    intent = QueryIntent(mentioned_entities=[], query_type="general", subgraph_ids={"a"})
    router = AgentRouter()
    assert router.select(intent, []) == []


def test_inactive_agents_excluded():
    intent = QueryIntent(
        mentioned_entities=["a"],
        query_type="search",
        subgraph_ids={"a", "b"},
    )
    agents = [
        _agent("ag1", "Retired", ["a", "b"], status="retired"),
        _agent("ag2", "Active", ["a"], status="active"),
    ]
    router = AgentRouter()
    result = router.select(intent, agents)
    assert len(result) == 1
    assert result[0].agent_id == "ag2"
