"""Tests for knowledge gap detector."""
from __future__ import annotations
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.shared.models import Entity, Relationship
from mycelium.network.gap_detector import GapDetector


def _make_entity(eid: str) -> Entity:
    return Entity(
        id=eid,
        name=eid,
        canonical_name=eid.lower(),
        entity_class="concept",
    )


def _make_rel(source: str, target: str) -> Relationship:
    return Relationship(
        id=f"r-{source}-{target}",
        source_id=source,
        target_id=target,
        rel_type="related_to",
        rel_category="semantic",
    )


def test_isolated_entity():
    graph = KnowledgeGraph()
    graph.add_entity(_make_entity("lonely"))

    detector = GapDetector(min_connections=2)
    gaps = detector.detect(graph)

    assert len(gaps) == 1
    assert gaps[0].gap_type == "isolated"
    assert gaps[0].entity_id == "lonely"


def test_low_connectivity():
    graph = KnowledgeGraph()
    graph.add_entity(_make_entity("a"))
    graph.add_entity(_make_entity("b"))
    graph.add_relationship(_make_rel("a", "b"))

    detector = GapDetector(min_connections=2)
    gaps = detector.detect(graph)

    # Both nodes have 1 connection (< min 2)
    assert len(gaps) == 2
    gap_types = {g.gap_type for g in gaps}
    assert gap_types == {"low_connectivity"}


def test_well_connected_no_gaps():
    graph = KnowledgeGraph()
    for eid in ["a", "b", "c", "d"]:
        graph.add_entity(_make_entity(eid))

    # Connect 'a' to b, c, d
    graph.add_relationship(_make_rel("a", "b"))
    graph.add_relationship(_make_rel("a", "c"))
    graph.add_relationship(_make_rel("a", "d"))

    detector = GapDetector(min_connections=2)
    gaps = detector.detect(graph)

    # Only 'a' has 3 connections. b, c, d each have 1.
    a_gaps = [g for g in gaps if g.entity_id == "a"]
    assert len(a_gaps) == 0

    # b, c, d should each have low_connectivity
    other_gaps = [g for g in gaps if g.entity_id != "a"]
    assert len(other_gaps) == 3
    assert all(g.gap_type == "low_connectivity" for g in other_gaps)
