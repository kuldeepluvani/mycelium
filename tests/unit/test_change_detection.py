"""Tests for content-hash-based change detection."""
from __future__ import annotations

import hashlib
import pytest
from pathlib import Path

from mycelium.brainstem.store import BrainstemStore
from mycelium.connectors.vault import VaultConnector


@pytest.fixture
def store(tmp_path):
    s = BrainstemStore(tmp_path / "brainstem.db")
    s.initialize()
    return s


def test_save_and_get_document_hash(store):
    """Store round-trips content hash for a path."""
    store.save_document_hash("/vault/test.md", "abc123")
    assert store.get_document_hash("/vault/test.md") == "abc123"


def test_get_missing_hash_returns_none(store):
    assert store.get_document_hash("/nonexistent") is None


def test_hash_update_overwrites(store):
    """Updating hash for same path replaces the old value."""
    store.save_document_hash("/vault/test.md", "abc123")
    store.save_document_hash("/vault/test.md", "def456")
    assert store.get_document_hash("/vault/test.md") == "def456"


@pytest.mark.asyncio
async def test_vault_connector_skips_unchanged_files(tmp_path, store):
    """Files whose content hasn't changed should be filtered out."""
    vault = tmp_path / "vault"
    vault.mkdir()
    f = vault / "test.md"
    f.write_text("# Hello\nContent here.")

    connector = VaultConnector(vault_path=str(vault))
    changes = await connector.discover_changes()
    assert len(changes) == 1

    # Save the hash (simulating post-learn)
    content_hash = hashlib.sha256(f.read_bytes()).hexdigest()
    store.save_document_hash(str(f), content_hash)

    # Now discover again with known hashes
    changes = await connector.discover_changes(known_hashes=store)
    assert len(changes) == 0


@pytest.mark.asyncio
async def test_vault_connector_detects_content_change(tmp_path, store):
    """Files whose content changed should be returned."""
    vault = tmp_path / "vault"
    vault.mkdir()
    f = vault / "test.md"
    f.write_text("# Hello\nVersion 1.")

    connector = VaultConnector(vault_path=str(vault))

    # Save old hash
    store.save_document_hash(str(f), "old_hash_that_wont_match")

    changes = await connector.discover_changes(known_hashes=store)
    assert len(changes) == 1
    assert changes[0].change_type == "modified"
