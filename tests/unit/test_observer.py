"""Tests for mycelium.observe.observer.Observer."""
from __future__ import annotations

import pytest
from mycelium.observe.store import ObservationStore
from mycelium.observe.observer import Observer


@pytest.fixture
def store(tmp_path):
    s = ObservationStore(tmp_path / "test_observer.db")
    yield s
    s.close()


@pytest.fixture
def observer(store):
    return Observer(store)


@pytest.mark.asyncio
async def test_handle_event(observer: Observer, store: ObservationStore):
    await observer.handle_event("mycelium.test.SomeEvent", b'{"data": "value"}')
    events = store.get_events()
    assert len(events) == 1
    assert events[0]["subject"] == "mycelium.test.SomeEvent"
    assert events[0]["payload"] == '{"data": "value"}'


@pytest.mark.asyncio
async def test_get_recent_events(observer: Observer):
    await observer.handle_event("sub.a", b"payload1")
    await observer.handle_event("sub.b", b"payload2")
    await observer.handle_event("sub.c", b"payload3")
    recent = observer.get_recent_events()
    assert len(recent) == 3


@pytest.mark.asyncio
async def test_event_type_extracted(observer: Observer, store: ObservationStore):
    await observer.handle_event("mycelium.connector.DocumentIngested", b"{}")
    events = store.get_events()
    assert events[0]["event_type"] == "DocumentIngested"
    assert events[0]["module"] == "connector"
