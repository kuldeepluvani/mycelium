"""Tests for confidence propagation from challenger verdicts to entities."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.shared.models import Document, Entity
from mycelium.shared.config import PerceptionConfig
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.perception.engine import PerceptionEngine


def _make_doc(content: str = "# TestService\nDepends on [[Database]].") -> Document:
    return Document(
        id="doc-1", source="vault", path="/test/service.md",
        content=content, content_hash="abc123",
    )


def _mock_llm(entities=None):
    llm = MagicMock()
    if entities is None:
        entities = [{"name": "TestService", "entity_class": "service", "description": "A test service"}]
    llm.generate_json = AsyncMock(return_value={
        "entities": entities,
        "relationships": [],
        "claims": [],
    })
    return llm


@pytest.fixture
def graph():
    return KnowledgeGraph()


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "test.db")
    s.initialize()
    return s


@pytest.mark.asyncio
async def test_first_cycle_entities_get_070_confidence(graph, store):
    """First cycle skips challenge → entities get 0.70 (anchored but unverified)."""
    llm = _mock_llm()
    engine = PerceptionEngine(llm=llm, graph=graph, store=store, config=PerceptionConfig())
    await engine.process_document(_make_doc(), is_first_cycle=True)

    entities = [graph.get_entity(eid) for eid in graph.all_entity_ids()]
    assert len(entities) > 0
    for e in entities:
        assert e.confidence == 0.70


@pytest.mark.asyncio
async def test_confirmed_entity_gets_085_confidence(graph, store):
    """When challenger returns CONFIRMED, entity confidence should be 0.85."""
    llm = _mock_llm()
    call_count = 0

    async def mock_generate_json(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "entities": [{"name": "AlphaService", "entity_class": "service", "description": "test"}],
                "relationships": [], "claims": [],
            }
        elif call_count == 2:
            return {
                "entity_verdicts": [{"name": "AlphaService", "verdict": "CONFIRMED", "reason": "clearly stated"}],
                "relationship_verdicts": [],
            }
        return None

    llm.generate_json = AsyncMock(side_effect=mock_generate_json)
    config = PerceptionConfig(challenge_skip_anchor_ratio=1.1)
    engine = PerceptionEngine(llm=llm, graph=graph, store=store, config=config)
    await engine.process_document(_make_doc(), is_first_cycle=False)

    entities = [graph.get_entity(eid) for eid in graph.all_entity_ids()]
    confirmed = [e for e in entities if e and e.name == "AlphaService"]
    assert len(confirmed) == 1
    assert confirmed[0].confidence == 0.85


@pytest.mark.asyncio
async def test_uncertain_entity_gets_050_confidence(graph, store):
    """When challenger returns UNCERTAIN, entity confidence should be 0.50."""
    llm = _mock_llm()
    call_count = 0

    async def mock_generate_json(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "entities": [{"name": "BetaService", "entity_class": "service", "description": "test"}],
                "relationships": [], "claims": [],
            }
        elif call_count == 2:
            return {
                "entity_verdicts": [{"name": "BetaService", "verdict": "UNCERTAIN", "reason": "not explicit"}],
                "relationship_verdicts": [],
            }
        return None

    llm.generate_json = AsyncMock(side_effect=mock_generate_json)
    config = PerceptionConfig(challenge_skip_anchor_ratio=1.1)
    engine = PerceptionEngine(llm=llm, graph=graph, store=store, config=config)
    await engine.process_document(_make_doc(), is_first_cycle=False)

    entities = [graph.get_entity(eid) for eid in graph.all_entity_ids()]
    uncertain = [e for e in entities if e and e.name == "BetaService"]
    assert len(uncertain) == 1
    assert uncertain[0].confidence == 0.50


@pytest.mark.asyncio
async def test_reconcile_confidence_overrides_challenge(graph, store):
    """When reconciler provides explicit confidence, it overrides challenge verdict."""
    llm = _mock_llm()
    call_count = 0

    async def mock_generate_json(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "entities": [{"name": "GammaService", "entity_class": "service", "description": "test"}],
                "relationships": [], "claims": [],
            }
        elif call_count == 2:
            return {
                "entity_verdicts": [{"name": "GammaService", "verdict": "REJECT", "reason": "hallucinated"}],
                "relationship_verdicts": [],
            }
        elif call_count == 3:
            return {
                "verdicts": [{"name": "GammaService", "verdict": "ACCEPT", "reason": "actually valid", "confidence": 0.75}],
            }
        return None

    llm.generate_json = AsyncMock(side_effect=mock_generate_json)
    config = PerceptionConfig(challenge_skip_anchor_ratio=1.1)
    engine = PerceptionEngine(llm=llm, graph=graph, store=store, config=config)
    await engine.process_document(_make_doc(), is_first_cycle=False)

    entities = [graph.get_entity(eid) for eid in graph.all_entity_ids()]
    gamma = [e for e in entities if e and e.name == "GammaService"]
    assert len(gamma) == 1
    assert gamma[0].confidence == 0.75
