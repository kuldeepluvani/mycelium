"""FastAPI serve API with auth."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str
    rationale: list[str] = []
    unknowns: list[str] = []
    follow_ups: list[str] = []
    agents_used: list[str] = []


def create_app(host: str = "127.0.0.1", api_key: str | None = None) -> FastAPI:
    app = FastAPI(title="Mycelium", version="0.1.0")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if api_key and request.client:
            client_host = request.client.host
            if client_host not in ("127.0.0.1", "::1", "localhost"):
                key = request.headers.get("X-API-Key")
                if key != api_key:
                    raise HTTPException(status_code=403, detail="Invalid API key")
        return await call_next(request)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        # Placeholder — wired up when orchestrator is integrated
        return AskResponse(answer="Mycelium is not yet initialized. Run 'mycelium serve' with a loaded graph.")

    @app.get("/agents")
    async def list_agents():
        return {"agents": []}

    @app.get("/graph/stats")
    async def graph_stats():
        return {"nodes": 0, "edges": 0}

    return app
