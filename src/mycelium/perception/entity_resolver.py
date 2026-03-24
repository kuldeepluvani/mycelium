"""Entity resolver — multi-signal deduplication."""
from __future__ import annotations

from dataclasses import dataclass

from mycelium.shared.models import Entity
from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.embeddings import EmbeddingIndex


@dataclass
class ResolutionResult:
    action: str  # "create", "merge", "relate"
    entity_name: str
    existing_id: str | None = None  # if merge/relate, the existing entity ID
    relationship_type: str | None = None  # if relate, what type
    reason: str = ""
    call_cost: int = 0


class EntityResolver:
    def __init__(
        self,
        graph: KnowledgeGraph,
        embeddings: EmbeddingIndex | None = None,
        llm: ClaudeCLI | None = None,
        similarity_threshold: float = 0.85,
    ):
        self._graph = graph
        self._embeddings = embeddings
        self._llm = llm
        self._threshold = similarity_threshold

    async def resolve(self, name: str, entity_class: str, description: str = "") -> ResolutionResult:
        # Step 1: Exact name match
        for eid in self._graph.all_entity_ids():
            existing = self._graph.get_entity(eid)
            if existing and existing.canonical_name.lower() == name.lower():
                return ResolutionResult(
                    action="merge", entity_name=name, existing_id=eid,
                    reason="exact_name_match",
                )

        # Step 2: Alias match
        for eid in self._graph.all_entity_ids():
            existing = self._graph.get_entity(eid)
            if existing:
                for alias in existing.aliases:
                    if alias.lower() == name.lower():
                        return ResolutionResult(
                            action="merge", entity_name=name, existing_id=eid,
                            reason="alias_match",
                        )

        # Step 3: Embedding similarity (if index available and non-empty)
        if self._embeddings and self._embeddings.count > 0:
            search_text = f"{name} {description}" if description else name
            results = self._embeddings.search(search_text, top_k=3)
            for r in results:
                if r.score >= self._threshold:
                    # High similarity — candidate for merge
                    existing = self._graph.get_entity(r.entity_id)
                    if existing and existing.entity_class == entity_class:
                        # Same class + high similarity = likely same entity
                        return ResolutionResult(
                            action="merge", entity_name=name, existing_id=r.entity_id,
                            reason=f"embedding_similarity_{r.score:.2f}",
                        )
                    elif existing:
                        # Different class but similar — create relationship instead
                        return ResolutionResult(
                            action="relate", entity_name=name, existing_id=r.entity_id,
                            relationship_type="related_to",
                            reason=f"embedding_similar_diff_class_{r.score:.2f}",
                        )

        # Step 4: LLM arbitration for ambiguous cases (if LLM available)
        # Skipped for now — will be used in batch mode

        # No match — create new
        return ResolutionResult(action="create", entity_name=name, reason="no_match")

    async def resolve_batch(self, entities: list[dict]) -> list[ResolutionResult]:
        """Resolve a batch of entities."""
        results = []
        for e in entities:
            r = await self.resolve(
                name=e.get("name", ""),
                entity_class=e.get("entity_class", ""),
                description=e.get("description", ""),
            )
            results.append(r)
        return results
