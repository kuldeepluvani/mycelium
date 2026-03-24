"""Tests for quota tracker."""
from __future__ import annotations

import pytest

from mycelium.orchestrator.quota import QuotaTracker


def test_initial_state():
    qt = QuotaTracker(budget=50)
    assert qt.budget == 50
    assert qt.spent == 0
    assert qt.remaining == 50
    assert qt.exhausted is False


def test_spend_tracks():
    qt = QuotaTracker(budget=50)
    qt.spend("extract", "vault_connector")
    qt.spend("extract", "git_connector")
    qt.spend("merge", "graph")
    assert qt.spent == 3
    assert qt.remaining == 47
    assert len(qt.calls) == 3


def test_can_spend():
    qt = QuotaTracker(budget=2)
    qt.spend("extract", "mod_a")
    qt.spend("extract", "mod_b")
    assert qt.can_spend(1) is False
    assert qt.remaining == 0


def test_exhausted():
    qt = QuotaTracker(budget=3)
    for i in range(3):
        qt.spend("extract", f"mod_{i}")
    assert qt.exhausted is True
    assert qt.remaining == 0


def test_summary():
    qt = QuotaTracker(budget=10)
    qt.spend("extract", "mod_a")
    qt.spend("merge", "mod_b")
    s = qt.summary()
    assert s == {
        "budget": 10,
        "spent": 2,
        "remaining": 8,
        "exhausted": False,
        "calls": 2,
    }
