import pytest
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity, Relationship


@pytest.fixture
def graph():
    return KnowledgeGraph()


def _entity(id: str, name: str = "test") -> Entity:
    return Entity(id=id, name=name, canonical_name=name, entity_class="tech")


def _rel(id: str, src: str, tgt: str) -> Relationship:
    return Relationship(id=id, source_id=src, target_id=tgt, rel_type="depends_on", rel_category="structural")


def test_add_entity(graph):
    graph.add_entity(_entity("e1"))
    assert graph.has_entity("e1")
    assert graph.node_count() == 1


def test_remove_entity(graph):
    graph.add_entity(_entity("e1"))
    graph.remove_entity("e1")
    assert not graph.has_entity("e1")


def test_get_entity(graph):
    e = _entity("e1", "Kubernetes")
    graph.add_entity(e)
    got = graph.get_entity("e1")
    assert got.name == "Kubernetes"


def test_add_relationship(graph):
    graph.add_entity(_entity("e1"))
    graph.add_entity(_entity("e2"))
    graph.add_relationship(_rel("r1", "e1", "e2"))
    assert graph.edge_count() == 1


def test_get_relationship(graph):
    graph.add_entity(_entity("e1"))
    graph.add_entity(_entity("e2"))
    graph.add_relationship(_rel("r1", "e1", "e2"))
    got = graph.get_relationship("r1")
    assert got is not None
    assert got.source_id == "e1"


def test_subgraph_1_hop(graph):
    for i in range(1, 4):
        graph.add_entity(_entity(f"e{i}"))
    graph.add_relationship(_rel("r1", "e1", "e2"))
    graph.add_relationship(_rel("r2", "e2", "e3"))
    sub = graph.subgraph_around("e1", hops=1)
    assert "e1" in sub
    assert "e2" in sub
    assert "e3" not in sub


def test_subgraph_2_hops(graph):
    for i in range(1, 4):
        graph.add_entity(_entity(f"e{i}"))
    graph.add_relationship(_rel("r1", "e1", "e2"))
    graph.add_relationship(_rel("r2", "e2", "e3"))
    sub = graph.subgraph_around("e1", hops=2)
    assert "e3" in sub


def test_snapshot_is_independent(graph):
    graph.add_entity(_entity("e1"))
    snap = graph.snapshot()
    graph.add_entity(_entity("e2"))
    assert snap.node_count() == 1
    assert graph.node_count() == 2


def test_get_neighbors(graph):
    graph.add_entity(_entity("e1"))
    graph.add_entity(_entity("e2"))
    graph.add_entity(_entity("e3"))
    graph.add_relationship(_rel("r1", "e1", "e2"))
    graph.add_relationship(_rel("r2", "e3", "e1"))
    neighbors = graph.get_neighbors("e1")
    assert neighbors == {"e2", "e3"}


def test_rebuild(graph):
    entities = [_entity("e1"), _entity("e2")]
    rels = [_rel("r1", "e1", "e2")]
    graph.rebuild_from_entities_and_relationships(entities, rels)
    assert graph.node_count() == 2
    assert graph.edge_count() == 1
