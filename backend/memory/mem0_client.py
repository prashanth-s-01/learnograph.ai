from __future__ import annotations

from mem0 import MemoryClient

from backend.config import settings

_client: MemoryClient | None = None


def _get_client() -> MemoryClient:
    global _client
    if _client is None:
        _client = MemoryClient(api_key=settings.MEM0_API_KEY)
    return _client


def read_user_profile(user_id: str = settings.MEM0_USER_ID) -> dict:
    """Return a snapshot of the user's learning state from mem0 (read-only)."""
    client = _get_client()
    memories = client.search("learning progress mastered nodes pace preferences", user_id=user_id)
    mastered_ids: list[str] = []
    completed_at: dict[str, str] = {}
    preferences: dict[str, str] = {}

    for mem in memories:
        text: str = mem.get("memory", "")
        if text.startswith("mastered:"):
            node_id = text.split(":", 1)[1].strip()
            mastered_ids.append(node_id)
        elif text.startswith("completed_at:"):
            parts = text.split(":", 2)
            if len(parts) == 3:
                completed_at[parts[1].strip()] = parts[2].strip()
        elif text.startswith("preference:"):
            parts = text.split(":", 2)
            if len(parts) == 3:
                preferences[parts[1].strip()] = parts[2].strip()

    return {
        "mastered_node_ids": mastered_ids,
        "completed_at": completed_at,
        "preferences": preferences,
        "user_id": user_id,
    }


def read_full_state(user_id: str = settings.MEM0_USER_ID) -> dict:
    """Return full mem0 state including pace signals for regenerate_dag."""
    return read_user_profile(user_id)


def record_node_mastered(
    node_id: str,
    completed_at: str,
    user_id: str = settings.MEM0_USER_ID,
) -> None:
    """Write a mastered-node memory entry. Called by the API layer only, never by agents."""
    client = _get_client()
    client.add(
        [
            {"role": "user", "content": f"mastered:{node_id}"},
            {"role": "user", "content": f"completed_at:{node_id}:{completed_at}"},
        ],
        user_id=user_id,
    )
