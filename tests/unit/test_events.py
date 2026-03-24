"""Tests for typed event definitions and NATS subject mapping."""

from datetime import datetime, timezone

from mycelium.bus.events import (
    BaseEvent,
    DocumentIngested,
    ErrorOccurred,
    LearnCycleStarted,
    _SUBJECT_MAP,
    event_to_subject,
    subject_to_event_class,
)


def test_document_ingested_serialization():
    evt = DocumentIngested(source="git", path="/repo/README.md", content_hash="abc123")
    data = evt.model_dump_json()
    restored = DocumentIngested.model_validate_json(data)
    assert restored.source == "git"
    assert restored.path == "/repo/README.md"
    assert restored.content_hash == "abc123"
    assert restored.event_id == evt.event_id
    assert restored.timestamp == evt.timestamp


def test_event_to_subject():
    di = DocumentIngested(source="s3", path="/a", content_hash="x")
    assert event_to_subject(di) == "mycelium.connector.DocumentIngested"

    lcs = LearnCycleStarted(budget=10)
    assert event_to_subject(lcs) == "mycelium.orchestrator.LearnCycleStarted"

    err = ErrorOccurred(module="bus", error="boom")
    assert event_to_subject(err) == "mycelium.system.ErrorOccurred"


def test_base_event_has_id_and_timestamp():
    evt = DocumentIngested(source="x", path="y", content_hash="z")
    assert isinstance(evt.event_id, str)
    assert len(evt.event_id) == 36  # UUID format
    assert isinstance(evt.timestamp, datetime)
    assert evt.timestamp.tzinfo is not None


def test_all_events_have_subject_mapping():
    """Every concrete event class must appear in the subject map."""
    import mycelium.bus.events as mod

    event_classes = [
        cls
        for name, cls in vars(mod).items()
        if isinstance(cls, type)
        and issubclass(cls, BaseEvent)
        and cls is not BaseEvent
    ]
    assert len(event_classes) > 0, "No event classes found"
    for cls in event_classes:
        assert cls.__name__ in _SUBJECT_MAP, f"{cls.__name__} missing from _SUBJECT_MAP"


def test_subject_to_event_class_roundtrip():
    di = DocumentIngested(source="s3", path="/a", content_hash="x")
    subject = event_to_subject(di)
    cls = subject_to_event_class(subject)
    assert cls is DocumentIngested
