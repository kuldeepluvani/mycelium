"""Tests for mycelium.observe.tui — minimal instantiation tests."""
from __future__ import annotations

import pytest
from mycelium.observe.store import ObservationStore
from mycelium.observe.tui import MyceliumTUI, StatusPanel


@pytest.fixture
def store(tmp_path):
    s = ObservationStore(tmp_path / "test_tui.db")
    yield s
    s.close()


def test_tui_app_creation(store: ObservationStore):
    app = MyceliumTUI(store=store)
    assert app is not None
    assert app._store is store


def test_status_panel_creation(store: ObservationStore):
    panel = StatusPanel(store=store)
    assert panel is not None
    assert panel._store is store
