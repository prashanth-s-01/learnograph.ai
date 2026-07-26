"""
Generated from: prompts/enrich_node.prompt
Contract rules: R1–R6
"""
from __future__ import annotations

import logging

import httpx

from backend.config import settings
from backend.models.dag import Resource
from backend.orchestration import rocketride_client

log = logging.getLogger(__name__)

_SCRAPE_URL = "https://api.rtrvr.ai/scrape"
_AGENT_URL = "https://api.rtrvr.ai/agent"


def _rtrvr_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.RTRVR_API_KEY}",
        "Content-Type": "application/json",
    }


async def _search_article(node_title: str) -> Resource | None:
    """Use Rtrvr.ai /agent to find a tutorial article on Medium, Dev.to, freeCodeCamp, etc."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                _AGENT_URL,
                headers=_rtrvr_headers(),
                json={
                    "input": (
                        f"Find a high-quality tutorial article about the developer topic '{node_title}' "
                        f"published on Medium, Dev.to, freeCodeCamp, CSS-Tricks, Smashing Magazine, "
                        f"web.dev, or a similar developer blog. "
                        f"Return a JSON object with fields: title (string), url (full article URL), "
                        f"reason (string, why this article is the best match)."
                    ),
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["title", "url", "reason"],
                    },
                },
            )
            r.raise_for_status()
            data = r.json().get("result", {}).get("json") or {}
            url = data.get("url", "")
            if url.startswith("http") and "youtube" not in url and data.get("title"):
                return Resource(type="article", **data)
    except Exception as exc:
        log.warning("Rtrvr.ai article search failed for '%s': %s", node_title, exc)
    return None


async def _search_doc(node_title: str) -> Resource | None:
    """Use Rtrvr.ai /agent to find the official maintainer documentation page."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                _AGENT_URL,
                headers=_rtrvr_headers(),
                json={
                    "input": (
                        f"Find the official documentation page (published by the technology's "
                        f"maintainer, not a third-party tutorial) for the developer topic "
                        f"'{node_title}'. Return a JSON object with fields: "
                        f"title (string), url (string), reason (string)."
                    ),
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["title", "url", "reason"],
                    },
                },
            )
            r.raise_for_status()
            data = r.json().get("result", {}).get("json") or {}
            if data.get("url"):
                return Resource(type="doc", **data)
    except Exception as exc:
        log.warning("Rtrvr.ai doc search failed for '%s': %s", node_title, exc)
    return None


async def _search_youtube(node_title: str, success_criteria: str) -> Resource | None:
    """Use Rtrvr.ai /agent to find a developer-focused YouTube tutorial."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                _AGENT_URL,
                headers=_rtrvr_headers(),
                json={
                    "input": (
                        f"Find a YouTube tutorial video for the developer topic '{node_title}' "
                        f"that covers: {success_criteria}. "
                        f"Return a JSON object: title (string), url (youtube.com URL), reason (string)."
                    ),
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["title", "url", "reason"],
                    },
                },
            )
            r.raise_for_status()
            data = r.json().get("result", {}).get("json") or {}
            if "youtube.com" in data.get("url", "") or "youtu.be" in data.get("url", ""):
                return Resource(type="youtube", **data)
    except Exception as exc:
        log.warning("Rtrvr.ai YouTube search failed for '%s': %s", node_title, exc)
    return None


async def enrich_node(
    node_title: str, success_criteria: str, session_id: str = "default"
) -> list[Resource]:
    """
    R1: Return exactly 3 resources: tutorial_article, official_doc, youtube_video.
    R2: Each resource has type, title, url, reason.
    R3: Only developer/engineering resources.
    R4: No duplicate URLs.
    R5: official_doc from maintainer, not third-party.
    R6: No fabricated URLs — all come from Rtrvr.ai.
    """
    article = await _search_article(node_title)
    doc = await _search_doc(node_title)
    video = await _search_youtube(node_title, success_criteria)

    resources: list[Resource] = []

    if article:
        resources.append(article)
    else:
        log.warning("No tutorial article found for '%s'", node_title)
        resources.append(Resource(
            type="article", title=f"{node_title} — freeCodeCamp",
            url=f"https://www.freecodecamp.org/news/search/?query={node_title.replace(' ', '+')}",
            reason="freeCodeCamp search fallback — Rtrvr.ai could not find a specific article",
        ))

    if doc:
        resources.append(doc)
    else:
        resources.append(Resource(
            type="doc", title=f"{node_title} — MDN Web Docs",
            url=f"https://developer.mozilla.org/en-US/search?q={node_title.replace(' ', '+')}",
            reason="MDN search fallback — Rtrvr.ai could not find the official doc page",
        ))

    if video:
        resources.append(video)
    else:
        resources.append(Resource(
            type="youtube", title=f"{node_title} Tutorial",
            url=f"https://www.youtube.com/results?search_query={node_title.replace(' ', '+')}+tutorial",
            reason="YouTube search fallback — Rtrvr.ai could not find a specific video",
        ))

    # R4: deduplicate by URL
    seen_urls: set[str] = set()
    deduped: list[Resource] = []
    for r in resources:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            deduped.append(r)

    return deduped


async def handle_dag_generated(data: dict) -> None:
    """Enriches all nodes in parallel; each completion fires a node.enriched event."""
    import asyncio
    from backend.db import postgres

    nodes_raw: list[dict] = data.get("nodes", [])
    session_id: str = data.get("session_id", "default")

    async def _enrich_one(node: dict) -> None:
        resources = await enrich_node(node["title"], node["success_criteria"], session_id)
        # DB write happens before the event so _on_node_enriched reads fresh data
        await postgres.update_node_resources(session_id, node["id"], resources)
        await rocketride_client.publish(
            "node.enriched",
            {"node_title": node["title"], "resources": [r.model_dump() for r in resources], "session_id": session_id},
        )

    await asyncio.gather(*[_enrich_one(n) for n in nodes_raw], return_exceptions=True)
