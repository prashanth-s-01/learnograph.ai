<!-- pdd-story-prompts: prompts/comprehension_check.prompt, prompts/regenerate_dag.prompt -->

# User Story: UI updates immediately after a comprehension pass

## Story

As a developer who just passed the comprehension check for "React Components",
I want my learning map to reflect the new "mastered" status and newly unlocked nodes
within a second — not after a 10–30 second LLM wait,
so that the learning loop feels responsive and satisfying.

## Implementation note

Two-pronged approach:
1. **Frontend**: `page.tsx` calls `refresh()` immediately on "pass" verdict. `refresh()` is an
   HTTP fetch to GET /api/dag/{sessionId} that bypasses the WebSocket pipeline entirely.
2. **Backend**: `_on_node_mastered` in main.py broadcasts the current DB state (already correct
   because `unlock_eligible_nodes` ran before publish) to all WebSocket clients before starting
   the LLM regeneration as an `asyncio.create_task()`. The LLM reordering then arrives as a
   second `dag.regenerated` update when it completes in the background.
