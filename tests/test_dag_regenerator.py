"""
Tests for backend/agents/dag_regenerator.py
Contract rules covered: R1, R2, R3, R4, R5, R7
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.dag import DAGNode, NodeStatus
from tests.conftest import LOCKED_NODE, MASTERED_NODE, SAMPLE_NODE


def _make_nodes(*raw_dicts) -> list[DAGNode]:
    return [DAGNode(**d) for d in raw_dicts]


def _mock_llm(nodes: list[dict]):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = json.dumps(nodes)
    return mock


MEM0_STATE = {
    "mastered_node_ids": ["react-components"],
    "completed_at": {"react-components": "2026-07-20T10:00:00Z"},
    "preferences": {},
}


@pytest.mark.asyncio
async def test_R1_no_nodes_dropped():
    """R1: All input nodes present in output — none dropped."""
    current = _make_nodes(SAMPLE_NODE, LOCKED_NODE, MASTERED_NODE)
    llm_output = [SAMPLE_NODE, LOCKED_NODE, MASTERED_NODE]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(llm_output))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    result_ids = {n.id for n in result}
    assert all(n.id in result_ids for n in current), "A node was dropped"


@pytest.mark.asyncio
async def test_R1_dropped_node_is_restored():
    """R1: If the LLM drops a node, the regenerator adds it back."""
    current = _make_nodes(SAMPLE_NODE, LOCKED_NODE, MASTERED_NODE)
    # LLM only returns 2 of 3
    llm_output = [SAMPLE_NODE, MASTERED_NODE]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(llm_output))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    result_ids = {n.id for n in result}
    assert LOCKED_NODE["id"] in result_ids, "Dropped node was not restored"


@pytest.mark.asyncio
async def test_R2_unlocks_nodes_whose_prerequisites_are_mastered():
    """R2: Nodes whose prerequisites are all mastered get unlocked."""
    mastered = {**MASTERED_NODE}
    locked = {**SAMPLE_NODE, "status": "locked", "prerequisites": ["react-components"]}
    current = _make_nodes(mastered, locked)
    llm_output = [mastered, {**locked, "status": "available"}]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(llm_output))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    hooks = next(n for n in result if n.id == "react-hooks")
    assert hooks.status == NodeStatus.available


@pytest.mark.asyncio
async def test_R3_prerequisite_edges_unchanged():
    """R3: Prerequisite relationships preserved exactly as in input."""
    current = _make_nodes(SAMPLE_NODE, LOCKED_NODE)
    # LLM attempts to add a prerequisite
    tampered = [{**SAMPLE_NODE, "prerequisites": ["extra-node"]}, LOCKED_NODE]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(tampered))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    hooks = next(n for n in result if n.id == "react-hooks")
    assert hooks.prerequisites == SAMPLE_NODE["prerequisites"], "Prerequisites were tampered with"


@pytest.mark.asyncio
async def test_R4_immutable_fields_unchanged():
    """R4: id, title, description, success_criteria never changed."""
    current = _make_nodes(SAMPLE_NODE)
    # LLM tries to change title and success_criteria
    tampered = [{
        **SAMPLE_NODE,
        "title": "HACKED TITLE",
        "description": "HACKED",
        "success_criteria": "HACKED CRITERIA",
    }]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(tampered))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    node = result[0]
    assert node.title == SAMPLE_NODE["title"]
    assert node.description == SAMPLE_NODE["description"]
    assert node.success_criteria == SAMPLE_NODE["success_criteria"]


@pytest.mark.asyncio
async def test_R5_mastered_status_never_regresses():
    """R5: A mastered node stays mastered even if LLM downgrades it."""
    current = _make_nodes(MASTERED_NODE)
    # LLM tries to set mastered node back to available
    tampered = [{**MASTERED_NODE, "status": "available"}]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(tampered))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    mastered = next(n for n in result if n.id == MASTERED_NODE["id"])
    assert mastered.status == NodeStatus.mastered, "Mastered node must not regress"


@pytest.mark.asyncio
async def test_R7_invented_nodes_dropped():
    """R7: Nodes not in the original DAG are silently dropped."""
    current = _make_nodes(SAMPLE_NODE)
    # LLM invents a new node
    invented = [{**SAMPLE_NODE}, {
        "id": "invented-node",
        "title": "Invented",
        "description": "...",
        "prerequisites": [],
        "difficulty": "beginner",
        "estimated_hours": 1,
        "success_criteria": "...",
        "status": "available",
        "resources": [],
        "completed_at": None,
        "triggering_content": None,
    }]

    with patch("backend.agents.dag_regenerator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_llm(invented))
        with patch("backend.agents.dag_regenerator.rocketride_client.publish", new_callable=AsyncMock):
            from backend.agents.dag_regenerator import regenerate_dag
            result = await regenerate_dag(current, MEM0_STATE)

    result_ids = {n.id for n in result}
    assert "invented-node" not in result_ids, "Invented node must be dropped"
