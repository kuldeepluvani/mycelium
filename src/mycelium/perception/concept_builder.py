"""Higher-order concept formation from entity clusters."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.models import Entity
from mycelium.brainstem.graph import KnowledgeGraph


CONCEPT_PROMPT = """These entities form a tightly connected cluster in a knowledge graph.

Entities:
{entities}

Synthesize a higher-order concept that describes what these entities collectively represent.

Return JSON:
{{
  "label": "...",
  "description": "...",
  "domain": "..."
}}

Output ONLY valid JSON."""

CONCEPT_SYSTEM = "You synthesize higher-order concepts from entity clusters. Be concise and precise."


@dataclass
class ConceptResult:
    entity: Entity | None = None  # The concept entity to add to graph
    member_entity_ids: list[str] = field(default_factory=list)
    call_cost: int = 0
    skipped: bool = False
    skip_reason: str = ""


class ConceptBuilder:
    def __init__(self, llm: ClaudeCLI, min_cluster_size: int = 5):
        self._llm = llm
        self._min_size = min_cluster_size

    async def build_concept(
        self, entity_ids: list[str], graph: KnowledgeGraph
    ) -> ConceptResult:
        """Attempt to form a concept from a cluster of entities."""
        if len(entity_ids) < self._min_size:
            return ConceptResult(
                skipped=True,
                skip_reason=f"cluster_too_small ({len(entity_ids)} < {self._min_size})",
            )

        # Gather entity info
        entities_info = []
        for eid in entity_ids:
            e = graph.get_entity(eid)
            if e:
                entities_info.append(
                    f"- {e.name} ({e.entity_class}): {e.description or 'no description'}"
                )

        if not entities_info:
            return ConceptResult(skipped=True, skip_reason="no_entities_found")

        prompt = CONCEPT_PROMPT.format(entities="\n".join(entities_info))
        result = await self._llm.generate_json(prompt, system=CONCEPT_SYSTEM)

        if result is None:
            return ConceptResult(call_cost=1, skipped=True, skip_reason="llm_failed")

        concept_entity = Entity(
            id=f"concept-{uuid4().hex[:8]}",
            name=result.get("label", "Unknown Concept"),
            canonical_name=result.get("label", "Unknown Concept"),
            entity_class="concept",
            entity_subclass="synthesized",
            domain=result.get("domain"),
            description=result.get("description"),
            provenance=[],
            confidence=0.6,
        )

        return ConceptResult(
            entity=concept_entity,
            member_entity_ids=entity_ids,
            call_cost=1,
        )
