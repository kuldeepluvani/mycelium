"""In-process async event emitter for WebSocket broadcast."""
from __future__ import annotations
import asyncio
from typing import Any, Callable, Coroutine


class EventEmitter:
    def __init__(self):
        self._handlers: list[Callable[[dict], Coroutine]] = []

    def subscribe(self, handler: Callable[[dict], Coroutine]) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[dict], Coroutine]) -> None:
        self._handlers = [h for h in self._handlers if h is not handler]

    async def emit(self, event: dict[str, Any]) -> None:
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception:
                pass  # Don't let one bad handler break broadcast


# Global singleton
emitter = EventEmitter()
