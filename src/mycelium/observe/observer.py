"""Observer — subscribes to all NATS events and persists them."""
from __future__ import annotations

from mycelium.observe.store import ObservationStore


class Observer:
    def __init__(self, store: ObservationStore):
        self._store = store

    async def handle_event(self, subject: str, data: bytes) -> None:
        """Handle raw event from NATS wildcard subscription."""
        payload = data.decode("utf-8", errors="replace")
        event_type = subject.rsplit(".", 1)[-1] if "." in subject else subject
        module = subject.split(".")[1] if subject.count(".") >= 2 else None
        self._store.log_event(
            event_type=event_type,
            subject=subject,
            payload=payload,
            module=module,
        )

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        return self._store.get_events(limit=limit)

    def get_event_count(self) -> int:
        return self._store.get_event_count()
