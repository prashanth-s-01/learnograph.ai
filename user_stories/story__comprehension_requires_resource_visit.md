<!-- pdd-story-prompts: prompts/comprehension_check.prompt -->

# User Story: Comprehension check requires prior resource visit

## Story

As a developer trying to take the comprehension check for "React Hooks" without reading anything,
I want the system to block the attempt and tell me I must review at least one resource first,
so that the oral check tests genuine understanding rather than guessing.

## Implementation note

The /comprehension/score route calls `postgres.has_visited_any_resource(session_id, node_id)`
before calling `score_comprehension`. If no visit is recorded it returns HTTP 403 with the message
"Must review at least one resource before attempting the comprehension check". The resource_visit
route records visits when the Chrome extension or NodePanel detects a resource URL navigation.
