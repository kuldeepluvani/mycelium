"""Unit tests for the NATS JetStream event bus (no NATS server required)."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestEventBusInit:
    """Test EventBus structural initialization."""

    def test_event_bus_init_defaults(self):
        """EventBus stores default url and prefix."""
        # Import lazily to avoid pulling in events module at collection time
        from mycelium.bus.bus import EventBus

        bus = EventBus()
        assert bus._url == "nats://localhost:4222"
        assert bus._prefix == "mycelium"
        assert bus._nc is None
        assert bus._js is None
        assert bus._publisher is None
        assert bus._subscriber is None

    def test_event_bus_init_custom(self):
        """EventBus stores custom url and prefix."""
        from mycelium.bus.bus import EventBus

        bus = EventBus(url="nats://custom:5222", stream_prefix="test_stream")
        assert bus._url == "nats://custom:5222"
        assert bus._prefix == "test_stream"

    def test_event_bus_not_connected_by_default(self):
        """EventBus reports not connected before connect() is called."""
        from mycelium.bus.bus import EventBus

        bus = EventBus()
        assert bus.is_connected is False


class TestTypedPublisherInit:
    """Test TypedPublisher structural initialization."""

    def test_publisher_accepts_js_context(self):
        """TypedPublisher stores the JetStream context and prefix."""
        from mycelium.bus.publisher import TypedPublisher

        mock_js = MagicMock()
        pub = TypedPublisher(js=mock_js, stream_prefix="test")
        assert pub._js is mock_js
        assert pub._prefix == "test"

    def test_publisher_default_prefix(self):
        """TypedPublisher defaults to 'mycelium' prefix."""
        from mycelium.bus.publisher import TypedPublisher

        mock_js = MagicMock()
        pub = TypedPublisher(js=mock_js)
        assert pub._prefix == "mycelium"


class TestTypedSubscriberInit:
    """Test TypedSubscriber structural initialization."""

    def test_subscriber_stores_js_reference(self):
        """TypedSubscriber stores the JetStream context."""
        from mycelium.bus.subscriber import TypedSubscriber

        mock_js = MagicMock()
        sub = TypedSubscriber(js=mock_js, stream_prefix="test")
        assert sub._js is mock_js
        assert sub._prefix == "test"

    def test_subscriber_starts_with_empty_subscriptions(self):
        """TypedSubscriber initializes with no active subscriptions."""
        from mycelium.bus.subscriber import TypedSubscriber

        mock_js = MagicMock()
        sub = TypedSubscriber(js=mock_js)
        assert sub._subscriptions == []

    def test_subscriber_default_prefix(self):
        """TypedSubscriber defaults to 'mycelium' prefix."""
        from mycelium.bus.subscriber import TypedSubscriber

        mock_js = MagicMock()
        sub = TypedSubscriber(js=mock_js)
        assert sub._prefix == "mycelium"
