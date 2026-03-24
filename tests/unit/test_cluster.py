"""Tests for Louvain clustering engine."""
from __future__ import annotations
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity, Relationship
from mycelium.network.cluster import ClusterEngine


def _make_entity(eid: str) -> Entity:
    return Entity(
        id=eid,
        name=eid,
        canonical_name=eid.lower(),
        entity_class="concept",
    )


def _make_rel(source: str, target: str, rid: str | None = None) -> Relationship:
    return Relationship(
        id=rid or f"r-{source}-{target}",
        source_id=source,
        target_id=target,
        rel_type="related_to",
        rel_category="semantic",
    )


def _build_clique(graph: KnowledgeGraph, prefix: str, size: int) -> list[str]:
    """Build a fully connected clique of nodes."""
    ids = [f"{prefix}-{i}" for i in range(size)]
    for eid in ids:
        graph.add_entity(_make_entity(eid))
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            graph.add_relationship(_make_rel(a, b))
    return ids


def test_empty_graph_no_clusters():
    graph = KnowledgeGraph()
    # Add fewer nodes than min_cluster_size
    for i in range(5):
        graph.add_entity(_make_entity(f"e-{i}"))
    engine = ClusterEngine(min_cluster_size=10)
    clusters = engine.detect(graph)
    assert clusters == []


def test_detect_clusters():
    graph = KnowledgeGraph()
    # Two dense cliques of 12 nodes each, no cross-edges
    _build_clique(graph, "groupA", 12)
    _build_clique(graph, "groupB", 12)

    engine = ClusterEngine(min_cluster_size=10, min_coherence=0.1)
    clusters = engine.detect(graph)

    assert len(clusters) == 2
    cluster_sizes = sorted(c.size for c in clusters)
    assert cluster_sizes == [12, 12]

    # Verify all node_ids are present
    all_nodes = set()
    for c in clusters:
        all_nodes.update(c.node_ids)
    assert len(all_nodes) == 24


def test_min_size_filter():
    graph = KnowledgeGraph()
    # One small clique (5 nodes) and one large clique (12 nodes)
    _build_clique(graph, "small", 5)
    _build_clique(graph, "large", 12)

    engine = ClusterEngine(min_cluster_size=10, min_coherence=0.1)
    clusters = engine.detect(graph)

    # Only the large cluster should pass
    assert len(clusters) == 1
    assert clusters[0].size == 12


def test_stability_tracking():
    graph = KnowledgeGraph()
    _build_clique(graph, "stable", 12)

    engine = ClusterEngine(min_cluster_size=10, min_coherence=0.1)

    # First detection
    clusters1 = engine.detect(graph)
    assert len(clusters1) == 1
    assert clusters1[0].cycles_stable == 1

    # Second detection with same graph -> stability should increment
    clusters2 = engine.detect(graph)
    assert len(clusters2) == 1
    assert clusters2[0].cycles_stable == 2
