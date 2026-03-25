import pytest
import asyncio
from mycelium.serve.event_emitter import EventEmitter


@pytest.mark.asyncio
async def test_emit_and_subscribe():
    emitter = EventEmitter()
    received = []

    async def handler(event):
        received.append(event)

    emitter.subscribe(handler)
    await emitter.emit({"type": "test", "data": "hello"})
    assert len(received) == 1
    assert received[0]["type"] == "test"


@pytest.mark.asyncio
async def test_unsubscribe():
    emitter = EventEmitter()
    received = []

    async def handler(event):
        received.append(event)

    emitter.subscribe(handler)
    emitter.unsubscribe(handler)
    await emitter.emit({"type": "test", "data": "hello"})
    assert len(received) == 0


@pytest.mark.asyncio
async def test_handler_error_doesnt_break_others():
    emitter = EventEmitter()
    received = []

    async def bad_handler(event):
        raise ValueError("boom")

    async def good_handler(event):
        received.append(event)

    emitter.subscribe(bad_handler)
    emitter.subscribe(good_handler)
    await emitter.emit({"type": "test"})
    assert len(received) == 1
