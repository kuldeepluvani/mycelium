"""FastAPI serve API — wired to orchestrator."""
from __future__ import annotations
import asyncio
import json as json_mod
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class AskRequest(BaseModel):
    query: str
    mode: str = "auto"


def create_app(orch=None, host: str = "127.0.0.1", api_key: str | None = None) -> FastAPI:
    app = FastAPI(title="Mycelium", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if api_key and request.client:
            client_host = request.client.host
            if client_host not in ("127.0.0.1", "::1", "localhost"):
                key = request.headers.get("X-API-Key")
                if key != api_key:
                    raise HTTPException(status_code=403, detail="Invalid API key")
        return await call_next(request)

    # WebSocket clients list
    ws_clients: list[WebSocket] = []

    # -------------------------------------------------------------------------
    # Health + Status
    # -------------------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/status")
    async def api_status():
        if not orch:
            return {
                "graph": {"nodes": 0, "edges": 0},
                "agents": {"total": 0, "active": 0, "meta_agents": 0},
                "last_session": None,
                "connectors": [],
            }
        last = orch.session_store.get_latest()
        last_session = None
        if last:
            last_session = {
                "id": last.id,
                "status": last.status,
                "entities_created": last.entities_created,
                "edges_created": last.edges_created,
                "started_at": last.started_at.isoformat() if last.started_at else None,
            }
        connectors: list[str] = []
        try:
            connectors = list(orch.connector_registry.source_types())
        except Exception:
            pass

        return {
            "graph": {
                "nodes": orch.graph.node_count(),
                "edges": orch.graph.edge_count(),
            },
            "agents": {
                "total": len(orch.agent_manager.agents),
                "active": len(orch.agent_manager.get_active()),
                "meta_agents": len(orch.agent_manager.get_meta_agents()),
            },
            "last_session": last_session,
            "connectors": connectors,
        }

    # -------------------------------------------------------------------------
    # Graph
    # -------------------------------------------------------------------------

    @app.get("/api/graph/nodes")
    async def graph_nodes():
        if not orch:
            return {"nodes": []}
        nodes = []
        for eid in orch.graph.all_entity_ids():
            entity = orch.graph.get_entity(eid)
            if entity:
                nodes.append(entity.model_dump(mode="json"))
        return {"nodes": nodes}

    @app.get("/api/graph/edges")
    async def graph_edges():
        if not orch:
            return {"edges": []}
        edges = [r.model_dump(mode="json") for r in orch.graph.all_relationships()]
        return {"edges": edges}

    @app.get("/api/graph/entity/{entity_id}")
    async def graph_entity(entity_id: str):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        entity = orch.graph.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
        neighbor_ids = list(orch.graph.get_neighbors(entity_id))
        relationships = [
            r.model_dump(mode="json")
            for r in orch.graph.all_relationships()
            if r.source_id == entity_id or r.target_id == entity_id
        ]
        return {
            "entity": entity.model_dump(mode="json"),
            "neighbor_ids": neighbor_ids,
            "relationships": relationships,
        }

    @app.get("/api/graph/diff")
    async def graph_diff(session_id: str | None = None):
        if not orch:
            return {"nodes": [], "edges": []}
        if not session_id:
            return {"nodes": [], "edges": []}
        session = orch.session_store.load(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        cutoff = session.started_at
        nodes = []
        for eid in orch.graph.all_entity_ids():
            entity = orch.graph.get_entity(eid)
            if entity:
                created = getattr(entity, "first_seen", None) or getattr(entity, "created_at", None)
                if created and created >= cutoff:
                    nodes.append(entity.model_dump(mode="json"))
        edges = []
        for r in orch.graph.all_relationships():
            created = getattr(r, "created_at", None)
            if created and created >= cutoff:
                edges.append(r.model_dump(mode="json"))
        return {"nodes": nodes, "edges": edges}

    # -------------------------------------------------------------------------
    # Agents
    # -------------------------------------------------------------------------

    @app.get("/api/agents")
    async def agents_list():
        if not orch:
            return {"agents": []}
        agents = []
        for a in orch.agent_manager.agents:
            agents.append({
                "id": a.id,
                "name": a.name,
                "domain": getattr(a, "domain", None),
                "description": getattr(a, "description", None),
                "status": getattr(a, "status", None),
                "node_count": len(getattr(a, "node_ids", [])),
                "confidence": getattr(a, "confidence", None),
                "pinned": getattr(a, "pinned", False),
                "parent_id": getattr(a, "parent_id", None),
            })
        return {"agents": agents}

    @app.get("/api/agents/hierarchy")
    async def agents_hierarchy():
        if not orch:
            return {"meta_agents": []}
        meta_agents = []
        for m in orch.agent_manager.get_meta_agents():
            children = []
            manifest = getattr(m, "manifest", None)
            if manifest:
                for child_id in getattr(manifest, "l1_agent_ids", []):
                    agent = orch.agent_manager.get(child_id)
                    if agent:
                        children.append({
                            "id": agent.id,
                            "name": agent.name,
                            "domain": getattr(agent, "domain", None),
                            "status": getattr(agent, "status", None),
                        })
            meta_agents.append({
                "id": m.id,
                "name": m.name,
                "domain": getattr(m, "domain", None),
                "description": getattr(m, "description", None),
                "children": children,
            })
        return {"meta_agents": meta_agents}

    @app.get("/api/agents/spillover")
    async def agents_spillover():
        if not orch:
            return {"spillover": []}
        try:
            rows = orch.store.execute(
                "SELECT * FROM spillover_cache ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            return {"spillover": [dict(r) for r in rows]}
        except Exception:
            return {"spillover": []}

    @app.put("/api/agents/{agent_id}/pin")
    async def agent_pin(agent_id: str, pinned: bool = True):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        if pinned:
            ok = orch.agent_manager.pin(agent_id)
        else:
            ok = orch.agent_manager.unpin(agent_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return {"ok": True, "agent_id": agent_id, "pinned": pinned}

    @app.put("/api/agents/{agent_id}/rename")
    async def agent_rename(agent_id: str, name: str):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        ok = orch.agent_manager.rename(agent_id, name)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return {"ok": True, "agent_id": agent_id, "name": name}

    @app.put("/api/agents/{agent_id}/retire")
    async def agent_retire(agent_id: str):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        ok = orch.agent_manager.retire(agent_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return {"ok": True, "agent_id": agent_id}

    # -------------------------------------------------------------------------
    # Ask
    # -------------------------------------------------------------------------

    @app.post("/api/ask")
    async def ask(req: AskRequest):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        from mycelium.serve.query_engine import QueryEngine
        from mycelium.serve.event_emitter import emitter

        engine = QueryEngine(orch=orch)

        await emitter.emit({"type": "ask.start", "query": req.query, "mode": req.mode})

        qr = await engine.ask(req.query, mode=req.mode)

        await emitter.emit({
            "type": "ask.done",
            "query": req.query,
            "agents_used": qr.agents_used,
            "mode": qr.mode,
        })

        # Save to query_history
        try:
            orch.store.execute(
                "INSERT INTO query_history (query, answer, agents_used, mode, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    req.query,
                    qr.answer,
                    json_mod.dumps(qr.agents_used),
                    qr.mode,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            orch.store.conn.commit()
        except Exception:
            pass

        return {
            "answer": qr.answer,
            "agents_used": qr.agents_used,
            "coordinated_by": qr.coordinated_by,
            "mode": qr.mode,
            "rationale": qr.rationale,
            "unknowns": qr.unknowns,
            "follow_ups": qr.follow_ups,
        }

    @app.get("/api/ask/history")
    async def ask_history(limit: int = 20):
        if not orch:
            return {"queries": []}
        try:
            rows = orch.store.execute(
                f"SELECT * FROM query_history ORDER BY created_at DESC LIMIT {limit}"
            ).fetchall()
            return {"queries": [dict(r) for r in rows]}
        except Exception:
            return {"queries": []}

    # -------------------------------------------------------------------------
    # Learn
    # -------------------------------------------------------------------------

    @app.post("/api/learn/start")
    async def learn_start(budget: int = 50):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")

        async def _run():
            from mycelium.serve.event_emitter import emitter
            await emitter.emit({"type": "learn.start", "budget": budget})
            try:
                session = await orch.learn(budget=budget)
                await emitter.emit({
                    "type": "learn.done",
                    "session_id": session.id,
                    "entities_created": session.entities_created,
                    "edges_created": session.edges_created,
                })
            except Exception as exc:
                await emitter.emit({"type": "learn.error", "error": str(exc)})

        asyncio.create_task(_run())
        return {"ok": True, "budget": budget, "status": "started"}

    @app.get("/api/learn/sessions")
    async def learn_sessions(limit: int = 20):
        if not orch:
            return {"sessions": []}
        sessions = orch.session_store.list_sessions()[:limit]
        result = []
        for s in sessions:
            result.append({
                "id": s.id,
                "status": s.status,
                "budget": s.budget,
                "spent": s.spent,
                "entities_created": s.entities_created,
                "edges_created": s.edges_created,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            })
        return {"sessions": result}

    @app.get("/api/learn/sessions/{session_id}")
    async def learn_session_detail(session_id: str):
        if not orch:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        session = orch.session_store.load(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {
            "id": session.id,
            "status": session.status,
            "budget": session.budget,
            "spent": session.spent,
            "entities_created": session.entities_created,
            "edges_created": session.edges_created,
            "agents_discovered": session.agents_discovered,
            "spillovers": session.spillovers,
            "documents_processed": list(session.documents_processed),
            "started_at": session.started_at.isoformat() if session.started_at else None,
        }

    # -------------------------------------------------------------------------
    # Observe
    # -------------------------------------------------------------------------

    @app.get("/api/observe/events")
    async def observe_events(
        type: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ):
        if not orch:
            return {"events": [], "total": 0}
        kwargs: dict[str, Any] = {"limit": limit}
        if type:
            kwargs["type"] = type
        if since:
            kwargs["since"] = since
        events = orch.observation_store.get_events(**kwargs)
        return {"events": events, "total": orch.observation_store.get_event_count()}

    @app.get("/api/observe/health")
    async def observe_health(module: str | None = None):
        if not orch:
            return {"metrics": []}
        kwargs: dict[str, Any] = {}
        if module:
            kwargs["module"] = module
        metrics = orch.observation_store.get_health_metrics(**kwargs)
        return {"metrics": metrics}

    # -------------------------------------------------------------------------
    # WebSocket
    # -------------------------------------------------------------------------

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket):
        from mycelium.serve.event_emitter import emitter

        await websocket.accept()
        ws_clients.append(websocket)

        async def broadcast(event: dict):
            try:
                await websocket.send_text(json_mod.dumps(event))
            except Exception:
                pass

        emitter.subscribe(broadcast)
        try:
            while True:
                # Keep connection alive; client can send pings
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            emitter.unsubscribe(broadcast)
            if websocket in ws_clients:
                ws_clients.remove(websocket)

    return app
