<!-- pdd-story-prompts: prompts/resource_visit.prompt -->

# User Story: Visiting a resource transitions node to "seen"

## Story

As a developer who clicks a tutorial article link on the "React Hooks" node,
I want the node to change from "Available" to "Seen" in my learning map,
so that I can see at a glance which topics I have started engaging with.

## Implementation note

The Chrome extension recognises when the user navigates to a URL that matches a resource URL
for an active node (via GET /dag/resources/{session_id}) and POSTs to /resource-visit.
`postgres.record_resource_visit()` atomically transitions the node from "available" → "seen"
on the first visit. Subsequent visits are recorded but do not change the status. The WebSocket
broadcast fires immediately so the frontend colour changes without a manual refresh.
