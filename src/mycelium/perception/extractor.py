"""Layer 2: LLM deep extraction with structural anchors."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.models import Document
from mycelium.perception.structural import StructuralResult


EXTRACTION_PROMPT = """Analyze this document and extract structured knowledge.

Document path: {path}
Document source: {source}

Already confirmed entities (ground truth from document structure):
{anchors}

Document content:
{content}

Extract additional entities and relationships NOT already in the confirmed list above.

Return JSON:
{{
  "entities": [
    {{"name": "...", "entity_class": "...", "entity_subclass": "...", "domain": "...", "description": "...", "aliases": []}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "rel_type": "...", "rel_category": "...", "rationale": "...", "evidence_quote": "..."}}
  ],
  "claims": [
    {{"statement": "...", "confidence": 0.8, "evidence_quote": "..."}}
  ]
}}

Output ONLY valid JSON. No explanation."""

EXTRACTION_SYSTEM = "You extract structured entities and relationships from documents. Output valid JSON only. Be precise — do not hallucinate entities not supported by the text."


@dataclass
class ExtractionResult:
    entities: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)
    call_cost: int = 1


class DeepExtractor:
    def __init__(self, llm: ClaudeCLI, chunk_size: int = 3000, chunk_overlap: int = 500):
        self._llm = llm
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def _chunk_content(self, content: str) -> list[str]:
        """Split content into overlapping chunks. Returns full content if within chunk_size."""
        if len(content) <= self._chunk_size:
            return [content]
        chunks = []
        start = 0
        while start < len(content):
            end = start + self._chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start = end - self._chunk_overlap
            if start >= len(content):
                break
        return chunks

    async def extract(self, document: Document, structural_result: StructuralResult | None = None) -> ExtractionResult:
        # Build anchor text from structural result
        if structural_result is not None and structural_result.anchors:
            anchor_text = "\n".join(f"- {name} ({cls})" for name, cls in structural_result.anchors.items())
        else:
            anchor_text = "(none found)"

        chunks = self._chunk_content(document.content)

        all_entities: list[dict] = []
        all_relationships: list[dict] = []
        all_claims: list[dict] = []
        seen_entity_names: set[str] = set()
        total_cost = 0

        for chunk in chunks:
            prompt = EXTRACTION_PROMPT.format(
                path=document.path,
                source=document.source,
                anchors=anchor_text,
                content=chunk,
            )

            result = await self._llm.generate_json(prompt, system=EXTRACTION_SYSTEM)
            total_cost += 1

            if result is None:
                continue

            # Deduplicate entities by lowercased name
            for entity in result.get("entities", []):
                name = entity.get("name", "")
                if name.lower() not in seen_entity_names:
                    seen_entity_names.add(name.lower())
                    all_entities.append(entity)

            all_relationships.extend(result.get("relationships", []))
            all_claims.extend(result.get("claims", []))

        return ExtractionResult(
            entities=all_entities,
            relationships=all_relationships,
            claims=all_claims,
            call_cost=total_cost,
        )
