"""Tests for mycelium.serve.reasoner."""
from __future__ import annotations
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity
from mycelium.shared.llm import CLIResponse
from mycelium.serve.router import RoutedAgent
from mycelium.serve.reasoner import ParallelReasoner


def _graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_entity(Entity(id="e1", name="Redis", canonical_name="redis", entity_class="service"))
    g.add_entity(Entity(id="e2", name="Postgres", canonical_name="postgres", entity_class="service"))
    return g


def _agent(aid: str, name: str, node_ids: list[str]) -> SimpleNamespace:
    return SimpleNamespace(id=aid, name=name, domain="infrastructure", node_ids=node_ids)


def test_parallel_reasoning():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=CLIResponse(content="Analysis complete.", duration_ms=100, success=True))

    reasoner = ParallelReasoner(llm)
    routed = [
        RoutedAgent(agent_id="a1", agent_name="Agent1", relevance=0.8, owned_nodes_in_subgraph=2),
        RoutedAgent(agent_id="a2", agent_name="Agent2", relevance=0.5, owned_nodes_in_subgraph=1),
    ]
    details = {
        "a1": _agent("a1", "Agent1", ["e1"]),
        "a2": _agent("a2", "Agent2", ["e2"]),
    }
    g = _graph()

    responses = asyncio.get_event_loop().run_until_complete(
        reasoner.reason("what is redis", routed, details, g)
    )
    assert len(responses) == 2
    assert all(r.success for r in responses)


def test_handles_failure():
    call_count = 0

    async def mock_generate(prompt, system=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return CLIResponse(content="OK", duration_ms=50, success=True)
        return CLIResponse(content="", duration_ms=50, success=False, error="timeout")

    llm = AsyncMock()
    llm.generate = mock_generate

    reasoner = ParallelReasoner(llm)
    routed = [
        RoutedAgent(agent_id="a1", agent_name="Agent1", relevance=0.8, owned_nodes_in_subgraph=1),
        RoutedAgent(agent_id="a2", agent_name="Agent2", relevance=0.5, owned_nodes_in_subgraph=1),
    ]
    details = {
        "a1": _agent("a1", "Agent1", ["e1"]),
        "a2": _agent("a2", "Agent2", ["e2"]),
    }
    g = _graph()

    responses = asyncio.get_event_loop().run_until_complete(
        reasoner.reason("query", routed, details, g)
    )
    assert len(responses) == 2
    successes = [r for r in responses if r.success]
    failures = [r for r in responses if not r.success]
    assert len(successes) >= 1
    assert len(failures) >= 1
