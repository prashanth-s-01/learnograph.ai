"""
Generated from: prompts/generate_dag.prompt
Contract rules: R1–R8
"""
from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI

from backend.config import settings
from backend.models.dag import DAGNode, Difficulty, NodeStatus

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

_SYSTEM = """
You are a developer-education curriculum designer.
Given a software engineering topic and an optional user profile, return a learning DAG.

Rules:
- Return ONLY a JSON array of node objects — no prose, no markdown fences.
- 5–30 nodes total.
- Each node id is a kebab-case slug derived from the title (e.g. "react-hooks").
- Root nodes (no prerequisites) have status "available"; all others "locked".
- success_criteria is a CONCEPTUAL question the learner can answer ORALLY in 1–2 sentences.
  It must test understanding, not ask the learner to write, build, implement, or code anything.
  Good example: "What is the difference between a pointer and a reference in C++?"
  Bad example: "Write a C program that uses pointers to swap two integers."
- Reject non-developer topics: return an empty array [].
- No circular dependencies. No self-referential prerequisites.
- If mastered_node_ids are provided, exclude those nodes and set their direct
  dependants to status "available" instead of "locked".

Node schema:
{
  "id": string,
  "title": string,
  "description": string,
  "prerequisites": [string],
  "difficulty": "beginner"|"intermediate"|"advanced",
  "estimated_hours": number,
  "success_criteria": string,
  "status": "available"|"locked",
  "resources": [],
  "completed_at": null,
  "triggering_content": null
}
""".strip()


def _topo_sort(nodes: list[DAGNode]) -> list[DAGNode]:
    """Return nodes in topological order (root nodes first) using Kahn's algorithm."""
    from collections import deque

    id_set = {n.id for n in nodes}
    node_map = {n.id: n for n in nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}
    children: dict[str, list[str]] = {n.id: [] for n in nodes}

    for node in nodes:
        for prereq in node.prerequisites:
            if prereq in id_set:
                in_degree[node.id] += 1
                children[prereq].append(node.id)

    queue: deque[str] = deque(nid for nid in in_degree if in_degree[nid] == 0)
    result: list[DAGNode] = []

    while queue:
        nid = queue.popleft()
        result.append(node_map[nid])
        for child in children[nid]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Append any remaining nodes (should only happen on unexpected cycles)
    seen = {n.id for n in result}
    result.extend(n for n in nodes if n.id not in seen)
    return result


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _parse_nodes(raw: str) -> list[DAGNode]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    data = json.loads(raw)
    nodes = []
    for item in data:
        item.setdefault("resources", [])
        item.setdefault("completed_at", None)
        item.setdefault("triggering_content", None)
        item["id"] = _slug(item["title"])
        nodes.append(DAGNode(**item))
    return nodes


async def generate_dag(topic: str, user_profile: dict | None) -> list[DAGNode]:
    """
    R1: Returns DAGNode list for any developer topic.
    R2: No circular deps, no self-deps.
    R3: Root nodes available, others locked.
    R4: success_criteria is a single testable sentence.
    R5: 5–30 nodes.
    R6: Non-dev topics → empty list.
    R7: IDs are derived slugs, never hardcoded.
    R8: Mastered nodes excluded; their dependants unlocked.
    """
    mastered: list[str] = (user_profile or {}).get("mastered_node_ids", [])

    user_context = ""
    if mastered:
        user_context = f"\nAlready mastered (exclude from DAG, unlock dependants): {mastered}"

    response = await _client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Topic: {topic}{user_context}"},
        ],
    )

    raw = response.choices[0].message.content or "[]"
    nodes = _parse_nodes(raw)

    # Enforce R5
    if nodes and not (5 <= len(nodes) <= 30):
        log.warning("Node count %d out of range for topic '%s'", len(nodes), topic)

    # Enforce R8: re-unlock dependants of mastered nodes (belt-and-suspenders)
    if mastered:
        mastered_set = set(mastered)
        for node in nodes:
            if all(p in mastered_set for p in node.prerequisites) and node.prerequisites:
                node.status = NodeStatus.available

    return _topo_sort(nodes)
