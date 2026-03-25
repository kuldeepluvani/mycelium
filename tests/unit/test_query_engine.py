import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.serve.query_engine import QueryEngine, QueryResult


@pytest.fixture
def mock_orch():
    orch = MagicMock()
    orch._llm = AsyncMock()
    orch._llm.generate = AsyncMock(return_value=MagicMock(content="Answer.", success=True))
    orch.graph = MagicMock()
    orch.graph.all_entity_ids = MagicMock(return_value=[])
    orch.graph.get_entity = MagicMock(return_value=None)
    orch.graph.get_neighbors = MagicMock(return_value=set())
    orch.graph.subgraph_around = MagicMock(return_value=set())
    orch.agent_manager = MagicMock()
    orch.agent_manager.get_active = MagicMock(return_value=[])
    orch.agent_manager.get_meta_agents = MagicMock(return_value=[])
    orch.agent_manager.agents = []
    return orch


@pytest.mark.asyncio
async def test_query_engine_flat_no_agents(mock_orch):
    engine = QueryEngine(orch=mock_orch)
    result = await engine.ask("test question", mode="flat")
    assert isinstance(result, QueryResult)
    assert "No agents" in result.answer


@pytest.mark.asyncio
async def test_query_engine_auto_falls_to_flat(mock_orch):
    """When no meta-agents exist, auto mode falls back to flat."""
    engine = QueryEngine(orch=mock_orch)
    result = await engine.ask("test question", mode="auto")
    assert isinstance(result, QueryResult)
