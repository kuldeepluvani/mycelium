"""Build rich agent context from graph data."""
from __future__ import annotations
from mycelium.brainstem.graph import KnowledgeGraph


def build_agent_context(graph: KnowledgeGraph, node_ids: list[str],
                        max_entities: int = 30, max_neighbors: int = 8) -> str:
    """Build detailed context string with entity descriptions and relationship metadata.

    Returns a structured text block showing each entity with its confidence,
    description, and typed relationships including rationale.
    """
    lines = []

    for nid in node_ids[:max_entities]:
        e = graph.get_entity(nid)
        if not e:
            continue

        # Entity header with confidence
        conf_pct = f"{e.confidence * 100:.0f}%"
        desc = f" — {e.description}" if e.description else ""
        lines.append(f"### {e.name} ({e.entity_class}, confidence: {conf_pct}){desc}")

        # Find relationships involving this entity
        neighbors_shown = 0
        for rel in graph.all_relationships():
            if neighbors_shown >= max_neighbors:
                break
            if rel.source_id == nid:
                n = graph.get_entity(rel.target_id)
                if n:
                    rationale_str = f" — {rel.rationale}" if rel.rationale else ""
                    lines.append(
                        f"  → {rel.rel_type} {n.name} "
                        f"(confidence: {rel.confidence:.1f}){rationale_str}"
                    )
                    neighbors_shown += 1
            elif rel.target_id == nid:
                n = graph.get_entity(rel.source_id)
                if n:
                    rationale_str = f" — {rel.rationale}" if rel.rationale else ""
                    lines.append(
                        f"  ← {rel.rel_type} from {n.name} "
                        f"(confidence: {rel.confidence:.1f}){rationale_str}"
                    )
                    neighbors_shown += 1

        if neighbors_shown == 0:
            lines.append("  (no relationships)")

    return "\n".join(lines)
