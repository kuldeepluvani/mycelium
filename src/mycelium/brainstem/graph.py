"""NetworkX-based knowledge graph with typed nodes and edges."""
from __future__ import annotations
import copy
import networkx as nx
from mycelium.shared.models import Entity, Relationship


class KnowledgeGraph:
    def __init__(self):
        self._graph = nx.DiGraph()

    def add_entity(self, entity: Entity) -> None:
        self._graph.add_node(entity.id, data=entity)

    def remove_entity(self, entity_id: str) -> None:
        if self._graph.has_node(entity_id):
            self._graph.remove_node(entity_id)

    def has_entity(self, entity_id: str) -> bool:
        return self._graph.has_node(entity_id)

    def get_entity(self, entity_id: str) -> Entity | None:
        if not self._graph.has_node(entity_id):
            return None
        return self._graph.nodes[entity_id].get("data")

    def add_relationship(self, rel: Relationship) -> None:
        self._graph.add_edge(rel.source_id, rel.target_id, key=rel.id, data=rel)

    def remove_relationship(self, rel_id: str) -> None:
        for u, v, data in list(self._graph.edges(data=True)):
            if data.get("data") and data["data"].id == rel_id:
                self._graph.remove_edge(u, v)
                break

    def get_relationship(self, rel_id: str) -> Relationship | None:
        for u, v, data in self._graph.edges(data=True):
            if data.get("data") and data["data"].id == rel_id:
                return data["data"]
        return None

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def subgraph_around(self, entity_id: str, hops: int = 2) -> set[str]:
        """BFS from entity_id up to N hops. Returns set of entity IDs."""
        if not self._graph.has_node(entity_id):
            return set()
        visited = set()
        queue = [(entity_id, 0)]
        while queue:
            node, depth = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            if depth < hops:
                for neighbor in list(self._graph.successors(node)) + list(self._graph.predecessors(node)):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))
        return visited

    def get_neighbors(self, entity_id: str) -> set[str]:
        if not self._graph.has_node(entity_id):
            return set()
        return set(self._graph.successors(entity_id)) | set(self._graph.predecessors(entity_id))

    def snapshot(self) -> KnowledgeGraph:
        """Return a shallow copy for read-only serve queries during learn."""
        new = KnowledgeGraph()
        new._graph = copy.deepcopy(self._graph)
        return new

    def rebuild_from_entities_and_relationships(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> None:
        """Rebuild graph from SQLite data."""
        self._graph.clear()
        for e in entities:
            self.add_entity(e)
        for r in relationships:
            if self.has_entity(r.source_id) and self.has_entity(r.target_id):
                self.add_relationship(r)

    def all_entity_ids(self) -> list[str]:
        return list(self._graph.nodes())
