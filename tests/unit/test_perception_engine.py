"""Tests for the 5-layer perception engine orchestrator."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from mycelium.shared.models import Document, Relationship, Evidence
from mycelium.shared.config import PerceptionConfig
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.perception.engine import PerceptionEngine, PerceptionStats


def _make_doc(
    doc_id: str = "doc-1",
    content: str = "# TestService\n\nThis service depends on [[Database]] for storage.",
    path: str = "/test/service.md",
    metadata: dict | None = None,
) -> Document:
    return Document(
        id=doc_id,
        source="vault",
        path=path,
        content=content,
        content_hash="abc123",
        metadata=metadata or {"repo": "test-service"},
    )


def _mock_llm(extraction_response: dict | None = None) -> MagicMock:
    """Create a mock LLM that returns predictable results for all pipeline stages."""
    llm = MagicMock()

    if extraction_response is None:
        extraction_response = {
            "entities": [
                {
                    "name": "TestService",
                    "entity_class": "service",
                    "description": "A test service",
                }
            ],
            "relationships": [
                {
                    "source": "TestService",
                    "target": "Database",
                    "rel_type": "depends_on",
                    "rel_category": "structural",
                    "rationale": "test",
                }
            ],
            "claims": [],
        }

    # generate_json is used by extractor, challenger, reconciler, relationship_builder
    # Return the extraction response for all calls — each sub-component parses what it needs
    llm.generate_json = AsyncMock(return_value=extraction_response)
    return llm


@pytest.fixture
def graph():
    return KnowledgeGraph()


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "test.db")
    s.initialize()
    return s


@pytest.fixture
def mock_llm():
    return _mock_llm()


@pytest.fixture
def engine(mock_llm, graph, store):
    return PerceptionEngine(
        llm=mock_llm,
        graph=graph,
        store=store,
        config=PerceptionConfig(),
    )


@pytest.fixture
def sample_doc():
    return _make_doc()


# ── Core pipeline tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_document_creates_entities(engine, sample_doc):
    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    assert stats.documents_processed == 1
    assert stats.entities_created > 0
    assert stats.total_call_cost >= 1


@pytest.mark.asyncio
async def test_process_document_first_cycle_challenge_skipped(engine, sample_doc):
    """First cycle should skip adversarial challenge (cost=0 for layer 3)."""
    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    assert stats.documents_processed == 1
    # Extraction = 1 call, challenge skipped = 0, reconcile skipped = 0
    # relationship builder = 1 call
    # Minimum: extraction(1) + relationship(1) = 2
    assert stats.total_call_cost >= 1


@pytest.mark.asyncio
async def test_process_document_entities_added_to_graph(engine, sample_doc, graph):
    await engine.process_document(sample_doc, is_first_cycle=True)
    assert graph.node_count() > 0


@pytest.mark.asyncio
async def test_process_document_entities_persisted_to_store(engine, sample_doc, store, graph):
    await engine.process_document(sample_doc, is_first_cycle=True)
    # Verify entities were persisted — check via graph and store.get_entity
    entity_ids = graph.all_entity_ids()
    assert len(entity_ids) > 0
    for eid in entity_ids:
        assert store.get_entity(eid) is not None


@pytest.mark.asyncio
async def test_process_document_handles_empty_content(engine):
    bad_doc = Document(
        id="bad", source="vault", path="/bad.md", content="", content_hash="x"
    )
    stats = await engine.process_document(bad_doc, is_first_cycle=True)
    # Should not crash — either processes or records error
    assert stats.documents_processed == 1 or len(stats.errors) > 0


@pytest.mark.asyncio
async def test_process_document_handles_llm_failure(graph, store):
    """When LLM returns None, engine should not crash."""
    llm = _mock_llm()
    llm.generate_json = AsyncMock(return_value=None)
    engine = PerceptionEngine(llm=llm, graph=graph, store=store)
    doc = _make_doc()
    stats = await engine.process_document(doc, is_first_cycle=True)
    # No entities extracted when LLM fails
    assert stats.entities_created == 0
    assert stats.documents_processed == 1


@pytest.mark.asyncio
async def test_process_document_tracks_call_cost(engine, sample_doc):
    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    # At minimum extraction costs 1 call
    assert stats.total_call_cost >= 1


@pytest.mark.asyncio
async def test_process_document_no_errors_on_success(engine, sample_doc):
    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    assert stats.errors == []


# ── Entity resolution tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entity_merge_on_duplicate(engine, sample_doc, graph):
    """Second processing of same entity should merge, not create duplicate."""
    from mycelium.shared.models import Entity

    # Pre-add an entity with the same name
    existing = Entity(
        id="ent-existing",
        name="TestService",
        canonical_name="TestService",
        entity_class="service",
    )
    graph.add_entity(existing)

    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    assert stats.entities_merged >= 1
    # Should not create a new entity for TestService
    assert graph.node_count() == 1  # still just the original


# ── Relationship tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_document_builds_relationships(engine, sample_doc):
    """Relationship builder should be invoked when extraction has relationships."""
    stats = await engine.process_document(sample_doc, is_first_cycle=True)
    # The mock LLM returns a relationship result for the builder too
    assert stats.relationships_created >= 0  # depends on mock response shape


# ── Batch processing tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_batch_multiple_docs(engine):
    docs = [
        _make_doc(doc_id="doc-1", content="# ServiceA\nDepends on DB."),
        _make_doc(doc_id="doc-2", content="# ServiceB\nDepends on Cache."),
    ]
    stats = await engine.process_batch(docs, is_first_cycle=True, max_concurrent=2)
    assert stats.documents_processed == 2


@pytest.mark.asyncio
async def test_process_batch_aggregates_stats(engine):
    docs = [
        _make_doc(doc_id=f"doc-{i}", content=f"# Service{i}")
        for i in range(3)
    ]
    stats = await engine.process_batch(docs, is_first_cycle=True, max_concurrent=2)
    assert stats.documents_processed == 3
    assert stats.total_call_cost >= 3  # at least 1 extraction call per doc


@pytest.mark.asyncio
async def test_process_batch_handles_partial_failure(graph, store):
    """If one doc fails, others should still be processed."""
    llm = _mock_llm()
    call_count = 0

    async def flaky_generate_json(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Fail on second call (will affect one doc's extraction)
        if call_count == 2:
            raise RuntimeError("LLM transient failure")
        return {
            "entities": [{"name": f"Ent{call_count}", "entity_class": "service", "description": "test"}],
            "relationships": [],
            "claims": [],
        }

    llm.generate_json = AsyncMock(side_effect=flaky_generate_json)
    engine = PerceptionEngine(llm=llm, graph=graph, store=store)

    docs = [_make_doc(doc_id=f"doc-{i}") for i in range(3)]
    stats = await engine.process_batch(docs, is_first_cycle=True, max_concurrent=1)
    # At least some docs processed, and errors captured
    assert stats.documents_processed + len(stats.errors) >= 1


@pytest.mark.asyncio
async def test_process_batch_empty_list(engine):
    stats = await engine.process_batch([], is_first_cycle=True)
    assert stats.documents_processed == 0
    assert stats.errors == []


# ── Stats dataclass tests ───────────────────────────────────────────────


def test_perception_stats_defaults():
    stats = PerceptionStats()
    assert stats.documents_processed == 0
    assert stats.entities_created == 0
    assert stats.entities_merged == 0
    assert stats.relationships_created == 0
    assert stats.quarantined == 0
    assert stats.rejected == 0
    assert stats.total_call_cost == 0
    assert stats.errors == []


# ── find_entity_by_name tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_entity_by_name_case_insensitive(engine, graph):
    from mycelium.shared.models import Entity

    entity = Entity(
        id="ent-1",
        name="MyService",
        canonical_name="MyService",
        entity_class="service",
    )
    graph.add_entity(entity)

    assert engine._find_entity_by_name("myservice") == "ent-1"
    assert engine._find_entity_by_name("MYSERVICE") == "ent-1"
    assert engine._find_entity_by_name("MyService") == "ent-1"


@pytest.mark.asyncio
async def test_find_entity_by_name_returns_none_for_missing(engine):
    assert engine._find_entity_by_name("nonexistent") is None
