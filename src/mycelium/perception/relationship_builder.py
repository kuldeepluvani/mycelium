"""Batched relationship extraction with rationale and evidence."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.models import Relationship, Evidence


RELATIONSHIP_PROMPT = """Analyze these entity pairs and determine their relationships.

Entity pairs to analyze:
{pairs}

For each pair, determine:
1. The relationship type (e.g., depends_on, implements, owns, caused, related_to)
2. The relationship category (structural, causal, temporal, semantic)
3. A brief rationale explaining WHY they are connected
4. A confidence score (0.0 to 1.0)

Return JSON:
{{
  "relationships": [
    {{
      "source": "...",
      "target": "...",
      "rel_type": "...",
      "rel_category": "...",
      "rationale": "...",
      "confidence": 0.8
    }}
  ]
}}

If a pair has NO meaningful relationship, omit it. Output ONLY valid JSON."""

RELATIONSHIP_SYSTEM = "You analyze entity pairs to determine their relationships. Be precise with relationship types and provide clear rationale."


@dataclass
class BatchRelationshipResult:
    relationships: list[Relationship] = field(default_factory=list)
    call_cost: int = 0


class RelationshipBuilder:
    def __init__(self, llm: ClaudeCLI, batch_size: int = 15):
        self._llm = llm
        self._batch_size = batch_size

    async def build_batch(
        self, entity_pairs: list[tuple[str, str]], document_id: str = ""
    ) -> BatchRelationshipResult:
        """Build relationships for a batch of entity name pairs."""
        if not entity_pairs:
            return BatchRelationshipResult()

        all_relationships: list[Relationship] = []
        total_cost = 0

        # Process in batches
        for i in range(0, len(entity_pairs), self._batch_size):
            batch = entity_pairs[i : i + self._batch_size]
            pairs_text = "\n".join(f"- {src} <-> {tgt}" for src, tgt in batch)

            prompt = RELATIONSHIP_PROMPT.format(pairs=pairs_text)
            result = await self._llm.generate_json(prompt, system=RELATIONSHIP_SYSTEM)
            total_cost += 1

            if result is None:
                continue

            for r in result.get("relationships", []):
                rel = Relationship(
                    id=str(uuid4()),
                    source_id=r.get("source", ""),
                    target_id=r.get("target", ""),
                    rel_type=r.get("rel_type", "related_to"),
                    rel_category=r.get("rel_category", "semantic"),
                    rationale=r.get("rationale", ""),
                    confidence=r.get("confidence", 0.5),
                    evidence=[
                        Evidence(
                            document_id=document_id,
                            quote="",
                            location="relationship_builder",
                        )
                    ]
                    if document_id
                    else [],
                )
                all_relationships.append(rel)

        return BatchRelationshipResult(relationships=all_relationships, call_cost=total_cost)

    async def enrich_cross_document(self, graph, store, budget: int = 10) -> int:
        """Find and create relationships between entities from different documents.

        Groups entities by provenance (document source), finds pairs that share
        entity_class or domain but come from different documents, then uses the
        LLM to discover relationships between them.

        Returns number of new relationships created.
        """
        # Group entities by provenance (document source)
        doc_entities: dict[str, list[str]] = {}
        for eid in graph.all_entity_ids():
            e = graph.get_entity(eid)
            if e and e.provenance:
                for doc_id in e.provenance:
                    doc_entities.setdefault(doc_id, []).append(eid)

        # Build set of existing edges to avoid duplicates
        existing_edges: set[tuple[str, str]] = set()
        for rel in graph.all_relationships():
            existing_edges.add((rel.source_id, rel.target_id))
            existing_edges.add((rel.target_id, rel.source_id))

        # Find entity pairs sharing entity_class/domain but from different documents
        candidates: list[tuple[str, str, str, str]] = []  # (name_a, name_b, id_a, id_b)
        all_eids = graph.all_entity_ids()
        for i, eid_a in enumerate(all_eids):
            e_a = graph.get_entity(eid_a)
            if not e_a:
                continue
            for eid_b in all_eids[i + 1:]:
                if (eid_a, eid_b) in existing_edges:
                    continue
                e_b = graph.get_entity(eid_b)
                if not e_b:
                    continue
                # Same class or same domain, different documents
                if e_a.entity_class == e_b.entity_class or (
                    e_a.domain and e_a.domain == e_b.domain
                ):
                    prov_a = set(e_a.provenance)
                    prov_b = set(e_b.provenance)
                    if not prov_a & prov_b:  # no shared documents
                        candidates.append((e_a.name, e_b.name, eid_a, eid_b))

        if not candidates:
            return 0

        # Take top candidates (limit by budget * batch_size)
        candidates = candidates[: budget * self._batch_size]

        new_count = 0
        # Process in batches
        for batch_start in range(0, len(candidates), self._batch_size):
            batch = candidates[batch_start: batch_start + self._batch_size]
            pairs = [(c[0], c[1]) for c in batch]
            id_map = {(c[0], c[1]): (c[2], c[3]) for c in batch}

            result = await self.build_batch(pairs, "cross-document")
            for rel in result.relationships:
                # build_batch uses names as source_id/target_id
                key = (rel.source_id, rel.target_id)
                ids = id_map.get(key)
                if not ids:
                    # Try reverse
                    ids = id_map.get((rel.target_id, rel.source_id))
                if ids and (ids[0], ids[1]) not in existing_edges:
                    rel.source_id = ids[0]
                    rel.target_id = ids[1]
                    graph.add_relationship(rel)
                    store.upsert_relationship(rel)
                    existing_edges.add((ids[0], ids[1]))
                    existing_edges.add((ids[1], ids[0]))
                    new_count += 1

            if batch_start + self._batch_size >= budget * self._batch_size:
                break

        return new_count
