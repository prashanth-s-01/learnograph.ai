<!-- pdd-story-prompts: prompts/regenerate_dag.prompt -->

# User Story: Seen nodes cannot regress to available

## Story

As a developer who has visited a resource for "React Hooks" (node is "seen"),
I want the node to stay "seen" after every DAG regeneration,
so that my engagement history is never silently wiped.

## Implementation note

`dag_regenerator._normalize_statuses()` returns early for both "mastered" and "seen" nodes without
changing their status. The final R2 programmatic pass in `regenerate_dag()` also explicitly skips
nodes whose status is "mastered" or "seen" when applying the unlock rule. This means a seen node
will never be set back to "available" by any regeneration, even if the LLM incorrectly suggests it.
