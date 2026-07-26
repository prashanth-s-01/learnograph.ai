<!-- pdd-story-prompts: prompts/generate_dag.prompt -->

# User Story: DAG nodes arrive in topological order

## Story

As a developer viewing my learning roadmap,
I want root nodes (no prerequisites) to appear at the top and each node to appear only after
all its prerequisites,
so that the visual layout makes intuitive reading sense left-to-right and top-to-bottom.

## Implementation note

`dag_generator._topo_sort()` applies Kahn's algorithm before the list is returned. The frontend
`computeDepths()` function in DAGCanvas.tsx independently calculates visual depth for layout,
placing nodes at y = depth × 200. Together these guarantee root nodes are first in storage order
and topmost in the visual layout.
