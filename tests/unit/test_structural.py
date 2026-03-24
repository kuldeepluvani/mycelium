"""Tests for Layer 1: Structural pre-parse."""
from __future__ import annotations

import pytest
from mycelium.shared.models import Document
from mycelium.perception.structural import StructuralParser, StructuralResult


def _make_doc(content: str = "", metadata: dict | None = None) -> Document:
    return Document(
        id="test-doc",
        source="test",
        path="/test/doc.md",
        content=content,
        content_hash="abc123",
        metadata=metadata or {},
    )


@pytest.fixture
def parser() -> StructuralParser:
    return StructuralParser()


def test_extracts_wikilinks(parser: StructuralParser):
    doc = _make_doc("Check [[service-a]] and [[service-b|alias]].")
    result = parser.parse(doc)
    wikilink_entities = [e for e in result.entities if e.source == "wikilink"]
    assert len(wikilink_entities) == 2
    names = {e.name for e in wikilink_entities}
    assert "service-a" in names
    assert "service-b" in names
    assert all(e.entity_class == "reference" for e in wikilink_entities)


def test_extracts_headers(parser: StructuralParser):
    doc = _make_doc("# Title\n\nSome text\n\n## Subtitle")
    result = parser.parse(doc)
    header_entities = [e for e in result.entities if e.source == "header"]
    assert len(header_entities) == 2
    names = [e.name for e in header_entities]
    assert "Title" in names
    assert "Subtitle" in names
    assert all(e.entity_class == "topic" for e in header_entities)


def test_extracts_frontmatter_repo(parser: StructuralParser):
    doc = _make_doc("Some content", metadata={"repo": "zauthz"})
    result = parser.parse(doc)
    service_entities = [e for e in result.entities if e.entity_class == "service"]
    assert len(service_entities) == 1
    assert service_entities[0].name == "zauthz"
    assert service_entities[0].source == "frontmatter"


def test_extracts_dates(parser: StructuralParser):
    doc = _make_doc("Created on 2026-03-23 and updated 2026-03-24.")
    result = parser.parse(doc)
    date_entities = [e for e in result.entities if e.source == "date"]
    assert len(date_entities) == 2
    names = {e.name for e in date_entities}
    assert "2026-03-23" in names
    assert "2026-03-24" in names
    assert all(e.entity_class == "date" for e in date_entities)


def test_extracts_inline_code(parser: StructuralParser):
    doc = _make_doc("Use `kubectl` to deploy.")
    result = parser.parse(doc)
    code_entities = [e for e in result.entities if e.source == "code"]
    assert len(code_entities) == 1
    assert code_entities[0].name == "kubectl"
    assert code_entities[0].entity_class == "code_ref"


def test_anchor_ratio(parser: StructuralParser):
    # 200 chars of content -> expected ~1 entity. 3 entities -> ratio = min(1.0, 3/1) = 1.0
    doc = _make_doc("x" * 200, metadata={"repo": "svc", "team": "eng", "tags": ["infra"]})
    result = parser.parse(doc)
    assert result.anchor_ratio == 1.0

    # 1000 chars -> expected ~5. 1 entity -> ratio = 1/5 = 0.2
    doc2 = _make_doc("x" * 1000, metadata={"repo": "svc"})
    result2 = parser.parse(doc2)
    assert result2.anchor_ratio == pytest.approx(0.2)


def test_empty_document(parser: StructuralParser):
    doc = _make_doc("")
    result = parser.parse(doc)
    assert result.entities == []
    assert result.anchors == {}
    assert result.anchor_ratio == 0.0
