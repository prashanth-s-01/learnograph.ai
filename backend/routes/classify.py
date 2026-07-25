import httpx
from fastapi import APIRouter, HTTPException

from backend.agents import content_classifier
from backend.config import settings
from backend.db import postgres
from backend.models.dag import ClassifyRequest

router = APIRouter(prefix="/classify", tags=["classify"])

_RTRVR_SCRAPE = "https://api.rtrvr.ai/scrape"


async def _scrape_page_text(url: str) -> str:
    """Fallback: call Rtrvr.ai to extract clean page text when the extension didn't send it."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            _RTRVR_SCRAPE,
            headers={
                "Authorization": f"Bearer {settings.RTRVR_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"urls": [url], "response": {"inlineOutputMaxBytes": 1048576}},
        )
        r.raise_for_status()
        tabs = r.json().get("tabs", [])
        return tabs[0]["content"] if tabs else ""


@router.post("")
async def classify(req: ClassifyRequest) -> dict:
    # Use page_text from the Chrome extension if available; fall back to Rtrvr.ai scrape
    if req.page_text and req.page_text.strip():
        page_text = req.page_text
    else:
        try:
            page_text = await _scrape_page_text(req.page_url)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Rtrvr.ai scrape failed: {exc}")

    available = await postgres.get_available_nodes(req.session_id)
    if not available:
        return {"matched_node_id": None}

    matched_id = await content_classifier.classify_content(
        page_text,
        req.page_url,
        [n.model_dump(mode="json") for n in available],
    )

    return {"matched_node_id": matched_id}
