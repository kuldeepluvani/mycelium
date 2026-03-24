"""Algorithmic intent parser — extracts entities and classifies query."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.brainstem.graph import KnowledgeGraph


@dataclass
class QueryIntent:
    mentioned_entities: list[str]  # entity IDs found in query
    query_type: str  # "search", "impact", "comparison", "general"
    subgraph_ids: set[str] = field(default_factory=set)  # entity IDs in relevant subgraph


class IntentParser:
    def __init__(self, graph: KnowledgeGraph, subgraph_hops: int = 3):
        self._graph = graph
        self._hops = subgraph_hops

    def parse(self, query: str) -> QueryIntent:
        query_lower = query.lower()

        # Find entities mentioned in query (by name or alias)
        mentioned = []
        for eid in self._graph.all_entity_ids():
            entity = self._graph.get_entity(eid)
            if not entity:
                continue
            if entity.name.lower() in query_lower or entity.canonical_name.lower() in query_lower:
                mentioned.append(eid)
                continue
            for alias in entity.aliases:
                if alias.lower() in query_lower:
                    mentioned.append(eid)
                    break

        # Classify query type
        query_type = self._classify(query_lower)

        # Build subgraph around mentioned entities
        subgraph_ids: set[str] = set()
        for eid in mentioned:
            subgraph_ids |= self._graph.subgraph_around(eid, self._hops)

        return QueryIntent(
            mentioned_entities=mentioned,
            query_type=query_type,
            subgraph_ids=subgraph_ids,
        )

    def _classify(self, query: str) -> str:
        impact_words = {"break", "affect", "impact", "change", "migrate", "remove", "delete", "fail"}
        comparison_words = {"compare", "difference", "versus", "vs", "better", "worse"}
        search_words = {"what", "where", "which", "find", "list", "show"}

        words = set(query.split())
        if words & impact_words:
            return "impact"
        if words & comparison_words:
            return "comparison"
        if words & search_words:
            return "search"
        return "general"
