from mycelium.shared.models import (
    ChangeSet,
    Document,
    Entity,
    Evidence,
    Relationship,
    TimeScope,
)


def test_entity_creation():
    entity = Entity(
        id="e1",
        name="Test Entity",
        canonical_name="test_entity",
        entity_class="concept",
    )
    assert entity.confidence == 0.5
    assert entity.version == 1
    assert entity.quarantined is False
    assert entity.archived is False
    assert entity.aliases == []
    assert entity.provenance == []


def test_entity_aliases_and_properties():
    entity = Entity(
        id="e2",
        name="Rich Entity",
        canonical_name="rich_entity",
        entity_class="person",
        aliases=["alias1", "alias2"],
        properties={"role": "engineer", "level": 5},
    )
    assert entity.aliases == ["alias1", "alias2"]
    assert entity.properties == {"role": "engineer", "level": 5}


def test_relationship_creation():
    rel = Relationship(
        id="r1",
        source_id="e1",
        target_id="e2",
        rel_type="depends_on",
        rel_category="structural",
    )
    assert rel.confidence == 0.5
    assert rel.strength == 0.5
    assert rel.bidirectional is False
    assert rel.decay_rate == 0.05
    assert rel.contradiction_of is None


def test_relationship_with_evidence():
    ev = Evidence(
        document_id="d1",
        quote="This is evidence.",
        location="paragraph 3",
    )
    rel = Relationship(
        id="r2",
        source_id="e1",
        target_id="e2",
        rel_type="causes",
        rel_category="causal",
        evidence=[ev],
    )
    assert len(rel.evidence) == 1
    assert rel.evidence[0].document_id == "d1"
    assert rel.evidence[0].quote == "This is evidence."
    assert rel.evidence[0].extracted_at is not None


def test_time_scope():
    ts = TimeScope(is_permanent=True)
    assert ts.valid_from is None
    assert ts.valid_until is None
    assert ts.is_permanent is True


def test_document():
    doc = Document(
        id="d1",
        source="vault",
        path="/notes/test.md",
        content="hello world",
        content_hash="abc123",
    )
    assert doc.source == "vault"
    assert doc.incomplete is False


def test_changeset():
    cs = ChangeSet(
        source="vault",
        path="/notes/test.md",
        change_type="created",
    )
    assert cs.change_type == "created"
    assert cs.timestamp is not None
