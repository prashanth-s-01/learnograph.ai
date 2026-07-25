"""
Generated from: prompts/classify_content.prompt
Contract rules: R1–R6
"""
from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from backend.config import settings
from backend.models.dag import DAGNode
from backend.orchestration import rocketride_client

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

_SYSTEM = """
You are a content-to-learning-node classifier.

Given scraped page text and a list of available learning nodes, return ONLY the single
best-matching node_id as a plain string — or the literal null if there is no confident match.

Rules:
- A confident match means the page text SUBSTANTIVELY covers the concept in the node's
  success_criteria, not merely mentions the keyword.
- Never return a node whose status is "locked".
- Never return more than one node_id.
- Never invent node IDs; only use IDs from the provided list.
- Return exactly: a node_id string, or the word null.
""".strip()


async def classify_content(
    page_text: str,
    page_url: str,
    available_nodes: list[dict],
) -> str | None:
    """
    R1: Return node_id only for substantive coverage.
    R2: Return null when no confident match.
    R3: Never match locked nodes.
    R4: Match on concept coverage, not keyword presence alone.
    R5: One match or null, never a list.
    R6: Only IDs from available_nodes.
    """
    if not page_text.strip() or not available_nodes:
        return None

    node_catalog = json.dumps(
        [
            {"id": n["id"], "title": n["title"], "success_criteria": n["success_criteria"]}
            for n in available_nodes
        ],
        indent=2,
    )

    response = await _client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Available nodes:\n{node_catalog}\n\n"
                    f"Page URL: {page_url}\n\n"
                    f"Page text (first 8000 chars):\n{page_text[:8000]}"
                ),
            },
        ],
    )

    raw = (response.choices[0].message.content or "null").strip().strip('"').strip("'")

    if raw.lower() == "null" or not raw:
        return None

    # R6: Guard — only return IDs that exist in the provided list
    valid_ids = {n["id"] for n in available_nodes}
    if raw not in valid_ids:
        log.warning("Classifier returned unknown node_id '%s' — returning null", raw)
        return None

    # Publish → triggers regenerate_dag via RocketRide pipeline
    await rocketride_client.publish(
        "content.classified",
        {"node_id": raw, "page_url": page_url},
    )

    return raw
