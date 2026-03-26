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

    def batch_find_duplicates(self) -> list[tuple[str, str]]:
        """Scan all entities for duplicates by name/alias match. Returns list of (keep_id, merge_id) pairs."""
        entities = {}
        for eid in self._graph.all_entity_ids():
            e = self._graph.get_entity(eid)
            if e and not e.archived and not e.quarantined:
                entities[eid] = e

        # Build name → entity_id index
        name_index: dict[str, list[str]] = {}
        for eid, e in entities.items():
            key = e.canonical_name.lower().strip()
            name_index.setdefault(key, []).append(eid)
            for alias in e.aliases:
                alias_key = alias.lower().strip()
                name_index.setdefault(alias_key, []).append(eid)

        # Find groups with >1 entity
        seen_pairs: set[tuple[str, str]] = set()
        merge_pairs: list[tuple[str, str]] = []
        for key, eids in name_index.items():
            unique_ids = list(set(eids))
            if len(unique_ids) < 2:
                continue
            # Pick the one with highest confidence as survivor
            unique_ids.sort(key=lambda eid: entities[eid].confidence, reverse=True)
            for i in range(1, len(unique_ids)):
                pair = (unique_ids[0], unique_ids[i])
                pair_key = tuple(sorted(pair))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    merge_pairs.append(pair)

        return merge_pairs

    def merge_entities(self, keep_id: str, remove_id: str, store=None):
        """Merge remove_id into keep_id. Combines provenance, keeps higher confidence, transfers edges."""
        keeper = self._graph.get_entity(keep_id)
        removed = self._graph.get_entity(remove_id)
        if not keeper or not removed:
            return None

        # Combine provenance
        combined_prov = list(set(keeper.provenance + removed.provenance))
        keeper.provenance = combined_prov

        # Keep higher confidence
        keeper.confidence = max(keeper.confidence, removed.confidence)

        # Combine aliases
        combined_aliases = list(set(keeper.aliases + removed.aliases + [removed.name]))
        keeper.aliases = combined_aliases

        # Transfer relationships from removed to keeper
        for rel in list(self._graph.all_relationships()):
            if rel.source_id == remove_id:
                rel.source_id = keep_id
                if store:
                    store.upsert_relationship(rel)
            elif rel.target_id == remove_id:
                rel.target_id = keep_id
                if store:
                    store.upsert_relationship(rel)

        # Remove the duplicate
        self._graph.remove_entity(remove_id)
        if store:
            store.execute("UPDATE entities SET archived = 1 WHERE id = ?", (remove_id,))
            store.conn.commit()
            store.upsert_entity(keeper)

        # Update in-memory graph
        self._graph.add_entity(keeper)

        return keeper

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
