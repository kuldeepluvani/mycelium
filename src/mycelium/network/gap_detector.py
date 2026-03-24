"""Knowledge gap detector."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.brainstem.graph import KnowledgeGraph


@dataclass
class KnowledgeGap:
    entity_id: str
    entity_name: str
    gap_type: str  # "isolated", "low_connectivity", "missing_domain"
    description: str


class GapDetector:
    def __init__(self, min_connections: int = 2):
        self._min_connections = min_connections

    def detect(self, graph: KnowledgeGraph) -> list[KnowledgeGap]:
        gaps = []
        for eid in graph.all_entity_ids():
            entity = graph.get_entity(eid)
            if not entity:
                continue
            neighbors = graph.get_neighbors(eid)
            if len(neighbors) == 0:
                gaps.append(
                    KnowledgeGap(
                        entity_id=eid,
                        entity_name=entity.name,
                        gap_type="isolated",
                        description=f"Entity '{entity.name}' has no connections",
                    )
                )
            elif len(neighbors) < self._min_connections:
                gaps.append(
                    KnowledgeGap(
                        entity_id=eid,
                        entity_name=entity.name,
                        gap_type="low_connectivity",
                        description=f"Entity '{entity.name}' has only {len(neighbors)} connection(s)",
                    )
                )
        return gaps
