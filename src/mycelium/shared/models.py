from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(BaseModel):
    document_id: str
    quote: str
    location: str
    extracted_at: datetime = Field(default_factory=_now)


class TimeScope(BaseModel):
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_permanent: bool = False


class Entity(BaseModel):
    id: str
    name: str
    canonical_name: str
    entity_class: str
    entity_subclass: str | None = None
    domain: str | None = None
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    first_seen: datetime = Field(default_factory=_now)
    last_seen: datetime = Field(default_factory=_now)
    last_validated: datetime | None = None
    version: int = 1
    quarantined: bool = False
    archived: bool = False


class Relationship(BaseModel):
    id: str
    source_id: str
    target_id: str
    rel_type: str
    rel_category: str  # causal, structural, temporal, semantic
    rationale: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = 0.5
    strength: float = 0.5
    bidirectional: bool = False
    temporal_scope: TimeScope | None = None
    contradiction_of: str | None = None
    decay_rate: float = 0.05
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    last_validated: datetime | None = None
    quarantined: bool = False
    archived: bool = False


class Document(BaseModel):
    id: str
    source: str
    path: str
    content: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    wikilinks: list[str] = Field(default_factory=list)
    incomplete: bool = False


class ChangeSet(BaseModel):
    source: str
    path: str
    change_type: str  # "created", "modified", "deleted"
    diff_summary: str | None = None
    timestamp: datetime = Field(default_factory=_now)
