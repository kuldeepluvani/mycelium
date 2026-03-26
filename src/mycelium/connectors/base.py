"""Base connector interface for data sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from mycelium.shared.models import ChangeSet, Document


class BaseConnector(ABC):
    @abstractmethod
    async def discover_changes(self, since: datetime | None = None, **kwargs) -> list[ChangeSet]:
        """Discover documents changed since given timestamp."""
        ...

    @abstractmethod
    async def fetch_content(self, path: str) -> Document | None:
        """Fetch and parse a single document."""
        ...

    @abstractmethod
    def source_type(self) -> str:
        """Return connector source type identifier (e.g., 'vault', 'git')."""
        ...
