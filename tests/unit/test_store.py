"""Tests for BrainstemStore — SQLite schema, pragmas, and entity/relationship CRUD."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mycelium.brainstem.store import BrainstemStore
from mycelium.shared.models import Entity, Relationship


@pytest.fixture()
def store(tmp_path: Path) -> BrainstemStore:
    s = BrainstemStore(db_path=tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


# ── schema & pragmas ─────────────────────────────────────────────────────

EXPECTED_TABLES = {
    "agents",
    "agent_nodes",
    "concepts",
    "document_chunks",
    "documents",
    "entities",
    "feedback_queue",
    "relationships",
    "schema_version",
    "staging_entities",
}


def test_initialize_creates_tables(store: BrainstemStore) -> None:
    tables = set(store.list_tables())
    assert EXPECTED_TABLES.issubset(tables), f"Missing: {EXPECTED_TABLES - tables}"


def test_foreign_keys_enabled(store: BrainstemStore) -> None:
    row = store.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_wal_mode_enabled(store: BrainstemStore) -> None:
    row = store.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"


def test_schema_version_set(store: BrainstemStore) -> None:
    row = store.execute("SELECT MAX(version) FROM schema_version").fetchone()
    assert row[0] == 1


# ── entity CRUD ──────────────────────────────────────────────────────────

def _make_entity(**overrides) -> Entity:
    defaults = dict(
        id="ent-001",
        name="Python",
        canonical_name="python",
        entity_class="language",
        entity_subclass="programming",
        domain="tech",
        aliases=["py", "cpython"],
        description="A programming language",
        properties={"typed": False},
        provenance=["doc-1"],
        confidence=0.85,
    )
    defaults.update(overrides)
    return Entity(**defaults)


def test_insert_and_get_entity(store: BrainstemStore) -> None:
    entity = _make_entity()
    store.upsert_entity(entity)

    loaded = store.get_entity("ent-001")
    assert loaded is not None
    assert loaded.id == entity.id
    assert loaded.name == "Python"
    assert loaded.canonical_name == "python"
    assert loaded.entity_class == "language"
    assert loaded.entity_subclass == "programming"
    assert loaded.domain == "tech"
    assert loaded.aliases == ["py", "cpython"]
    assert loaded.description == "A programming language"
    assert loaded.properties == {"typed": False}
    assert loaded.provenance == ["doc-1"]
    assert loaded.confidence == pytest.approx(0.85)
    assert loaded.version == 1
    assert loaded.quarantined is False
    assert loaded.archived is False


# ── relationship CRUD ────────────────────────────────────────────────────

def test_insert_and_get_relationship(store: BrainstemStore) -> None:
    e1 = _make_entity(id="ent-src", name="FastAPI", canonical_name="fastapi")
    e2 = _make_entity(id="ent-tgt", name="Uvicorn", canonical_name="uvicorn")
    store.upsert_entity(e1)
    store.upsert_entity(e2)

    rel = Relationship(
        id="rel-001",
        source_id="ent-src",
        target_id="ent-tgt",
        rel_type="depends_on",
        rel_category="structural",
        rationale="FastAPI runs on Uvicorn",
        confidence=0.9,
        strength=0.8,
        bidirectional=False,
    )
    store.upsert_relationship(rel)

    loaded = store.get_relationship("rel-001")
    assert loaded is not None
    assert loaded.id == "rel-001"
    assert loaded.source_id == "ent-src"
    assert loaded.target_id == "ent-tgt"
    assert loaded.rel_type == "depends_on"
    assert loaded.rel_category == "structural"
    assert loaded.rationale == "FastAPI runs on Uvicorn"
    assert loaded.confidence == pytest.approx(0.9)
    assert loaded.strength == pytest.approx(0.8)
    assert loaded.bidirectional is False
    assert loaded.version == 1
    assert loaded.quarantined is False
    assert loaded.archived is False
