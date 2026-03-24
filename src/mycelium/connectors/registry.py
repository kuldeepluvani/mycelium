"""Connector registry -- stores connectors by source type."""
from __future__ import annotations

from mycelium.connectors.base import BaseConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        src = connector.source_type()
        if src in self._connectors:
            raise ValueError(f"Connector for source '{src}' already registered")
        self._connectors[src] = connector

    def get(self, source_type: str) -> BaseConnector | None:
        return self._connectors.get(source_type)

    def all(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def source_types(self) -> list[str]:
        return list(self._connectors.keys())
