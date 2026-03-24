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
    def __init__(self, llm: ClaudeCLI):
        self._llm = llm

    async def extract(self, document: Document, anchors: StructuralResult) -> ExtractionResult:
        anchor_text = "\n".join(f"- {name} ({cls})" for name, cls in anchors.anchors.items())
        if not anchor_text:
            anchor_text = "(none found)"

        # Truncate content for prompt
        content = document.content[:3000]

        prompt = EXTRACTION_PROMPT.format(
            path=document.path,
            source=document.source,
            anchors=anchor_text,
            content=content,
        )

        result = await self._llm.generate_json(prompt, system=EXTRACTION_SYSTEM)

        if result is None:
            return ExtractionResult(call_cost=1)

        return ExtractionResult(
            entities=result.get("entities", []),
            relationships=result.get("relationships", []),
            claims=result.get("claims", []),
            call_cost=1,
        )
