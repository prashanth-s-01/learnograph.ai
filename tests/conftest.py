"""Shared fixtures for all agent tests."""
import pytest

# Base DAGNode fixture conforming to the shared schema in context/project_preamble.prompt
SAMPLE_NODE = {
    "id": "react-hooks",
    "title": "React Hooks",
    "description": "useState, useEffect, useContext",
    "prerequisites": ["react-components"],
    "difficulty": "intermediate",
    "estimated_hours": 3.0,
    "success_criteria": "Can explain what useEffect's dependency array does and why it matters",
    "status": "available",
    "resources": [],
    "completed_at": None,
    "triggering_content": None,
}

LOCKED_NODE = {**SAMPLE_NODE, "id": "advanced-react", "title": "Advanced React",
               "prerequisites": ["react-hooks"], "status": "locked"}

MASTERED_NODE = {**SAMPLE_NODE, "id": "react-components", "title": "React Components",
                 "prerequisites": [], "status": "mastered", "difficulty": "beginner"}
