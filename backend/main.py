from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.db import postgres
from backend.orchestration import rocketride_client
from backend.routes import classify, comprehension, dag

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Learnograph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dag.router)
app.include_router(classify.router)
app.include_router(comprehension.router)

# ── Active WebSocket connections ──────────────────────────────────────────────
_ws_clients: set[WebSocket] = set()


async def _broadcast(data: dict) -> None:
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.add(ws)

    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        _ws_clients.discard(ws)


# ── RocketRide subscribers wired to push updates over WebSocket ───────────────

async def _on_dag_generated(data: dict) -> None:
    session_id = data.get("session_id", "default")
    # Nodes are already in Postgres (upsert_nodes ran before this publish)
    nodes = await postgres.get_nodes(session_id)
    await _broadcast({
        "event": "dag.generated",
        "data": {"nodes": [n.model_dump(mode="json") for n in nodes]},
    })
    # Enrichment runs in the background; node.enriched events push per-node updates
    from backend.agents.node_enricher import handle_dag_generated
    asyncio.create_task(handle_dag_generated(data))


async def _on_node_enriched(data: dict) -> None:
    """Fired after each node's resources are saved to Postgres; pushes fresh DAG to frontend."""
    session_id = data.get("session_id", "default")
    nodes = await postgres.get_nodes(session_id)
    await _broadcast({
        "event": "dag.updated",
        "data": {"nodes": [n.model_dump(mode="json") for n in nodes]},
    })


async def _on_content_classified(data: dict) -> None:
    from backend.agents.dag_regenerator import handle_content_classified
    await handle_content_classified(data)
    nodes = await postgres.get_nodes(data.get("session_id", "default"))
    await _broadcast({
        "event": "dag.updated",
        "data": {"nodes": [n.model_dump(mode="json") for n in nodes]},
    })


async def _on_dag_regenerated(data: dict) -> None:
    await _broadcast({"event": "dag.regenerated", "data": data})


async def _on_node_mastered(data: dict) -> None:
    session_id = data.get("session_id", "default")
    # Broadcast immediately using the already-correct DB state
    # (unlock_eligible_nodes ran in the route before this event was published)
    nodes = await postgres.get_nodes(session_id)
    await _broadcast({
        "event": "dag.updated",
        "data": {"nodes": [n.model_dump(mode="json") for n in nodes]},
    })
    # LLM-based regeneration runs in the background; it will broadcast again via dag.regenerated
    from backend.agents.dag_regenerator import handle_node_mastered
    asyncio.create_task(handle_node_mastered(data))


# ── Lifespan ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    await postgres.run_migrations()

    await rocketride_client.subscribe("dag.generated",      _on_dag_generated)
    await rocketride_client.subscribe("node.enriched",      _on_node_enriched)
    await rocketride_client.subscribe("content.classified", _on_content_classified)
    await rocketride_client.subscribe("dag.regenerated",    _on_dag_regenerated)
    await rocketride_client.subscribe("node.mastered",      _on_node_mastered)

    log.info("Learnograph API started — RocketRide subscribers active")


@app.on_event("shutdown")
async def shutdown() -> None:
    rocketride_client.cancel_all()
    await postgres.close_pool()
