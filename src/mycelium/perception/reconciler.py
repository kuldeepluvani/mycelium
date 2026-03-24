"""Layer 5: Reconciliation — resolves conflicts via LLM, quarantines ambiguous data."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.shared.llm import ClaudeCLI
from mycelium.perception.extractor import ExtractionResult
from mycelium.perception.challenger import ChallengeResult, ChallengeVerdict
from mycelium.perception.consistency import ConsistencyResult


RECONCILE_PROMPT = """Two reviewers disagree on extracted knowledge. Arbitrate.

Challenge verdicts (Reviewer 2 disagreed with these):
{conflicts}

Graph consistency issues found:
{consistency_issues}

Original extraction context:
{context}

For each conflict, provide your verdict:
Return JSON:
{{
  "verdicts": [
    {{"name": "...", "verdict": "ACCEPT|REJECT|QUARANTINE", "reason": "...", "confidence": 0.8}}
  ]
}}

ACCEPT = include in knowledge graph
REJECT = discard
QUARANTINE = store separately for human review

Output ONLY valid JSON."""

RECONCILE_SYSTEM = "You are an impartial arbiter resolving disagreements about extracted knowledge. Be conservative — when in doubt, QUARANTINE."


@dataclass
class ReconcileVerdict:
    name: str
    verdict: str  # ACCEPT, REJECT, QUARANTINE
    reason: str
    confidence: float = 0.5


@dataclass
class ReconcileResult:
    verdicts: list[ReconcileVerdict] = field(default_factory=list)
    quarantined_entities: list[str] = field(default_factory=list)
    rejected_entities: list[str] = field(default_factory=list)
    accepted_entities: list[str] = field(default_factory=list)
    call_cost: int = 0
    skipped: bool = False


class Reconciler:
    def __init__(self, llm: ClaudeCLI):
        self._llm = llm

    def needs_reconciliation(self, challenge: ChallengeResult, consistency: ConsistencyResult) -> bool:
        """Check if there are conflicts needing reconciliation."""
        if challenge.skipped:
            return False
        has_rejections = any(v.verdict == "REJECT" for v in challenge.entity_verdicts)
        has_consistency_issues = len(consistency.issues) > 0
        return has_rejections or has_consistency_issues

    async def reconcile(
        self,
        extraction: ExtractionResult,
        challenge: ChallengeResult,
        consistency: ConsistencyResult,
    ) -> ReconcileResult:
        if not self.needs_reconciliation(challenge, consistency):
            # No conflicts — accept everything
            accepted = [e.get("name", "") for e in extraction.entities]
            return ReconcileResult(accepted_entities=accepted, skipped=True)

        # Build conflict summary
        conflicts = []
        for v in challenge.entity_verdicts:
            if v.verdict in ("REJECT", "UNCERTAIN"):
                conflicts.append(f"- {v.name}: {v.verdict} — {v.reason}")

        consistency_text = []
        for issue in consistency.issues:
            consistency_text.append(f"- [{issue.severity}] {issue.issue_type}: {issue.description}")

        context = "\n".join(
            f"- {e.get('name', '?')} ({e.get('entity_class', '?')})"
            for e in extraction.entities[:20]  # limit context
        )

        prompt = RECONCILE_PROMPT.format(
            conflicts="\n".join(conflicts) or "(none)",
            consistency_issues="\n".join(consistency_text) or "(none)",
            context=context or "(none)",
        )

        result = await self._llm.generate_json(prompt, system=RECONCILE_SYSTEM)

        if result is None:
            # LLM failed — quarantine everything in conflict
            quarantined = [v.name for v in challenge.entity_verdicts if v.verdict == "REJECT"]
            accepted = [e.get("name", "") for e in extraction.entities if e.get("name", "") not in quarantined]
            return ReconcileResult(
                quarantined_entities=quarantined,
                accepted_entities=accepted,
                call_cost=1,
            )

        verdicts = []
        quarantined = []
        rejected = []
        accepted = []

        for v in result.get("verdicts", []):
            rv = ReconcileVerdict(
                name=v.get("name", ""),
                verdict=v.get("verdict", "QUARANTINE"),
                reason=v.get("reason", ""),
                confidence=v.get("confidence", 0.5),
            )
            verdicts.append(rv)
            if rv.verdict == "QUARANTINE":
                quarantined.append(rv.name)
            elif rv.verdict == "REJECT":
                rejected.append(rv.name)
            else:
                accepted.append(rv.name)

        return ReconcileResult(
            verdicts=verdicts,
            quarantined_entities=quarantined,
            rejected_entities=rejected,
            accepted_entities=accepted,
            call_cost=1,
        )
