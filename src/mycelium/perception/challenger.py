"""Layer 3: Adversarial challenge — independent verification of extractions."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.models import Document
from mycelium.perception.extractor import ExtractionResult
from mycelium.perception.structural import StructuralResult


CHALLENGE_PROMPT = """You are a skeptical reviewer. Review these extracted entities and relationships for accuracy.

Document content (excerpt):
{content}

Extracted entities:
{entities}

Extracted relationships:
{relationships}

For each item, rate as:
- CONFIRMED: clearly supported by the document
- UNCERTAIN: plausible but not directly stated
- REJECT: not supported or likely hallucinated

Return JSON:
{{
  "entity_verdicts": [
    {{"name": "...", "verdict": "CONFIRMED|UNCERTAIN|REJECT", "reason": "..."}}
  ],
  "relationship_verdicts": [
    {{"source": "...", "target": "...", "verdict": "CONFIRMED|UNCERTAIN|REJECT", "reason": "..."}}
  ]
}}

Be strict. If in doubt, mark UNCERTAIN. Output ONLY valid JSON."""

CHALLENGE_SYSTEM = "You are a skeptical fact-checker reviewing entity and relationship extractions. Be strict."


@dataclass
class ChallengeVerdict:
    name: str
    verdict: str  # CONFIRMED, UNCERTAIN, REJECT
    reason: str = ""


@dataclass
class ChallengeResult:
    entity_verdicts: list[ChallengeVerdict] = field(default_factory=list)
    relationship_verdicts: list[ChallengeVerdict] = field(default_factory=list)
    call_cost: int = 1
    skipped: bool = False
    skip_reason: str = ""


class AdversarialChallenger:
    def __init__(self, llm: ClaudeCLI, challenge_skip_anchor_ratio: float = 0.8):
        self._llm = llm
        self._skip_ratio = challenge_skip_anchor_ratio

    def should_skip(self, anchors: StructuralResult, is_first_cycle: bool) -> tuple[bool, str]:
        if is_first_cycle:
            return True, "first_cycle"
        if anchors.anchor_ratio >= self._skip_ratio:
            return True, "high_anchor_ratio"
        return False, ""

    async def challenge(
        self,
        document: Document,
        extraction: ExtractionResult,
        anchors: StructuralResult,
        is_first_cycle: bool = False,
    ) -> ChallengeResult:
        skip, reason = self.should_skip(anchors, is_first_cycle)
        if skip:
            # Auto-confirm everything
            verdicts = [
                ChallengeVerdict(name=e.get("name", ""), verdict="CONFIRMED", reason=f"skip: {reason}")
                for e in extraction.entities
            ]
            return ChallengeResult(entity_verdicts=verdicts, call_cost=0, skipped=True, skip_reason=reason)

        entities_text = "\n".join(
            f"- {e.get('name', '?')} ({e.get('entity_class', '?')}): {e.get('description', '')}"
            for e in extraction.entities
        )
        rels_text = "\n".join(
            f"- {r.get('source', '?')} --[{r.get('rel_type', '?')}]--> {r.get('target', '?')}: {r.get('rationale', '')}"
            for r in extraction.relationships
        )

        prompt = CHALLENGE_PROMPT.format(
            content=document.content[:2000],
            entities=entities_text or "(none)",
            relationships=rels_text or "(none)",
        )

        result = await self._llm.generate_json(prompt, system=CHALLENGE_SYSTEM)

        if result is None:
            return ChallengeResult(call_cost=1)

        entity_verdicts = [
            ChallengeVerdict(
                name=v.get("name", ""),
                verdict=v.get("verdict", "UNCERTAIN"),
                reason=v.get("reason", ""),
            )
            for v in result.get("entity_verdicts", [])
        ]

        rel_verdicts = [
            ChallengeVerdict(
                name=f"{v.get('source', '?')}->{v.get('target', '?')}",
                verdict=v.get("verdict", "UNCERTAIN"),
                reason=v.get("reason", ""),
            )
            for v in result.get("relationship_verdicts", [])
        ]

        return ChallengeResult(
            entity_verdicts=entity_verdicts,
            relationship_verdicts=rel_verdicts,
            call_cost=1,
        )
