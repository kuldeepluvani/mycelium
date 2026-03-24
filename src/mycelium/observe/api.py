"""Observation REST API endpoints."""
from __future__ import annotations

from fastapi import FastAPI, Query
from mycelium.observe.store import ObservationStore


def create_observation_app(store: ObservationStore) -> FastAPI:
    app = FastAPI(title="Mycelium Observation", version="0.1.0")

    @app.get("/observe/events")
    async def get_events(
        event_type: str | None = None,
        limit: int = Query(default=100, le=1000),
        since: str | None = None,
    ):
        events = store.get_events(event_type=event_type, limit=limit, since=since)
        return {"events": events, "count": len(events)}

    @app.get("/observe/health")
    async def get_health(module: str | None = None, limit: int = Query(default=100, le=1000)):
        metrics = store.get_health_metrics(module=module, limit=limit)
        return {"metrics": metrics}

    @app.get("/observe/stats")
    async def get_stats():
        return {"total_events": store.get_event_count()}

    return app
