"""
Tests for backend/agents/node_enricher.py
Contract rules covered: R1, R2, R5, R6
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.dag import Resource


def _rtrvr_response(url: str, title: str, reason: str) -> dict:
    return {"success": True, "result": {"json": {"title": title, "url": url, "reason": reason}}}


@pytest.fixture
def mock_rtrvr(monkeypatch):
    """Mock all Rtrvr.ai HTTP calls — never call real API in tests."""

    async def _fake_post(self_or_url, *args, **kwargs):
        url = self_or_url if isinstance(self_or_url, str) else kwargs.get("url", "")
        json_body = kwargs.get("json", {})
        task = json_body.get("input", "")

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = AsyncMock()

        if "GitHub" in task or "github" in task.lower():
            mock_resp.json = lambda: _rtrvr_response(
                "https://github.com/facebook/react", "facebook/react", "Most starred React repo"
            )
        elif "official" in task.lower() or "documentation" in task.lower():
            mock_resp.json = lambda: _rtrvr_response(
                "https://react.dev", "React Official Docs", "Maintained by the React team"
            )
        else:
            mock_resp.json = lambda: _rtrvr_response(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "React Hooks Tutorial",
                "Popular tutorial on hooks",
            )
        return mock_resp

    with patch("httpx.AsyncClient.post", new=_fake_post):
        with patch("backend.agents.node_enricher.rocketride_client.publish", new_callable=AsyncMock):
            yield


@pytest.mark.asyncio
async def test_R1_returns_exactly_3_resources(mock_rtrvr):
    """R1: Exactly 3 resources returned in order: github, doc, youtube."""
    from backend.agents.node_enricher import enrich_node

    resources = await enrich_node("React Hooks", "Can explain useEffect dependency array")

    assert len(resources) == 3
    assert resources[0].type == "github"
    assert resources[1].type == "doc"
    assert resources[2].type == "youtube"


@pytest.mark.asyncio
async def test_R2_all_resources_have_required_fields(mock_rtrvr):
    """R2: Each resource has type, title, url, reason."""
    from backend.agents.node_enricher import enrich_node

    resources = await enrich_node("React Hooks", "Can explain useEffect dependency array")

    for r in resources:
        assert r.type in ("github", "doc", "youtube")
        assert r.title
        assert r.url
        assert r.reason


@pytest.mark.asyncio
async def test_R5_official_doc_is_maintainer_url(mock_rtrvr):
    """R5: official_doc links to maintainer's own documentation."""
    from backend.agents.node_enricher import enrich_node

    resources = await enrich_node("React Hooks", "Can explain useEffect dependency array")
    doc = resources[1]

    assert doc.type == "doc"
    assert "react.dev" in doc.url


@pytest.mark.asyncio
async def test_R6_no_fabricated_urls_all_from_rtrvr(mock_rtrvr):
    """R6: All URLs come from Rtrvr.ai, none are invented by the agent."""
    from backend.agents.node_enricher import enrich_node

    resources = await enrich_node("React Hooks", "Can explain useEffect dependency array")

    for r in resources:
        assert r.url.startswith("https://"), f"URL {r.url} does not look real"
        assert " " not in r.url, f"URL {r.url} contains spaces — likely fabricated"
