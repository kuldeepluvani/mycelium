"""Tests for Layer 2: LLM deep extraction."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.shared.models import Document
from mycelium.perception.structural import StructuralResult, StructuralEntity
from mycelium.perception.extractor import DeepExtractor, ExtractionResult


def _make_doc(content: str = "Some document content.") -> Document:
    return Document(
        id="test-doc",
        source="test",
        path="/test/doc.md",
        content=content,
        content_hash="abc123",
    )


def _make_anchors(anchors: dict[str, str] | None = None, ratio: float = 0.5) -> StructuralResult:
    anchors = anchors or {}
    entities = [StructuralEntity(name=n, entity_class=c, source="test") for n, c in anchors.items()]
    return StructuralResult(entities=entities, anchors=anchors, anchor_ratio=ratio)


def _mock_llm(return_value: dict | None) -> MagicMock:
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=return_value)
    return llm


@pytest.mark.asyncio
async def test_extract_returns_entities():
    llm_response = {
        "entities": [
            {"name": "GKE", "entity_class": "technology", "description": "Google Kubernetes Engine"},
            {"name": "zauthz", "entity_class": "service", "description": "Auth service"},
        ],
        "relationships": [
            {"source": "zauthz", "target": "GKE", "rel_type": "deployed_on", "rel_category": "structural"},
        ],
        "claims": [
            {"statement": "zauthz runs on GKE", "confidence": 0.9},
        ],
    }
    llm = _mock_llm(llm_response)
    extractor = DeepExtractor(llm)

    doc = _make_doc()
    anchors = _make_anchors({"existing-svc": "service"})
    result = await extractor.extract(doc, anchors)

    assert len(result.entities) == 2
    assert result.entities[0]["name"] == "GKE"
    assert len(result.relationships) == 1
    assert len(result.claims) == 1
    assert result.call_cost == 1


@pytest.mark.asyncio
async def test_extract_handles_llm_failure():
    llm = _mock_llm(None)
    extractor = DeepExtractor(llm)

    doc = _make_doc()
    anchors = _make_anchors()
    result = await extractor.extract(doc, anchors)

    assert result.entities == []
    assert result.relationships == []
    assert result.claims == []
    assert result.call_cost == 1


@pytest.mark.asyncio
async def test_extract_includes_anchors_in_prompt():
    llm = _mock_llm({"entities": [], "relationships": [], "claims": []})
    extractor = DeepExtractor(llm)

    doc = _make_doc()
    anchors = _make_anchors({"my-service": "service", "my-team": "team"})
    await extractor.extract(doc, anchors)

    # Verify the prompt sent to LLM contains anchor text
    call_args = llm.generate_json.call_args
    prompt = call_args[0][0]
    assert "my-service (service)" in prompt
    assert "my-team (team)" in prompt
