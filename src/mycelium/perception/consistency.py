"""Layer 4: Graph consistency check — algorithmic, no LLM calls."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.perception.extractor import ExtractionResult


@dataclass
class ConsistencyIssue:
    issue_type: str  # "contradiction", "temporal", "degree_anomaly", "cluster_mismatch"
    entity_name: str
    description: str
    severity: str = "warning"  # "warning" or "critical"


@dataclass
class ConsistencyResult:
    issues: list[ConsistencyIssue] = field(default_factory=list)
    is_clean: bool = True
    call_cost: int = 0  # always 0 — purely algorithmic


class ConsistencyChecker:
    def __init__(self, anomaly_entity_limit: int = 50, anomaly_edge_limit: int = 100):
        self._entity_limit = anomaly_entity_limit
        self._edge_limit = anomaly_edge_limit

    def check(self, extraction: ExtractionResult, graph: KnowledgeGraph) -> ConsistencyResult:
        issues: list[ConsistencyIssue] = []

        # Skip if graph is empty (first cycle)
        if graph.node_count() == 0:
            return ConsistencyResult(issues=[], is_clean=True)

        # Check 1: Degree anomaly — too many entities from one document
        if len(extraction.entities) > self._entity_limit:
            issues.append(ConsistencyIssue(
                issue_type="degree_anomaly",
                entity_name="(document)",
                description=f"Document produced {len(extraction.entities)} entities (limit: {self._entity_limit})",
                severity="critical",
            ))

        # Check 2: Edge anomaly — too many relationships from one document
        if len(extraction.relationships) > self._edge_limit:
            issues.append(ConsistencyIssue(
                issue_type="degree_anomaly",
                entity_name="(document)",
                description=f"Document produced {len(extraction.relationships)} relationships (limit: {self._edge_limit})",
                severity="critical",
            ))

        # Check 3: Contradiction detection — new relationship contradicts existing
        for rel in extraction.relationships:
            source_name = rel.get("source", "")
            target_name = rel.get("target", "")
            rel_type = rel.get("rel_type", "")

            if not source_name or not target_name:
                continue

            # Find existing entities matching source/target by name
            for existing_entity_id in graph.all_entity_ids():
                existing = graph.get_entity(existing_entity_id)
                if existing and existing.name.lower() == source_name.lower():
                    neighbors = graph.get_neighbors(existing_entity_id)
                    for neighbor_id in neighbors:
                        neighbor = graph.get_entity(neighbor_id)
                        if neighbor and neighbor.name.lower() == target_name.lower():
                            # Found existing edge between same entities — check rel_type
                            candidate_rel_id = f"{existing_entity_id}-{neighbor_id}"
                            edge_data = graph.get_relationship(candidate_rel_id)
                            if edge_data and edge_data.rel_type != rel_type:
                                issues.append(ConsistencyIssue(
                                    issue_type="contradiction",
                                    entity_name=f"{source_name}->{target_name}",
                                    description=f"Existing rel_type '{edge_data.rel_type}' vs new '{rel_type}'",
                                    severity="warning",
                                ))

        is_clean = not any(i.severity == "critical" for i in issues)
        return ConsistencyResult(issues=issues, is_clean=is_clean)
