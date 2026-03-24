"""Typed event definitions with NATS subject mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Connector events  —  mycelium.connector.*
# ---------------------------------------------------------------------------

class DocumentIngested(BaseEvent):
    source: str
    path: str
    content_hash: str


class DocumentChanged(BaseEvent):
    source: str
    path: str
    diff_summary: str | None = None


class DocumentDeleted(BaseEvent):
    source: str
    path: str
    orphaned_entity_ids: list[str] = []


# ---------------------------------------------------------------------------
# Perception events  —  mycelium.perception.*
# ---------------------------------------------------------------------------

class EntitiesExtracted(BaseEvent):
    node_id: str
    entities: list[dict]
    call_cost: int = 1


class RelationshipBuilt(BaseEvent):
    source_id: str
    target_id: str
    rel_type: str
    rationale: str | None = None
    confidence: float = 0.5


class ConceptFormed(BaseEvent):
    concept_id: str
    member_nodes: list[str]
    label: str
    description: str | None = None


class EntityMerged(BaseEvent):
    source_id: str
    target_id: str
    surviving_id: str
    merge_reason: str


class DataQuarantined(BaseEvent):
    entity_ids: list[str]
    reason: str
    layer: int


# ---------------------------------------------------------------------------
# Graph events  —  mycelium.graph.*
# ---------------------------------------------------------------------------

class GraphUpdated(BaseEvent):
    node_ids: list[str]
    edge_count_delta: int = 0


# ---------------------------------------------------------------------------
# Network events  —  mycelium.network.*
# ---------------------------------------------------------------------------

class ClusterDetected(BaseEvent):
    cluster_id: str
    node_ids: list[str]
    coherence_score: float


class AgentDiscovered(BaseEvent):
    agent_id: str
    domain: str
    seed_nodes: list[str]


class AgentRetired(BaseEvent):
    agent_id: str
    reason: str


class SpilloverTriggered(BaseEvent):
    from_agent: str
    to_agent: str
    shared_edges: list[str]


# ---------------------------------------------------------------------------
# Orchestration events  —  mycelium.orchestrator.*
# ---------------------------------------------------------------------------

class LearnCycleStarted(BaseEvent):
    budget: int
    priority_queue: list[str] = []


class CallSpent(BaseEvent):
    call_number: int
    budget_remaining: int
    task_type: str


class QuotaExhausted(BaseEvent):
    total_spent: int
    tasks_completed: int


class LearnCycleCompleted(BaseEvent):
    stats: dict = {}


# ---------------------------------------------------------------------------
# Serve events  —  mycelium.serve.*
# ---------------------------------------------------------------------------

class QueryReceived(BaseEvent):
    query: str
    session_id: str


class QueryRouted(BaseEvent):
    query: str
    agents: list[str]
    rationale: str | None = None


class QueryAnswered(BaseEvent):
    query: str
    response: str
    sources: list[str] = []


# ---------------------------------------------------------------------------
# System events  —  mycelium.system.*
# ---------------------------------------------------------------------------

class ErrorOccurred(BaseEvent):
    module: str
    error: str
    recoverable: bool = True


class HealthCheck(BaseEvent):
    module: str
    status: str
    metrics: dict = {}


# ---------------------------------------------------------------------------
# Subject mapping
# ---------------------------------------------------------------------------

_SUBJECT_MAP: dict[str, str] = {
    # Connector
    "DocumentIngested": "mycelium.connector",
    "DocumentChanged": "mycelium.connector",
    "DocumentDeleted": "mycelium.connector",
    # Perception
    "EntitiesExtracted": "mycelium.perception",
    "RelationshipBuilt": "mycelium.perception",
    "ConceptFormed": "mycelium.perception",
    "EntityMerged": "mycelium.perception",
    "DataQuarantined": "mycelium.perception",
    # Graph
    "GraphUpdated": "mycelium.graph",
    # Network
    "ClusterDetected": "mycelium.network",
    "AgentDiscovered": "mycelium.network",
    "AgentRetired": "mycelium.network",
    "SpilloverTriggered": "mycelium.network",
    # Orchestrator
    "LearnCycleStarted": "mycelium.orchestrator",
    "CallSpent": "mycelium.orchestrator",
    "QuotaExhausted": "mycelium.orchestrator",
    "LearnCycleCompleted": "mycelium.orchestrator",
    # Serve
    "QueryReceived": "mycelium.serve",
    "QueryRouted": "mycelium.serve",
    "QueryAnswered": "mycelium.serve",
    # System
    "ErrorOccurred": "mycelium.system",
    "HealthCheck": "mycelium.system",
}

# Reverse map: NATS subject -> event class
_CLASS_MAP: dict[str, type[BaseEvent]] = {
    f"{prefix}.{name}": cls
    for name, prefix in _SUBJECT_MAP.items()
    for cls in [globals()[name]]
}


def event_to_subject(event: BaseEvent) -> str:
    """Return the NATS subject string for an event instance."""
    cls_name = type(event).__name__
    prefix = _SUBJECT_MAP[cls_name]
    return f"{prefix}.{cls_name}"


def subject_to_event_class(subject: str) -> type[BaseEvent]:
    """Reverse lookup: NATS subject -> event class."""
    return _CLASS_MAP[subject]
