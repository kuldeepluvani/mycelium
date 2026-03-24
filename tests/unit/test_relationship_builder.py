"""Tests for relationship builder — batched extraction with rationale."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.perception.relationship_builder import RelationshipBuilder, BatchRelationshipResult


def _make_llm(return_value):
    """Create a mock ClaudeCLI with generate_json returning the given value."""
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=return_value)
    return llm


@pytest.mark.asyncio
async def test_build_batch_returns_relationships():
    llm = _make_llm({
        "relationships": [
            {
                "source": "Kubernetes",
                "target": "Docker",
                "rel_type": "depends_on",
                "rel_category": "structural",
                "rationale": "K8s uses Docker as container runtime",
                "confidence": 0.9,
            },
            {
                "source": "Terraform",
                "target": "AWS",
                "rel_type": "manages",
                "rel_category": "structural",
                "rationale": "Terraform provisions AWS resources",
                "confidence": 0.85,
            },
        ]
    })

    builder = RelationshipBuilder(llm=llm)
    result = await builder.build_batch(
        [("Kubernetes", "Docker"), ("Terraform", "AWS")],
        document_id="doc-1",
    )

    assert len(result.relationships) == 2
    assert result.call_cost == 1
    assert result.relationships[0].rel_type == "depends_on"
    assert result.relationships[1].rel_type == "manages"
    # Evidence should reference the document
    assert len(result.relationships[0].evidence) == 1
    assert result.relationships[0].evidence[0].document_id == "doc-1"


@pytest.mark.asyncio
async def test_build_empty_pairs():
    llm = _make_llm(None)
    builder = RelationshipBuilder(llm=llm)
    result = await builder.build_batch([])
    assert result.relationships == []
    assert result.call_cost == 0
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_batching():
    llm = _make_llm({"relationships": []})
    builder = RelationshipBuilder(llm=llm, batch_size=15)

    # 20 pairs → should produce 2 LLM calls (15 + 5)
    pairs = [(f"entity_{i}", f"entity_{i+1}") for i in range(20)]
    result = await builder.build_batch(pairs)

    assert result.call_cost == 2
    assert llm.generate_json.call_count == 2


@pytest.mark.asyncio
async def test_llm_failure_continues():
    llm = _make_llm(None)  # LLM returns None (failure)
    builder = RelationshipBuilder(llm=llm)
    result = await builder.build_batch([("A", "B")])
    assert result.relationships == []
    assert result.call_cost == 1
