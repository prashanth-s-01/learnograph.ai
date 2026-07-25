from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.agents import comprehension as comp_agent, dag_regenerator
from backend.db import postgres
from backend.memory import mem0_client
from backend.models.dag import ComprehensionRequest, NodeStatus
from backend.orchestration import rocketride_client

router = APIRouter(prefix="/comprehension", tags=["comprehension"])


@router.post("/score")
async def score(req: ComprehensionRequest) -> dict:
    result = await comp_agent.score_comprehension(
        req.success_criteria,
        req.transcribed_answer,
    )

    if result.verdict == "pass":
        # API layer owns the write path: update Postgres + mem0 + publish node.mastered
        now = datetime.now(timezone.utc)
        await postgres.update_node_status(
            req.session_id,
            req.node_id,
            NodeStatus.mastered,
            completed_at=now,
        )
        await postgres.unlock_eligible_nodes(req.session_id)
        mem0_client.record_node_mastered(req.node_id, now.isoformat())

        # Publish node.mastered → triggers regenerate_dag via RocketRide pipeline
        await rocketride_client.publish(
            "node.mastered",
            {"node_id": req.node_id, "session_id": req.session_id},
        )

    return result.model_dump()
