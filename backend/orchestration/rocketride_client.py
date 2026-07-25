"""
RocketRide pipeline orchestration client.

Each Learnograph event maps to a named step in learnograph.pipe.
Publishing dispatches event data through the RocketRide pipeline and
simultaneously routes it to in-process asyncio queues so subscribers
are notified immediately without waiting for a network round-trip.

When ROCKETRIDE_API_KEY is not set or the service is unreachable, the
local queue path handles all orchestration transparently.

Pipeline:
  dag.generated      → enrich_nodes  (node_enricher subscribes)
  node.enriched      → (terminal — written to Postgres)
  content.classified → regenerate_dag (dag_regenerator subscribes)
  dag.regenerated    → frontend WebSocket broadcast
  node.mastered      → regenerate_dag (dag_regenerator subscribes)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine

log = logging.getLogger(__name__)

Handler = Callable[[dict], Coroutine[Any, Any, None]]

_PIPELINE_FILE = str(Path(__file__).parent.parent.parent / "learnograph.pipe")

# In-process queues — always used for delivery; RocketRide gets a copy for observability
_local_queues: dict[str, asyncio.Queue] = {}
_subscriber_tasks: list[asyncio.Task] = []


def _rr_configured() -> bool:
    return bool(os.getenv("ROCKETRIDE_API_KEY"))


async def _send_to_rocketride(event: str, data: dict) -> None:
    """Best-effort: send event payload to RocketRide pipeline for observability."""
    try:
        from rocketride import RocketRideClient  # type: ignore

        api_key = os.getenv("ROCKETRIDE_API_KEY", "")
        uri = os.getenv("ROCKETRIDE_URI", "https://cloud.rocketride.ai")

        async with RocketRideClient(uri=uri, auth=api_key) as client:
            result = await client.use(filepath=_PIPELINE_FILE)
            token = result["token"]
            await client.send(token, json.dumps({"event": event, "data": data}))
            log.info("RocketRide send OK: event=%s token=%s", event, token)
    except Exception as exc:
        log.debug("RocketRide send skipped (%s)", exc)


async def publish(event: str, data: dict) -> None:
    """
    Publish an event payload.

    Always enqueues data for local subscribers first (zero-latency delivery),
    then asynchronously forwards to RocketRide for pipeline observability when
    ROCKETRIDE_API_KEY is configured.
    """
    q = _local_queues.setdefault(event, asyncio.Queue())
    await q.put(data)
    log.info("Published: event=%s", event)

    if _rr_configured():
        asyncio.create_task(_send_to_rocketride(event, data))


async def subscribe(event: str, handler: Handler) -> None:
    """
    Register an async handler for an event.

    Starts a background task that drains the local queue, calling handler for
    each payload. If RocketRide is configured, the pipeline definition in
    learnograph.pipe documents the same topology for external observability.
    """
    async def _drain() -> None:
        q = _local_queues.setdefault(event, asyncio.Queue())
        while True:
            payload = await q.get()
            try:
                await handler(payload)
            except Exception as exc:
                log.error("Handler error for event=%s: %s", event, exc)

    task = asyncio.create_task(_drain(), name=f"rr-sub-{event}")
    _subscriber_tasks.append(task)
    log.info("Subscribed: event=%s", event)


def cancel_all() -> None:
    for t in _subscriber_tasks:
        t.cancel()
    _subscriber_tasks.clear()
