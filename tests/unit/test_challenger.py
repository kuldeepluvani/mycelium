"""Tests for Layer 3: Adversarial challenge."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mycelium.shared.models import Document
from mycelium.perception.structural import StructuralResult, StructuralEntity
from mycelium.perception.extractor import ExtractionResult
from mycelium.perception.challenger import AdversarialChallenger, ChallengeResult


def _make_doc(content: str = "Some document content.") -> Document:
    return Document(
        id="test-doc",
        source="test",
        path="/test/doc.md",
        content=content,
        content_hash="abc123",
    )


def _make_anchors(ratio: float = 0.5) -> StructuralResult:
    return StructuralResult(entities=[], anchors={}, anchor_ratio=ratio)


def _make_extraction(entities: list[dict] | None = None) -> ExtractionResult:
    return ExtractionResult(
        entities=entities or [{"name": "TestEntity", "entity_class": "service", "description": "A test"}],
        relationships=[],
        claims=[],
        call_cost=1,
    )


def _mock_llm(return_value: dict | None) -> MagicMock:
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value=return_value)
    return llm


@pytest.mark.asyncio
async def test_skip_first_cycle():
    llm = _mock_llm(None)
    challenger = AdversarialChallenger(llm)

    doc = _make_doc()
    anchors = _make_anchors(ratio=0.3)
    extraction = _make_extraction()

    result = await challenger.challenge(doc, extraction, anchors, is_first_cycle=True)

    assert result.skipped is True
    assert result.skip_reason == "first_cycle"
    assert result.call_cost == 0
    assert len(result.entity_verdicts) == 1
    assert result.entity_verdicts[0].verdict == "CONFIRMED"
    # LLM should NOT have been called
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_skip_high_anchor_ratio():
    llm = _mock_llm(None)
    challenger = AdversarialChallenger(llm)

    doc = _make_doc()
    anchors = _make_anchors(ratio=0.9)
    extraction = _make_extraction()

    result = await challenger.challenge(doc, extraction, anchors, is_first_cycle=False)

    assert result.skipped is True
    assert result.skip_reason == "high_anchor_ratio"
    assert result.call_cost == 0
    llm.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_challenge_runs_when_not_skipped():
    llm_response = {
        "entity_verdicts": [
            {"name": "TestEntity", "verdict": "CONFIRMED", "reason": "clearly stated"},
        ],
        "relationship_verdicts": [
            {"source": "A", "target": "B", "verdict": "UNCERTAIN", "reason": "implied only"},
        ],
    }
    llm = _mock_llm(llm_response)
    challenger = AdversarialChallenger(llm)

    doc = _make_doc()
    anchors = _make_anchors(ratio=0.3)
    extraction = _make_extraction()

    result = await challenger.challenge(doc, extraction, anchors, is_first_cycle=False)

    assert result.skipped is False
    assert result.call_cost == 1
    assert len(result.entity_verdicts) == 1
    assert result.entity_verdicts[0].verdict == "CONFIRMED"
    assert len(result.relationship_verdicts) == 1
    assert result.relationship_verdicts[0].verdict == "UNCERTAIN"
    llm.generate_json.assert_called_once()


@pytest.mark.asyncio
async def test_challenge_handles_llm_failure():
    llm = _mock_llm(None)
    challenger = AdversarialChallenger(llm)

    doc = _make_doc()
    anchors = _make_anchors(ratio=0.3)
    extraction = _make_extraction()

    result = await challenger.challenge(doc, extraction, anchors, is_first_cycle=False)

    assert result.entity_verdicts == []
    assert result.relationship_verdicts == []
    assert result.call_cost == 1
