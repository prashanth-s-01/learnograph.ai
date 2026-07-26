<!-- pdd-story-prompts: prompts/regenerate_dag.prompt -->

# User Story: Mastered node unlocks dependants immediately

## Story

As a developer who just mastered "React Components",
I want the DAG to immediately unlock "React Hooks" and other direct dependants
(before any LLM regeneration runs),
so that my available next steps are visible the moment my comprehension check passes.

## Implementation note

`postgres.unlock_eligible_nodes()` runs in the /comprehension/score route immediately after
marking the node mastered and before publishing `node.mastered`. The WebSocket broadcast in
`_on_node_mastered` reads the already-correct DB state, so the frontend sees the unlocked nodes
without waiting for the LLM reordering step.
