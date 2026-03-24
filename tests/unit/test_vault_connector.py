"""Tests for VaultConnector."""
from __future__ import annotations

from pathlib import Path

import pytest

from mycelium.connectors.vault import VaultConnector

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_vault"


@pytest.fixture
def vault():
    return VaultConnector(vault_path=str(FIXTURES))


async def test_discover_changes(vault: VaultConnector):
    changes = await vault.discover_changes()
    paths = [c.path for c in changes]
    assert len(changes) == 3
    assert any("service-a.md" in p for p in paths)
    assert any("service-b.md" in p for p in paths)
    assert any("ticket-1.md" in p for p in paths)


async def test_fetch_content_parses_frontmatter(vault: VaultConnector):
    doc = await vault.fetch_content(str(FIXTURES / "service-a.md"))
    assert doc is not None
    assert doc.metadata["repo"] == "service-a"
    assert doc.metadata["team"] == "platform"
    assert "service" in doc.metadata["tags"]


async def test_fetch_content_extracts_wikilinks(vault: VaultConnector):
    doc = await vault.fetch_content(str(FIXTURES / "service-a.md"))
    assert doc is not None
    assert "service-b" in doc.wikilinks
    assert "ticket-1" in doc.wikilinks


async def test_ignore_patterns(tmp_path: Path):
    # Create a small vault with an ignorable file
    (tmp_path / "keep.md").write_text("# Keep\n")
    (tmp_path / "ignore-me.md").write_text("# Ignore\n")
    vc = VaultConnector(
        vault_path=str(tmp_path),
        ignore_patterns=["ignore-*"],
    )
    changes = await vc.discover_changes()
    paths = [c.path for c in changes]
    assert len(changes) == 1
    assert any("keep.md" in p for p in paths)
    assert not any("ignore-me.md" in p for p in paths)
