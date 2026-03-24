import pytest
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity
from mycelium.perception.extractor import ExtractionResult
from mycelium.perception.consistency import ConsistencyChecker


def _entity(id: str, name: str = "test") -> Entity:
    return Entity(id=id, name=name, canonical_name=name, entity_class="tech")


@pytest.fixture
def checker():
    return ConsistencyChecker(anomaly_entity_limit=50, anomaly_edge_limit=100)


@pytest.fixture
def empty_graph():
    return KnowledgeGraph()


@pytest.fixture
def populated_graph():
    g = KnowledgeGraph()
    g.add_entity(_entity("e1", "ServiceA"))
    return g


def test_empty_graph_is_clean(checker, empty_graph):
    extraction = ExtractionResult(
        entities=[{"name": "Foo", "entity_class": "tech"}],
        relationships=[],
    )
    result = checker.check(extraction, empty_graph)
    assert result.is_clean is True
    assert result.issues == []


def test_entity_anomaly(checker, populated_graph):
    entities = [{"name": f"ent_{i}", "entity_class": "tech"} for i in range(60)]
    extraction = ExtractionResult(entities=entities, relationships=[])
    result = checker.check(extraction, populated_graph)
    assert result.is_clean is False
    critical = [i for i in result.issues if i.severity == "critical"]
    assert len(critical) >= 1
    assert critical[0].issue_type == "degree_anomaly"
    assert "60" in critical[0].description


def test_edge_anomaly(checker, populated_graph):
    relationships = [
        {"source": f"a_{i}", "target": f"b_{i}", "rel_type": "uses"}
        for i in range(120)
    ]
    extraction = ExtractionResult(entities=[], relationships=relationships)
    result = checker.check(extraction, populated_graph)
    assert result.is_clean is False
    critical = [i for i in result.issues if i.severity == "critical"]
    assert len(critical) >= 1
    assert "120" in critical[0].description


def test_normal_extraction_is_clean(checker, populated_graph):
    entities = [{"name": f"ent_{i}", "entity_class": "tech"} for i in range(5)]
    relationships = [
        {"source": f"a_{i}", "target": f"b_{i}", "rel_type": "uses"}
        for i in range(3)
    ]
    extraction = ExtractionResult(entities=entities, relationships=relationships)
    result = checker.check(extraction, populated_graph)
    assert result.is_clean is True


def test_call_cost_always_zero(checker, populated_graph, empty_graph):
    extraction = ExtractionResult(entities=[], relationships=[])
    r1 = checker.check(extraction, empty_graph)
    r2 = checker.check(extraction, populated_graph)
    assert r1.call_cost == 0
    assert r2.call_cost == 0
