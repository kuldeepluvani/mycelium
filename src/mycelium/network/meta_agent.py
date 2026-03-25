"""L2 Meta-Agent — coordinates a group of L1 specialist agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ChildManifest:
    """What an L2 knows about each of its L1 children."""

    agent_id: str
    agent_name: str
    domain: str
    confidence: float
    entity_count: int
    knowledge_gaps: list[str] = field(default_factory=list)
    key_entities: list[str] = field(default_factory=list)


@dataclass
class DelegationStrategy:
    """How an L2 decides to handle a query."""

    mode: str  # "direct" | "fanout" | "self"
    target_ids: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class MetaAgent:
    """L2 agent that supervises a group of L1 specialists."""

    id: str
    name: str
    domain: str
    description: str = ""
    children: list[ChildManifest] = field(default_factory=list)
    cross_domain_edges: list[str] = field(default_factory=list)
    status: str = "active"
    tier: int = 2
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def pick_strategy(self, query_entities: set[str]) -> DelegationStrategy:
        """Decide: direct to one child, fanout to many, or self-answer."""
        if not query_entities or not self.children:
            return DelegationStrategy(
                mode="self", rationale="no entities or no children"
            )

        q_lower = {e.lower() for e in query_entities}
        scores: list[tuple[str, float]] = []
        for child in self.children:
            child_ents = {e.lower() for e in child.key_entities}
            overlap = len(child_ents & q_lower)
            if overlap > 0:
                scores.append((child.agent_id, overlap / len(q_lower)))

        if not scores:
            return DelegationStrategy(
                mode="self", rationale="no child covers query entities"
            )

        scores.sort(key=lambda x: x[1], reverse=True)
        top_id, top_score = scores[0]

        if top_score > 0.6 and len(scores) == 1:
            return DelegationStrategy(
                mode="direct",
                target_ids=[top_id],
                rationale=f"single child covers {top_score:.0%}",
            )

        if len(scores) >= 2 and scores[0][1] > 2 * scores[1][1]:
            return DelegationStrategy(
                mode="direct",
                target_ids=[top_id],
                rationale=f"dominant child ({top_score:.0%} vs {scores[1][1]:.0%})",
            )

        relevant = [s[0] for s in scores if s[1] > 0.1]
        return DelegationStrategy(
            mode="fanout",
            target_ids=relevant,
            rationale=f"{len(relevant)} children share query entities",
        )
