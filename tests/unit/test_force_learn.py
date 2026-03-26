"""Tests for --force learn flag."""
from __future__ import annotations
import hashlib
import pytest
from mycelium.brainstem.store import BrainstemStore
from mycelium.connectors.vault import VaultConnector


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "brainstem.db")
    s.initialize()
    return s


@pytest.mark.asyncio
async def test_force_bypasses_content_hash(tmp_path, store):
    vault = tmp_path / "vault"
    vault.mkdir()
    f = vault / "test.md"
    f.write_text("# Hello\nContent here.")

    content_hash = hashlib.sha256(f.read_bytes()).hexdigest()
    store.save_document_hash(str(f), content_hash)

    connector = VaultConnector(vault_path=str(vault))

    # Without force: should skip
    changes = await connector.discover_changes(known_hashes=store)
    assert len(changes) == 0

    # With force: should return
    changes = await connector.discover_changes(force=True)
    assert len(changes) == 1


@pytest.mark.asyncio
async def test_discover_without_force_still_works(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "test.md").write_text("# Test")

    connector = VaultConnector(vault_path=str(vault))
    changes = await connector.discover_changes()
    assert len(changes) == 1
