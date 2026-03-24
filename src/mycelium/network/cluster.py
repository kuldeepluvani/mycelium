"""Louvain community detection for agent discovery."""
from __future__ import annotations
from dataclasses import dataclass, field
import community as community_louvain  # python-louvain
from mycelium.brainstem.graph import KnowledgeGraph


@dataclass
class ClusterInfo:
    cluster_id: str
    node_ids: list[str]
    size: int
    coherence: float  # intra-cluster edge density
    cycles_stable: int = 0


class ClusterEngine:
    def __init__(
        self,
        min_cluster_size: int = 10,
        min_coherence: float = 0.3,
        max_inter_density: float = 0.15,
    ):
        self._min_size = min_cluster_size
        self._min_coherence = min_coherence
        self._max_inter = max_inter_density
        self._previous_clusters: dict[str, set[str]] = {}  # cluster_id -> node_ids from last cycle
        self._stability_counts: dict[str, int] = {}

    def detect(self, graph: KnowledgeGraph) -> list[ClusterInfo]:
        if graph.node_count() < self._min_size:
            return []

        # Convert to undirected for Louvain (it requires undirected graph)
        nx_graph = graph._graph.to_undirected()

        if nx_graph.number_of_nodes() == 0:
            return []

        # Run Louvain
        partition = community_louvain.best_partition(nx_graph)

        # Group nodes by community
        communities: dict[int, list[str]] = {}
        for node_id, comm_id in partition.items():
            communities.setdefault(comm_id, []).append(node_id)

        clusters = []
        for comm_id, node_ids in communities.items():
            if len(node_ids) < self._min_size:
                continue

            # Calculate coherence (intra-cluster edge density)
            subgraph = nx_graph.subgraph(node_ids)
            n = len(node_ids)
            max_edges = n * (n - 1) / 2 if n > 1 else 1
            actual_edges = subgraph.number_of_edges()
            coherence = actual_edges / max_edges if max_edges > 0 else 0

            if coherence < self._min_coherence:
                continue

            cluster_id = f"cluster-{comm_id}"

            # Track stability
            overlap = self._check_overlap(cluster_id, set(node_ids))
            cycles = self._stability_counts.get(cluster_id, 0)
            if overlap > 0.7:  # >70% same nodes = stable
                cycles += 1
            else:
                cycles = 1
            self._stability_counts[cluster_id] = cycles

            clusters.append(
                ClusterInfo(
                    cluster_id=cluster_id,
                    node_ids=node_ids,
                    size=len(node_ids),
                    coherence=coherence,
                    cycles_stable=cycles,
                )
            )

        # Update previous clusters for next cycle
        self._previous_clusters = {c.cluster_id: set(c.node_ids) for c in clusters}

        return clusters

    def _check_overlap(self, cluster_id: str, current_nodes: set[str]) -> float:
        prev = self._previous_clusters.get(cluster_id, set())
        if not prev:
            return 0.0
        intersection = prev & current_nodes
        union = prev | current_nodes
        return len(intersection) / len(union) if union else 0.0
