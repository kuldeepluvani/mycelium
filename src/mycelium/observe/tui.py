"""Textual-based live observation dashboard."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log
from textual.containers import Horizontal, Vertical
from mycelium.observe.store import ObservationStore


class StatusPanel(Static):
    def __init__(self, store: ObservationStore, **kwargs):
        super().__init__(**kwargs)
        self._store = store

    def on_mount(self) -> None:
        self.set_interval(2.0, self.refresh_status)
        self.refresh_status()

    def refresh_status(self) -> None:
        count = self._store.get_event_count()
        recent = self._store.get_events(limit=1)
        last_event = recent[0]["event_type"] if recent else "none"
        self.update(f"Events: {count} | Last: {last_event}")


class EventLog(Log):
    def __init__(self, store: ObservationStore, **kwargs):
        super().__init__(**kwargs)
        self._store = store
        self._last_id = 0

    def on_mount(self) -> None:
        self.set_interval(1.0, self.poll_events)

    def poll_events(self) -> None:
        events = self._store.get_events(limit=20)
        for event in reversed(events):
            if event["id"] > self._last_id:
                self.write_line(f"[{event['timestamp'][:19]}] {event['event_type']}: {event['payload'][:80]}")
                self._last_id = event["id"]


class MyceliumTUI(App):
    CSS = """
    StatusPanel { height: 3; padding: 1; background: $surface; }
    EventLog { height: 1fr; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, store: ObservationStore, **kwargs):
        super().__init__(**kwargs)
        self._store = store

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusPanel(self._store)
        yield EventLog(self._store)
        yield Footer()
