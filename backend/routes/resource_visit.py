from fastapi import APIRouter, HTTPException

from backend.db import postgres
from backend.models.dag import ResourceVisitRequest
from backend.orchestration import rocketride_client

router = APIRouter(prefix="/resource-visit", tags=["resource-visit"])


@router.post("")
async def record_visit(req: ResourceVisitRequest) -> dict:
    """
    Record that the user visited a resource URL for a given node.
    Validates that the resource_url belongs to the node's actual resources.
    Transitions the node from 'available' → 'seen' on first visit.
    """
    # Verify the node exists and the URL matches one of its resources
    nodes = await postgres.get_nodes(req.session_id)
    target_node = next((n for n in nodes if n.id == req.node_id), None)
    if not target_node:
        raise HTTPException(status_code=404, detail="Node not found")

    known_urls = {r.url for r in target_node.resources}
    if req.resource_url not in known_urls:
        raise HTTPException(
            status_code=400,
            detail="URL does not match any resource for this node",
        )

    status_changed = await postgres.record_resource_visit(
        req.session_id, req.node_id, req.resource_url
    )

    # Push updated DAG over WebSocket so the frontend reflects the seen status
    if status_changed:
        await rocketride_client.publish(
            "resource.visited",
            {"session_id": req.session_id, "node_id": req.node_id},
        )

    return {"recorded": True, "status_changed": status_changed}
