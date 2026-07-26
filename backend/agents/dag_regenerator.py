"""
Generated from: prompts/regenerate_dag.prompt
Contract rules: R1–R7
"""
from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI

from backend.config import settings
from backend.models.dag import DAGNode, NodeStatus
from backend.orchestration import rocketride_client

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

_SYSTEM = """
You are a DAG state manager for a developer learning platform.

Given the full current DAG (as JSON) and the user's mem0 learning state, return an updated
DAG JSON array with corrected statuses and reordered available nodes.

Rules (strictly enforced):
- Return EVERY node from the input — never drop nodes.
- Unlock (set status "available") every node whose ALL prerequisites are "mastered".
- Preserve all prerequisite arrays exactly as received — never add or remove edges.
- Never change a node's id, title, description, or success_criteria fields.
- Never change a "mastered" node's status to anything else.
- Use mem0_state.completed_at timestamps to infer learning pace; reorder available
  nodes by estimated fit (fastest learner → harder nodes first; slower → easier first).
- Never invent new nodes.

Return ONLY the JSON array — no prose, no markdown.
""".strip()


def _parse_nodes(raw: str) -> list[DAGNode]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    data = json.loads(raw)
    return [DAGNode(**item) for item in data]


def _normalize_statuses(node: DAGNode, original_map: dict[str, DAGNode]) -> None:
    if node.status == NodeStatus.mastered:
        return

    if node.status == NodeStatus.seen:
        return

    if not node.prerequisites:
        node.status = NodeStatus.available
        return

    if all(original_map.get(prereq, node).status == NodeStatus.mastered for prereq in node.prerequisites):
        node.status = NodeStatus.available
    else:
        node.status = NodeStatus.locked


async def regenerate_dag(
    current_dag: list[DAGNode],
    mem0_state: dict,
) -> list[DAGNode]:
    """
    R1: All input nodes present in output.
    R2: Every node with all prerequisites mastered → unlocked.
    R3: Prerequisite relationships unchanged.
    R4: id, title, description, success_criteria immutable.
    R5: mastered status never changed.
    R6: completed_at timestamps used to infer pace.
    R7: No new nodes invented.
    """
    dag_json = json.dumps([n.model_dump(mode="json") for n in current_dag], indent=2)
    mem0_json = json.dumps(mem0_state, indent=2)

    updated: list[DAGNode] = []
    try:
        response = await _client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Current DAG:\n{dag_json}\n\nmem0_state:\n{mem0_json}",
                },
            ],
        )

        raw = response.choices[0].message.content or "[]"
        updated = _parse_nodes(raw)
    except Exception as exc:
        log.warning("regenerate_dag LLM call failed, falling back to rule-based update: %s", exc)
        updated = [DAGNode(**n.model_dump()) for n in current_dag]

    # Belt-and-suspenders: enforce R1 (no nodes dropped), R3 (edges unchanged),
    # R4 (immutable fields), R5 (mastered never regresses)
    original_map = {n.id: n for n in current_dag}
    result: list[DAGNode] = []

    for node in updated:
        orig = original_map.get(node.id)
        if orig is None:
            continue  # R7: drop invented nodes

        # R4: restore immutable fields from original
        node.id = orig.id
        node.title = orig.title
        node.description = orig.description
        node.success_criteria = orig.success_criteria
        # R3: restore prerequisite edges from original
        node.prerequisites = orig.prerequisites
        # R5: mastered never regresses
        if orig.status == NodeStatus.mastered:
            node.status = NodeStatus.mastered
            node.completed_at = orig.completed_at

        _normalize_statuses(node, original_map)

        result.append(node)

    # R1: add any nodes the LLM dropped
    returned_ids = {n.id for n in result}
    for orig_node in current_dag:
        if orig_node.id not in returned_ids:
            result.append(orig_node)

    # R2: Programmatically unlock every node whose ALL prerequisites are mastered
    mastered_ids = {n.id for n in result if n.status == NodeStatus.mastered}
    for node in result:
        if node.status != NodeStatus.mastered:
            if not node.prerequisites or all(p in mastered_ids for p in node.prerequisites):
                node.status = NodeStatus.available

    await rocketride_client.publish(
        "dag.regenerated",
        {"nodes": [n.model_dump(mode="json") for n in result]},
    )

    return result


async def handle_content_classified(data: dict) -> None:
    """RocketRide subscriber: triggered by content.classified."""
    from backend.db import postgres
    from backend.memory import mem0_client

    session_id: str = data.get("session_id", "default")
    node_id: str = data.get("node_id", "")

    if node_id:
        await postgres.update_node_status(
            session_id, node_id, NodeStatus.seen,
            triggering_content=data.get("page_url"),
        )

    current_dag = await postgres.get_nodes(session_id)
    mem0_state = await mem0_client.read_full_state()
    updated = await regenerate_dag(current_dag, mem0_state)
    await postgres.upsert_nodes(session_id, updated)


async def handle_node_mastered(data: dict) -> None:
    """RocketRide subscriber: triggered by node.mastered (published by API layer)."""
    from backend.db import postgres
    from backend.memory import mem0_client

    session_id: str = data.get("session_id", "default")
    current_dag = await postgres.get_nodes(session_id)
    mem0_state = await mem0_client.read_full_state()
    updated = await regenerate_dag(current_dag, mem0_state)
    await postgres.upsert_nodes(session_id, updated)
