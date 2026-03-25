"""Agent model."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Agent:
    id: str
    name: str
    domain: str
    description: str = ""
    seed_nodes: list[str] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)  # current membership
    status: str = "candidate"  # candidate, active, mature, retired
    queries_answered: int = 0
    avg_confidence: float = 0.0
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime | None = None
    pinned: bool = False
    parent_id: str | None = None  # L2 meta-agent that owns this L1
