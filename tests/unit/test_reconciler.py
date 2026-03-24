import pytest
from unittest.mock import AsyncMock
from mycelium.shared.llm import ClaudeCLI
from mycelium.perception.extractor import ExtractionResult
from mycelium.perception.challenger import ChallengeResult, ChallengeVerdict
from mycelium.perception.consistency import ConsistencyResult, ConsistencyIssue
from mycelium.perception.reconciler import Reconciler, ReconcileResult


@pytest.fixture
def mock_llm():
    return AsyncMock(spec=ClaudeCLI)


@pytest.fixture
def reconciler(mock_llm):
    return Reconciler(llm=mock_llm)


def _extraction(*names):
    return ExtractionResult(
        entities=[{"name": n, "entity_class": "tech"} for n in names],
        relationships=[],
    )


def _clean_challenge(*names):
    """All entities confirmed, not skipped."""
    return ChallengeResult(
        entity_verdicts=[ChallengeVerdict(name=n, verdict="CONFIRMED", reason="ok") for n in names],
        call_cost=1,
        skipped=False,
    )


def _skipped_challenge(*names):
    """Challenge was skipped — all auto-confirmed."""
    return ChallengeResult(
        entity_verdicts=[ChallengeVerdict(name=n, verdict="CONFIRMED", reason="skip: first_cycle") for n in names],
        call_cost=0,
        skipped=True,
    )


def _challenge_with_rejections(confirmed, rejected):
    verdicts = [ChallengeVerdict(name=n, verdict="CONFIRMED", reason="ok") for n in confirmed]
    verdicts += [ChallengeVerdict(name=n, verdict="REJECT", reason="not supported") for n in rejected]
    return ChallengeResult(entity_verdicts=verdicts, call_cost=1, skipped=False)


def _clean_consistency():
    return ConsistencyResult(issues=[], is_clean=True)


def _consistency_with_issues():
    return ConsistencyResult(
        issues=[ConsistencyIssue(issue_type="degree_anomaly", entity_name="(doc)", description="too many", severity="critical")],
        is_clean=False,
    )


@pytest.mark.asyncio
async def test_no_conflicts_skips(reconciler):
    extraction = _extraction("Alpha", "Beta")
    challenge = _skipped_challenge("Alpha", "Beta")
    consistency = _clean_consistency()

    result = await reconciler.reconcile(extraction, challenge, consistency)
    assert result.skipped is True
    assert "Alpha" in result.accepted_entities
    assert "Beta" in result.accepted_entities
    assert result.quarantined_entities == []
    assert result.rejected_entities == []


def test_needs_reconciliation_with_rejections(reconciler):
    challenge = _challenge_with_rejections(["Alpha"], ["Beta"])
    consistency = _clean_consistency()
    assert reconciler.needs_reconciliation(challenge, consistency) is True


def test_needs_reconciliation_skipped_challenge(reconciler):
    challenge = _skipped_challenge("Alpha")
    consistency = _clean_consistency()
    assert reconciler.needs_reconciliation(challenge, consistency) is False


def test_needs_reconciliation_with_consistency_issues(reconciler):
    challenge = _clean_challenge("Alpha")
    consistency = _consistency_with_issues()
    assert reconciler.needs_reconciliation(challenge, consistency) is True


@pytest.mark.asyncio
async def test_reconcile_with_conflicts(reconciler, mock_llm):
    mock_llm.generate_json.return_value = {
        "verdicts": [
            {"name": "Beta", "verdict": "ACCEPT", "reason": "valid", "confidence": 0.9},
            {"name": "Gamma", "verdict": "REJECT", "reason": "hallucinated", "confidence": 0.8},
            {"name": "Delta", "verdict": "QUARANTINE", "reason": "ambiguous", "confidence": 0.5},
        ]
    }

    extraction = _extraction("Alpha", "Beta", "Gamma", "Delta")
    challenge = _challenge_with_rejections(["Alpha"], ["Beta", "Gamma", "Delta"])
    consistency = _clean_consistency()

    result = await reconciler.reconcile(extraction, challenge, consistency)
    assert result.skipped is False
    assert "Beta" in result.accepted_entities
    assert "Gamma" in result.rejected_entities
    assert "Delta" in result.quarantined_entities
    assert result.call_cost == 1
    assert len(result.verdicts) == 3


@pytest.mark.asyncio
async def test_reconcile_llm_failure_quarantines(reconciler, mock_llm):
    mock_llm.generate_json.return_value = None

    extraction = _extraction("Alpha", "Beta", "Gamma")
    challenge = _challenge_with_rejections(["Alpha"], ["Beta", "Gamma"])
    consistency = _clean_consistency()

    result = await reconciler.reconcile(extraction, challenge, consistency)
    assert "Beta" in result.quarantined_entities
    assert "Gamma" in result.quarantined_entities
    assert "Alpha" in result.accepted_entities
    assert result.call_cost == 1
