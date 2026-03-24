"""NATS JetStream event bus — connects, publishes, subscribes."""
from __future__ import annotations

import nats
from nats.js import JetStreamContext

from mycelium.bus.publisher import TypedPublisher
from mycelium.bus.subscriber import TypedSubscriber
from mycelium.bus.events import BaseEvent


class EventBus:
    """High-level event bus wrapping NATS JetStream with typed pub/sub."""

    def __init__(self, url: str = "nats://localhost:4222", stream_prefix: str = "mycelium") -> None:
        self._url = url
        self._prefix = stream_prefix
        self._nc = None
        self._js: JetStreamContext | None = None
        self._publisher: TypedPublisher | None = None
        self._subscriber: TypedSubscriber | None = None

    async def connect(self) -> None:
        """Connect to NATS and initialize JetStream context and stream."""
        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()
        # Ensure stream exists for our subjects
        try:
            await self._js.add_stream(
                name=self._prefix,
                subjects=[f"{self._prefix}.>"],
            )
        except Exception:
            # Stream may already exist
            pass
        self._publisher = TypedPublisher(self._js, self._prefix)
        self._subscriber = TypedSubscriber(self._js, self._prefix)

    async def publish(self, event: BaseEvent) -> None:
        """Publish a typed event via the publisher."""
        if self._publisher is None:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        await self._publisher.publish(event)

    async def subscribe(self, event_class: type[BaseEvent], handler) -> None:
        """Subscribe to a typed event class."""
        if self._subscriber is None:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        await self._subscriber.subscribe(event_class, handler)

    async def subscribe_wildcard(self, subject: str, handler) -> None:
        """Subscribe to a wildcard subject for raw observation."""
        if self._subscriber is None:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        await self._subscriber.subscribe_wildcard(subject, handler)

    async def drain(self) -> None:
        """Drain subscriber and NATS connection."""
        if self._subscriber:
            await self._subscriber.drain()
        if self._nc:
            await self._nc.drain()

    async def health_check(self) -> bool:
        """Return True if NATS connection is alive."""
        try:
            if self._nc and self._nc.is_connected:
                return True
        except Exception:
            pass
        return False

    @property
    def is_connected(self) -> bool:
        """Check if the underlying NATS connection is active."""
        return self._nc is not None and self._nc.is_connected
