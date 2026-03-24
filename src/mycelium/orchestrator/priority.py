"""Priority scorer for learning task ordering."""
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass
from mycelium.shared.models import ChangeSet


@dataclass
class ScoredItem:
    changeset: ChangeSet
    score: float
    tier: str  # "changed", "stale", "crosslink"


class PriorityScorer:
    """Ranks documents for learning priority."""

    WEIGHTS = {
        "recency": 0.30,
        "connectivity": 0.25,
        "staleness": 0.20,
        "source_trust": 0.15,
        "change_magnitude": 0.10,
    }

    SOURCE_TRUST = {
        "vault": 1.0,
        "git": 0.7,
        "jira": 0.8,
        "confluence": 0.6,
    }

    def score(self, changeset: ChangeSet, connectivity: float = 0.0, staleness: float = 0.0) -> float:
        recency = self._recency_score(changeset.timestamp)
        source_trust = self.SOURCE_TRUST.get(changeset.source, 0.5)
        magnitude = 0.5 if changeset.change_type == "modified" else 1.0  # new > modified

        return (
            self.WEIGHTS["recency"] * recency
            + self.WEIGHTS["connectivity"] * connectivity
            + self.WEIGHTS["staleness"] * staleness
            + self.WEIGHTS["source_trust"] * source_trust
            + self.WEIGHTS["change_magnitude"] * magnitude
        )

    def _recency_score(self, ts: datetime) -> float:
        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (now - ts).total_seconds() / 3600
        if age_hours < 1:
            return 1.0
        elif age_hours < 24:
            return 0.8
        elif age_hours < 168:  # 1 week
            return 0.5
        else:
            return 0.2

    def allocate_budget(self, budget: int) -> dict[str, int]:
        """Allocate budget across tiers: 60% changed, 25% stale, 15% crosslink."""
        changed = int(budget * 0.60)
        stale = int(budget * 0.25)
        crosslink = budget - changed - stale  # remainder
        return {"changed": changed, "stale": stale, "crosslink": crosslink}

    def rank(self, changesets: list[ChangeSet]) -> list[ScoredItem]:
        scored = []
        for cs in changesets:
            s = self.score(cs)
            scored.append(ScoredItem(changeset=cs, score=s, tier="changed"))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
