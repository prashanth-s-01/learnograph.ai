from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class NodeStatus(str, Enum):
    locked = "locked"
    available = "available"
    seen = "seen"
    mastered = "mastered"


class Resource(BaseModel):
    type: Literal["github", "doc", "youtube"]
    title: str
    url: str
    reason: str


class DAGNode(BaseModel):
    id: str = Field(..., description="kebab-case slug derived from title")
    title: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)
    difficulty: Difficulty
    estimated_hours: float
    success_criteria: str
    status: NodeStatus = NodeStatus.locked
    resources: list[Resource] = Field(default_factory=list)
    completed_at: datetime | None = None
    triggering_content: str | None = None


class ComprehensionResult(BaseModel):
    verdict: Literal["pass", "needs_review"]
    feedback: str = Field(..., description="exactly one sentence of forward-pointing feedback")


class DAGGenerateRequest(BaseModel):
    topic: str
    session_id: str = "default"


class ClassifyRequest(BaseModel):
    page_url: str
    session_id: str = "default"
    page_text: str | None = None  # provided by Chrome extension; skips Rtrvr.ai when present


class ComprehensionRequest(BaseModel):
    node_id: str
    success_criteria: str
    transcribed_answer: str
    session_id: str = "default"


class RegenerateRequest(BaseModel):
    session_id: str = "default"
