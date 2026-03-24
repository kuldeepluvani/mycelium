"""5-layer perception engine — orchestrates the full extraction pipeline."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from mycelium.shared.models import Document, Entity
from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.config import PerceptionConfig
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.store import BrainstemStore
from mycelium.brainstem.embeddings import EmbeddingIndex
from mycelium.perception.structural import StructuralParser
from mycelium.perception.extractor import DeepExtractor
from mycelium.perception.challenger import AdversarialChallenger
from mycelium.perception.consistency import ConsistencyChecker
from mycelium.perception.reconciler import Reconciler
from mycelium.perception.entity_resolver import EntityResolver
from mycelium.perception.relationship_builder import RelationshipBuilder


@dataclass
class PerceptionStats:
    documents_processed: int = 0
    entities_created: int = 0
    entities_merged: int = 0
    relationships_created: int = 0
    quarantined: int = 0
    rejected: int = 0
    total_call_cost: int = 0
    errors: list[str] = field(default_factory=list)


class PerceptionEngine:
    """Orchestrates the 5-layer perception pipeline.

    Layer 1: Structural pre-parse (0 LLM calls)
    Layer 2: Deep extraction (1 LLM call)
    Layer 3: Adversarial challenge (0-1 LLM calls)
    Layer 4: Graph consistency check (0 LLM calls)
    Layer 5: Reconciliation (0-1 LLM calls)
    """

    def __init__(
        self,
        llm: ClaudeCLI,
        graph: KnowledgeGraph,
        store: BrainstemStore,
        embeddings: EmbeddingIndex | None = None,
        config: PerceptionConfig | None = None,
    ):
        self._llm = llm
        self._graph = graph
        self._store = store
        self._embeddings = embeddings
        self._config = config or PerceptionConfig()

        # Initialize sub-components
        self._structural = StructuralParser()
        self._extractor = DeepExtractor(llm)
        self._challenger = AdversarialChallenger(
            llm, challenge_skip_anchor_ratio=self._config.challenge_skip_anchor_ratio
        )
        self._consistency = ConsistencyChecker(
            anomaly_entity_limit=self._config.anomaly_entity_limit,
            anomaly_edge_limit=self._config.anomaly_edge_limit,
        )
        self._reconciler = Reconciler(llm)
        self._entity_resolver = EntityResolver(graph, embeddings, llm)
        self._relationship_builder = RelationshipBuilder(
            llm, batch_size=self._config.batch_size_relationships
        )

    async def process_document(
        self, document: Document, is_first_cycle: bool = False
    ) -> PerceptionStats:
        """Run the full 5-layer pipeline on a single document."""
        stats = PerceptionStats()

        try:
            # Layer 1: Structural pre-parse (0 calls)
            structural_result = self._structural.parse(document)

            # Layer 2: Deep extraction (1 call)
            extraction = await self._extractor.extract(document, structural_result)
            stats.total_call_cost += extraction.call_cost

            # Layer 3: Adversarial challenge (0-1 calls)
            challenge = await self._challenger.challenge(
                document, extraction, structural_result, is_first_cycle
            )
            stats.total_call_cost += challenge.call_cost

            # Layer 4: Graph consistency check (0 calls)
            consistency = self._consistency.check(extraction, self._graph)

            # Layer 5: Reconciliation (0-1 calls)
            reconcile = await self._reconciler.reconcile(
                extraction, challenge, consistency
            )
            stats.total_call_cost += reconcile.call_cost

            # Process accepted entities
            accepted_names = set(reconcile.accepted_entities)
            quarantined_names = set(reconcile.quarantined_entities)
            rejected_names = set(reconcile.rejected_entities)

            for entity_dict in extraction.entities:
                name = entity_dict.get("name", "")
                if not name:
                    continue

                # If reconciliation produced explicit lists, filter by them
                if reconcile.accepted_entities and name not in accepted_names:
                    if name in quarantined_names:
                        stats.quarantined += 1
                    elif name in rejected_names:
                        stats.rejected += 1
                    continue

                # Resolve: merge or create?
                resolution = await self._entity_resolver.resolve(
                    name=name,
                    entity_class=entity_dict.get("entity_class", "unknown"),
                    description=entity_dict.get("description", ""),
                )
                stats.total_call_cost += resolution.call_cost

                if resolution.action == "merge" and resolution.existing_id:
                    stats.entities_merged += 1
                elif resolution.action == "create":
                    entity = Entity(
                        id=f"ent-{uuid4().hex[:8]}",
                        name=name,
                        canonical_name=name,
                        entity_class=entity_dict.get("entity_class", "unknown"),
                        entity_subclass=entity_dict.get("entity_subclass"),
                        domain=entity_dict.get("domain"),
                        description=entity_dict.get("description"),
                        aliases=entity_dict.get("aliases", []),
                        provenance=[document.id],
                        confidence=0.5,
                    )
                    self._graph.add_entity(entity)
                    self._store.upsert_entity(entity)
                    if self._embeddings:
                        self._embeddings.add(
                            entity.id, f"{name} {entity.description or ''}"
                        )
                    stats.entities_created += 1

            # Build relationships
            if extraction.relationships:
                pairs = [
                    (r.get("source", ""), r.get("target", ""))
                    for r in extraction.relationships
                    if r.get("source") and r.get("target")
                ]
                if pairs:
                    rel_result = await self._relationship_builder.build_batch(
                        pairs, document.id
                    )
                    stats.total_call_cost += rel_result.call_cost
                    stats.relationships_created += len(rel_result.relationships)

                    for rel in rel_result.relationships:
                        source_id = self._find_entity_by_name(rel.source_id)
                        target_id = self._find_entity_by_name(rel.target_id)
                        if source_id and target_id:
                            rel.source_id = source_id
                            rel.target_id = target_id
                            self._graph.add_relationship(rel)
                            self._store.upsert_relationship(rel)

            stats.documents_processed = 1

        except Exception as e:
            stats.errors.append(str(e))

        return stats

    def _find_entity_by_name(self, name: str) -> str | None:
        """Find entity ID by name in graph."""
        name_lower = name.lower()
        for eid in self._graph.all_entity_ids():
            entity = self._graph.get_entity(eid)
            if entity and (
                entity.name.lower() == name_lower
                or entity.canonical_name.lower() == name_lower
            ):
                return eid
        return None

    async def process_batch(
        self,
        documents: list[Document],
        is_first_cycle: bool = False,
        max_concurrent: int = 3,
    ) -> PerceptionStats:
        """Process multiple documents with concurrency limit."""
        total_stats = PerceptionStats()
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_limit(doc: Document) -> PerceptionStats:
            async with semaphore:
                return await self.process_document(doc, is_first_cycle)

        results = await asyncio.gather(
            *(process_with_limit(doc) for doc in documents),
            return_exceptions=True,
        )

        for r in results:
            if isinstance(r, PerceptionStats):
                total_stats.documents_processed += r.documents_processed
                total_stats.entities_created += r.entities_created
                total_stats.entities_merged += r.entities_merged
                total_stats.relationships_created += r.relationships_created
                total_stats.quarantined += r.quarantined
                total_stats.rejected += r.rejected
                total_stats.total_call_cost += r.total_call_cost
                total_stats.errors.extend(r.errors)
            elif isinstance(r, Exception):
                total_stats.errors.append(str(r))

        return total_stats
