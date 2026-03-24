"""Tests for mycelium.serve.intent."""
from __future__ import annotations
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity
from mycelium.serve.intent import IntentParser


def _make_entity(eid: str, name: str, aliases: list[str] | None = None) -> Entity:
    return Entity(
        id=eid,
        name=name,
        canonical_name=name.lower().replace(" ", "-"),
        entity_class="service",
        aliases=aliases or [],
    )


def _build_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_entity(_make_entity("k8s", "Kubernetes", aliases=["k8s"]))
    g.add_entity(_make_entity("docker", "Docker"))
    g.add_entity(_make_entity("helm", "Helm"))
    from mycelium.shared.models import Relationship
    g.add_relationship(Relationship(
        id="r1", source_id="k8s", target_id="docker",
        rel_type="depends_on", rel_category="structural",
    ))
    g.add_relationship(Relationship(
        id="r2", source_id="k8s", target_id="helm",
        rel_type="uses", rel_category="structural",
    ))
    return g


def test_finds_mentioned_entities():
    g = _build_graph()
    parser = IntentParser(g)
    intent = parser.parse("Tell me about kubernetes")
    assert "k8s" in intent.mentioned_entities


def test_classifies_impact():
    g = _build_graph()
    parser = IntentParser(g)
    intent = parser.parse("what would break if we remove kubernetes")
    assert intent.query_type == "impact"


def test_classifies_search():
    g = _build_graph()
    parser = IntentParser(g)
    intent = parser.parse("what is kubernetes")
    assert intent.query_type == "search"


def test_subgraph_extracted():
    g = _build_graph()
    parser = IntentParser(g, subgraph_hops=2)
    intent = parser.parse("kubernetes deployment")
    assert "k8s" in intent.subgraph_ids
    # Docker and Helm are neighbors, should be in subgraph
    assert "docker" in intent.subgraph_ids
    assert "helm" in intent.subgraph_ids
