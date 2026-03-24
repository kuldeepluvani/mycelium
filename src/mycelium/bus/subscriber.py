"""Typed event subscriber for NATS JetStream."""
from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, Type

from nats.js import JetStreamContext

from mycelium.bus.events import BaseEvent, _SUBJECT_MAP


class TypedSubscriber:
    """Subscribes to NATS JetStream subjects with typed event handlers."""

    def __init__(self, js: JetStreamContext, stream_prefix: str = "mycelium") -> None:
        self._js = js
        self._prefix = stream_prefix
        self._subscriptions: list = []

    async def subscribe(
        self,
        event_class: Type[BaseEvent],
        handler: Callable[[BaseEvent], Awaitable[None]],
    ) -> None:
        """Subscribe to a typed event class, deserializing messages automatically."""
        cls_name = event_class.__name__
        prefix = _SUBJECT_MAP.get(cls_name)
        if prefix is None:
            raise ValueError(f"No subject mapping for event class: {cls_name}")

        subject = f"{prefix}.{cls_name}"
        sub = await self._js.subscribe(subject)
        self._subscriptions.append(sub)

        async def _dispatch() -> None:
            async for msg in sub.messages:
                event = event_class.model_validate_json(msg.data)
                await handler(event)
                await msg.ack()

        asyncio.create_task(_dispatch())

    async def subscribe_wildcard(
        self,
        subject: str,
        handler: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        """Raw wildcard subscription for the observation layer."""
        sub = await self._js.subscribe(subject)
        self._subscriptions.append(sub)

        async def _dispatch() -> None:
            async for msg in sub.messages:
                await handler(msg.subject, msg.data)
                await msg.ack()

        asyncio.create_task(_dispatch())

    async def drain(self) -> None:
        """Unsubscribe from all active subscriptions."""
        for sub in self._subscriptions:
            await sub.unsubscribe()
        self._subscriptions.clear()
