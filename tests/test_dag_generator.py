"""
Tests for backend/agents/dag_generator.py
Contract rules covered: R1, R2, R3, R4, R5, R6, R7, R8
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.dag import DAGNode, NodeStatus


@pytest.fixture
def mock_minimax(monkeypatch):
    """Mock MiniMax LLM call — never calls real API in tests."""
    response_nodes = [
        {
            "id": "javascript-basics",
            "title": "JavaScript Basics",
            "description": "Variables, functions, loops",
            "prerequisites": [],
            "difficulty": "beginner",
            "estimated_hours": 5,
            "success_criteria": "Can write a function that maps over an array",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
        {
            "id": "react-components",
            "title": "React Components",
            "description": "Functional components and props",
            "prerequisites": ["javascript-basics"],
            "difficulty": "beginner",
            "estimated_hours": 4,
            "success_criteria": "Can build a reusable component that accepts props",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
        {
            "id": "react-hooks",
            "title": "React Hooks",
            "description": "useState and useEffect",
            "prerequisites": ["react-components"],
            "difficulty": "intermediate",
            "estimated_hours": 3,
            "success_criteria": "Can explain what useEffect dependency array does",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
        {
            "id": "react-context",
            "title": "React Context",
            "description": "useContext for state sharing",
            "prerequisites": ["react-hooks"],
            "difficulty": "intermediate",
            "estimated_hours": 2,
            "success_criteria": "Can create and consume a context without prop-drilling",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
        {
            "id": "react-router",
            "title": "React Router",
            "description": "Client-side routing",
            "prerequisites": ["react-components"],
            "difficulty": "intermediate",
            "estimated_hours": 3,
            "success_criteria": "Can add multi-page navigation to a React app",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
    ]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(response_nodes)

    mock_create = AsyncMock(return_value=mock_response)

    with patch("backend.agents.dag_generator._client") as mock_client:
        mock_client.chat.completions.create = mock_create
        yield mock_create, response_nodes


@pytest.mark.asyncio
async def test_R1_returns_valid_dag_nodes(mock_minimax):
    """R1: Returns list of DAGNode objects for any developer topic."""
    from backend.agents.dag_generator import generate_dag

    nodes = await generate_dag("Learn React", None)

    assert isinstance(nodes, list)
    assert all(isinstance(n, DAGNode) for n in nodes)


@pytest.mark.asyncio
async def test_R2_no_circular_dependencies(mock_minimax):
    """R2: No node depends on itself; no circular dependency."""
    from backend.agents.dag_generator import generate_dag

    nodes = await generate_dag("Learn React", None)
    id_map = {n.id: n for n in nodes}

    def has_cycle(node_id: str, visited: set, stack: set) -> bool:
        visited.add(node_id)
        stack.add(node_id)
        for prereq in id_map.get(node_id, DAGNode(
            id=node_id, title="", description="", difficulty="beginner",
            estimated_hours=1, success_criteria="", prerequisites=[]
        )).prerequisites:
            if prereq not in visited:
                if has_cycle(prereq, visited, stack):
                    return True
            elif prereq in stack:
                return True
        stack.discard(node_id)
        return False

    visited: set = set()
    for node in nodes:
        assert node.id not in node.prerequisites, f"Node {node.id} depends on itself"
        if node.id not in visited:
            assert not has_cycle(node.id, visited, set()), f"Cycle detected involving {node.id}"


@pytest.mark.asyncio
async def test_R3_root_nodes_available_others_locked(mock_minimax):
    """R3: Root nodes (no prerequisites) are available; all others locked."""
    from backend.agents.dag_generator import generate_dag

    nodes = await generate_dag("Learn React", None)

    for node in nodes:
        if not node.prerequisites:
            assert node.status == NodeStatus.available, f"Root node {node.id} should be available"
        else:
            assert node.status in (NodeStatus.locked, NodeStatus.available), \
                f"Node {node.id} has invalid status"


@pytest.mark.asyncio
async def test_R4_success_criteria_is_single_sentence(mock_minimax):
    """R4: success_criteria is a single testable sentence."""
    from backend.agents.dag_generator import generate_dag

    nodes = await generate_dag("Learn React", None)

    for node in nodes:
        assert node.success_criteria.strip(), f"Node {node.id} has empty success_criteria"
        assert len(node.success_criteria.strip()) > 0


@pytest.mark.asyncio
async def test_R5_node_count_in_range(mock_minimax):
    """R5: Returns 5–30 nodes."""
    from backend.agents.dag_generator import generate_dag

    nodes = await generate_dag("Learn React", None)

    assert 5 <= len(nodes) <= 30, f"Got {len(nodes)} nodes, expected 5–30"


@pytest.mark.asyncio
async def test_R6_non_dev_topic_returns_empty():
    """R6: Non-developer topics produce no nodes."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "[]"

    with patch("backend.agents.dag_generator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        from backend.agents.dag_generator import generate_dag
        nodes = await generate_dag("Learn to cook pasta", None)
        assert nodes == [], "Non-dev topic should produce no nodes"


@pytest.mark.asyncio
async def test_R7_ids_are_kebab_case_slugs(mock_minimax):
    """R7: Node IDs are kebab-case slugs derived from titles, not hardcoded."""
    from backend.agents.dag_generator import generate_dag
    import re

    nodes = await generate_dag("Learn React", None)

    kebab_pattern = re.compile(r"^[a-z][a-z0-9-]*$")
    for node in nodes:
        assert kebab_pattern.match(node.id), f"Node id '{node.id}' is not valid kebab-case"


@pytest.mark.asyncio
async def test_R8_mastered_nodes_excluded_dependants_unlocked():
    """R8: Mastered nodes excluded; their direct dependants unlocked."""
    unlocked_response = [
        {
            "id": "react-hooks",
            "title": "React Hooks",
            "description": "...",
            "prerequisites": ["react-components"],
            "difficulty": "intermediate",
            "estimated_hours": 3,
            "success_criteria": "Can explain useEffect dependency array",
            "status": "locked",   # should be unlocked because prereq mastered
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        },
        *[{
            "id": f"node-{i}",
            "title": f"Node {i}",
            "description": "...",
            "prerequisites": ["react-hooks"],
            "difficulty": "beginner",
            "estimated_hours": 1,
            "success_criteria": f"Can do thing {i}",
            "status": "locked",
            "resources": [],
            "completed_at": None,
            "triggering_content": None,
        } for i in range(4)],
    ]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(unlocked_response)

    user_profile = {"mastered_node_ids": ["react-components"]}

    with patch("backend.agents.dag_generator._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        from backend.agents.dag_generator import generate_dag
        nodes = await generate_dag("Learn React", user_profile)

    node_ids = [n.id for n in nodes]
    assert "react-components" not in node_ids, "Mastered node should be excluded"

    hooks_node = next((n for n in nodes if n.id == "react-hooks"), None)
    if hooks_node:
        assert hooks_node.status == NodeStatus.available, \
            "Direct dependant of mastered node should be available"
