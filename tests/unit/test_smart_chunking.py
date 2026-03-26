"""Tests for smart document chunking in extraction."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from mycelium.shared.models import Document
from mycelium.perception.extractor import DeepExtractor


def _make_large_doc(num_sections: int = 10) -> Document:
    """Create a document larger than chunk_size with distinct entities per section."""
    sections = []
    for i in range(num_sections):
        sections.append(f"## Section {i}\n\nService{i} depends on Database{i} for storage. "
                       f"It uses Cache{i} for caching and Queue{i} for messaging.\n")
    content = "# Large Architecture Doc\n\n" + "\n".join(sections)
    return Document(id="large-doc", source="vault", path="/test/large.md",
                   content=content, content_hash="abc", metadata={})


@pytest.mark.asyncio
async def test_large_document_makes_multiple_calls():
    """Documents larger than chunk_size should trigger multiple LLM calls."""
    llm = MagicMock()
    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "entities": [{"name": f"Entity_chunk{call_count}", "entity_class": "service",
                         "description": f"from chunk {call_count}"}],
            "relationships": [],
            "claims": [],
        }

    llm.generate_json = AsyncMock(side_effect=mock_generate)
    extractor = DeepExtractor(llm, chunk_size=500, chunk_overlap=50)
    doc = _make_large_doc(10)
    result = await extractor.extract(doc, structural_result=None)

    assert call_count > 1
    assert len(result.entities) > 1


@pytest.mark.asyncio
async def test_small_document_single_call():
    """Small documents should use a single LLM call."""
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={
        "entities": [{"name": "SmallEntity", "entity_class": "service", "description": "test"}],
        "relationships": [], "claims": [],
    })

    extractor = DeepExtractor(llm, chunk_size=5000)
    doc = Document(id="small", source="vault", path="/test/small.md",
                  content="# Small\nJust a tiny doc.", content_hash="x")
    result = await extractor.extract(doc, structural_result=None)

    assert llm.generate_json.call_count == 1
    assert len(result.entities) == 1


@pytest.mark.asyncio
async def test_chunking_deduplicates_entities():
    """Entities extracted from overlapping chunks should be deduplicated by name."""
    llm = MagicMock()

    async def mock_generate(*args, **kwargs):
        return {
            "entities": [
                {"name": "SharedEntity", "entity_class": "service", "description": "appears in overlap"},
                {"name": f"Unique_{id(args)}", "entity_class": "service", "description": "unique"},
            ],
            "relationships": [], "claims": [],
        }

    llm.generate_json = AsyncMock(side_effect=mock_generate)
    extractor = DeepExtractor(llm, chunk_size=100, chunk_overlap=20)
    doc = Document(id="overlap", source="vault", path="/test/overlap.md",
                  content="x " * 200, content_hash="x")
    result = await extractor.extract(doc, structural_result=None)

    # SharedEntity should appear only once despite being in multiple chunks
    shared_count = sum(1 for e in result.entities if e.get("name") == "SharedEntity")
    assert shared_count == 1


@pytest.mark.asyncio
async def test_chunk_cost_tracked():
    """Total call_cost should count all chunk calls."""
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={
        "entities": [{"name": "E", "entity_class": "x", "description": "y"}],
        "relationships": [], "claims": [],
    })

    extractor = DeepExtractor(llm, chunk_size=100, chunk_overlap=10)
    doc = Document(id="multi", source="vault", path="/test/multi.md",
                  content="word " * 100, content_hash="x")
    result = await extractor.extract(doc, structural_result=None)

    assert result.call_cost == llm.generate_json.call_count
