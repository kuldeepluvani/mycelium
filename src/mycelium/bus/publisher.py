"""Typed event publisher for NATS JetStream."""
from __future__ import annotations

from nats.js import JetStreamContext

from mycelium.bus.events import BaseEvent, event_to_subject


class TypedPublisher:
    """Publishes typed events to NATS JetStream subjects."""

    def __init__(self, js: JetStreamContext, stream_prefix: str = "mycelium") -> None:
        self._js = js
        self._prefix = stream_prefix

    async def publish(self, event: BaseEvent) -> None:
        """Serialize and publish a typed event to its derived subject."""
        subject = event_to_subject(event)
        data = event.model_dump_json().encode()
        await self._js.publish(subject, data)
