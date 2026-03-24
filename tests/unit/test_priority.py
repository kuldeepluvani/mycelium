"""Tests for priority scorer."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

import pytest

from mycelium.shared.models import ChangeSet
from mycelium.orchestrator.priority import PriorityScorer


@pytest.fixture
def scorer():
    return PriorityScorer()


def _make_cs(source: str, change_type: str, hours_ago: float = 0) -> ChangeSet:
    ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return ChangeSet(source=source, path=f"/{source}/test.md", change_type=change_type, timestamp=ts)


def test_score_new_vault_doc(scorer):
    new_vault = _make_cs("vault", "created", hours_ago=0.5)
    old_git = _make_cs("git", "modified", hours_ago=200)
    assert scorer.score(new_vault) > scorer.score(old_git)


def test_allocate_budget(scorer):
    alloc = scorer.allocate_budget(50)
    assert alloc["changed"] == 30
    assert alloc["stale"] == 12
    assert alloc["crosslink"] == 8


def test_rank_orders_by_score(scorer):
    cs1 = _make_cs("vault", "created", hours_ago=0.5)
    cs2 = _make_cs("git", "modified", hours_ago=100)
    cs3 = _make_cs("confluence", "modified", hours_ago=500)
    ranked = scorer.rank([cs3, cs1, cs2])
    scores = [item.score for item in ranked]
    assert scores == sorted(scores, reverse=True)
    # vault/created/recent should be first
    assert ranked[0].changeset.source == "vault"
