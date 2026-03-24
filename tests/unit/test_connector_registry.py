"""Tests for ConnectorRegistry."""
from __future__ import annotations

from datetime import datetime

import pytest

from mycelium.connectors.base import BaseConnector
from mycelium.connectors.registry import ConnectorRegistry
from mycelium.shared.models import ChangeSet, Document


class _StubConnector(BaseConnector):
    def __init__(self, name: str) -> None:
        self._name = name

    def source_type(self) -> str:
        return self._name

    async def discover_changes(self, since: datetime | None = None) -> list[ChangeSet]:
        return []

    async def fetch_content(self, path: str) -> Document | None:
        return None


def test_register_and_get():
    reg = ConnectorRegistry()
    c = _StubConnector("vault")
    reg.register(c)
    assert reg.get("vault") is c


def test_duplicate_registration_raises():
    reg = ConnectorRegistry()
    reg.register(_StubConnector("vault"))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_StubConnector("vault"))


def test_all_connectors():
    reg = ConnectorRegistry()
    c1 = _StubConnector("vault")
    c2 = _StubConnector("git")
    reg.register(c1)
    reg.register(c2)
    assert len(reg.all()) == 2
    assert c1 in reg.all()
    assert c2 in reg.all()


def test_source_types():
    reg = ConnectorRegistry()
    reg.register(_StubConnector("vault"))
    reg.register(_StubConnector("git"))
    types = reg.source_types()
    assert "vault" in types
    assert "git" in types
    assert len(types) == 2
