from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg

from backend.config import settings
from backend.models.dag import DAGNode, NodeStatus, Resource


_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    pool = await get_pool()
    migration = open("backend/db/migrations/001_initial.sql").read()
    async with pool.acquire() as conn:
        await conn.execute(migration)


# ── DAG node CRUD ─────────────────────────────────────────────────────────────

def _row_to_node(row: asyncpg.Record) -> DAGNode:
    return DAGNode(
        id=row["node_id"],
        title=row["title"],
        description=row["description"],
        prerequisites=json.loads(row["prerequisites"]),
        difficulty=row["difficulty"],
        estimated_hours=row["estimated_hours"],
        success_criteria=row["success_criteria"],
        status=NodeStatus(row["status"]),
        resources=[Resource(**r) for r in json.loads(row["resources"])],
        completed_at=row["completed_at"],
        triggering_content=row["triggering_content"],
    )


async def clear_nodes(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM dag_nodes WHERE session_id=$1", session_id)


async def upsert_nodes(session_id: str, nodes: list[DAGNode]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO dag_nodes
                (session_id, node_id, title, description, prerequisites, difficulty,
                 estimated_hours, success_criteria, status, resources,
                 completed_at, triggering_content, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,NOW())
            ON CONFLICT (session_id, node_id) DO UPDATE SET
                title=EXCLUDED.title, description=EXCLUDED.description,
                prerequisites=EXCLUDED.prerequisites, difficulty=EXCLUDED.difficulty,
                estimated_hours=EXCLUDED.estimated_hours,
                success_criteria=EXCLUDED.success_criteria,
                status=EXCLUDED.status, resources=EXCLUDED.resources,
                completed_at=EXCLUDED.completed_at,
                triggering_content=EXCLUDED.triggering_content,
                updated_at=NOW()
            """,
            [
                (
                    session_id, n.id, n.title, n.description,
                    json.dumps(n.prerequisites), n.difficulty.value,
                    n.estimated_hours, n.success_criteria, n.status.value,
                    json.dumps([r.model_dump() for r in n.resources]),
                    n.completed_at, n.triggering_content,
                )
                for n in nodes
            ],
        )


async def get_nodes(session_id: str) -> list[DAGNode]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM dag_nodes WHERE session_id=$1 ORDER BY created_at", session_id
        )
    return [_row_to_node(r) for r in rows]


async def get_available_nodes(session_id: str) -> list[DAGNode]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM dag_nodes WHERE session_id=$1 AND status IN ('available','seen')",
            session_id,
        )
    return [_row_to_node(r) for r in rows]


async def update_node_status(
    session_id: str,
    node_id: str,
    status: NodeStatus,
    *,
    completed_at: datetime | None = None,
    triggering_content: str | None = None,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE dag_nodes
               SET status=$3, completed_at=$4, triggering_content=$5, updated_at=NOW()
             WHERE session_id=$1 AND node_id=$2
            """,
            session_id, node_id, status.value, completed_at, triggering_content,
        )


async def update_node_resources(
    session_id: str, node_id: str, resources: list[Resource]
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE dag_nodes SET resources=$3, updated_at=NOW() WHERE session_id=$1 AND node_id=$2",
            session_id, node_id, json.dumps([r.model_dump() for r in resources]),
        )
