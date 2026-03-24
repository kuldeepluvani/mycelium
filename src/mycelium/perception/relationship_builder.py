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
