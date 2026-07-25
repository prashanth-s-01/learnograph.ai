from fastapi import APIRouter, HTTPException

from backend.agents import dag_generator, dag_regenerator
from backend.db import postgres
from backend.memory import mem0_client
from backend.models.dag import DAGGenerateRequest, RegenerateRequest

router = APIRouter(prefix="/dag", tags=["dag"])


@router.post("/generate")
async def generate(req: DAGGenerateRequest) -> list[dict]:
    user_profile = mem0_client.read_user_profile()
    nodes = await dag_generator.generate_dag(req.topic, user_profile)
    if not nodes:
        raise HTTPException(status_code=422, detail="Topic is not a developer topic or produced no nodes.")
    await postgres.upsert_nodes(req.session_id, nodes)
    return [n.model_dump(mode="json") for n in nodes]


@router.post("/regenerate")
async def regenerate(req: RegenerateRequest) -> list[dict]:
    current_dag = await postgres.get_nodes(req.session_id)
    if not current_dag:
        raise HTTPException(status_code=404, detail="No DAG found for this session.")
    mem0_state = mem0_client.read_full_state()
    updated = await dag_regenerator.regenerate_dag(current_dag, mem0_state)
    await postgres.upsert_nodes(req.session_id, updated)
    return [n.model_dump(mode="json") for n in updated]


@router.get("/{session_id}")
async def get_dag(session_id: str) -> list[dict]:
    nodes = await postgres.get_nodes(session_id)
    return [n.model_dump(mode="json") for n in nodes]
