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
    def __init__(self, graph: KnowledgeGraph, embeddings=None, subgraph_hops: int = 3, semantic_threshold: float = 0.6):
        self._graph = graph
        self._embeddings = embeddings
        self._hops = subgraph_hops
        self._semantic_threshold = semantic_threshold

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

        # Semantic matching via embeddings when string matching finds few results
        if self._embeddings and hasattr(self._embeddings, 'count') and self._embeddings.count > 0 and len(mentioned) < 3:
            try:
                results = self._embeddings.search(query, top_k=5)
                for r in results:
                    if r.score >= self._semantic_threshold and r.entity_id not in mentioned:
                        if self._graph.has_entity(r.entity_id):
                            mentioned.append(r.entity_id)
            except Exception:
                pass  # Embeddings not available or search failed

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
