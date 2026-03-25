import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.network.hierarchy_builder import HierarchyBuilder
from mycelium.network.agent import Agent
from mycelium.network.meta_agent import MetaAgent


def _make_agent(id, name, domain, node_ids):
    return Agent(id=id, name=name, domain=domain, node_ids=node_ids, status="active")


def _mock_graph(domain="backend"):
    graph = MagicMock()
    entity = MagicMock()
    entity.name = "test-entity"
    entity.entity_class = "service"
    entity.domain = domain
    entity.description = "test"
    graph.get_entity = MagicMock(return_value=entity)
    return graph


def _mock_llm():
    llm = AsyncMock()
    llm.generate_json = AsyncMock(return_value={
        "name": "Test Cortex",
        "domain": "test",
        "description": "Coordinates test agents",
    })
    return llm


@pytest.mark.asyncio
async def test_builds_hierarchy_from_overlapping_agents():
    agents = [
        _make_agent("a1", "Agent A", "backend", ["e1", "e2"]),
        _make_agent("a2", "Agent B", "backend", ["e2", "e3"]),
    ]
    builder = HierarchyBuilder(llm=_mock_llm(), min_group_size=2)
    metas = await builder.build(agents, _mock_graph())
    assert len(metas) == 1
    assert isinstance(metas[0], MetaAgent)
    assert len(metas[0].children) == 2


@pytest.mark.asyncio
async def test_single_agent_no_hierarchy():
    agents = [_make_agent("a1", "Lone", "misc", ["e1"])]
    builder = HierarchyBuilder(llm=_mock_llm(), min_group_size=2)
    metas = await builder.build(agents, _mock_graph())
    assert len(metas) == 0


@pytest.mark.asyncio
async def test_children_get_parent_id():
    agents = [
        _make_agent("a1", "Agent A", "backend", ["e1"]),
        _make_agent("a2", "Agent B", "backend", ["e2"]),
    ]
    builder = HierarchyBuilder(llm=_mock_llm(), min_group_size=2)
    metas = await builder.build(agents, _mock_graph())
    assert len(metas) == 1
    for agent in agents:
        assert agent.parent_id == metas[0].id


@pytest.mark.asyncio
async def test_llm_failure_still_creates_meta():
    llm = AsyncMock()
    llm.generate_json = AsyncMock(return_value=None)
    agents = [
        _make_agent("a1", "A", "backend", ["e1"]),
        _make_agent("a2", "B", "backend", ["e2"]),
    ]
    builder = HierarchyBuilder(llm=llm, min_group_size=2)
    metas = await builder.build(agents, _mock_graph())
    assert len(metas) == 1
    assert metas[0].name.startswith("Meta-")
