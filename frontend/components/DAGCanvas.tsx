"use client";

import { useCallback, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { DAGNode } from "@/types/dag";

const STATUS_COLOR: Record<string, string> = {
  locked: "#6b7280",
  available: "#3b82f6",
  seen: "#f59e0b",
  mastered: "#10b981",
};

function DAGNodeCard({ data }: NodeProps) {
  const node = data.node as DAGNode;
  const color = STATUS_COLOR[node.status] ?? "#6b7280";

  return (
    <div
      style={{
        border: `2px solid ${color}`,
        borderRadius: 8,
        padding: "10px 14px",
        background: "#1e293b",
        color: "#f1f5f9",
        minWidth: 180,
        maxWidth: 240,
        fontSize: 13,
        boxShadow: node.status === "seen" ? `0 0 12px ${color}` : undefined,
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 700, marginBottom: 4, color }}>{node.title}</div>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 6 }}>{node.description}</div>
      <div
        style={{
          fontSize: 10,
          background: color + "33",
          borderRadius: 4,
          padding: "2px 6px",
          display: "inline-block",
          textTransform: "uppercase",
          letterSpacing: 1,
          color,
        }}
      >
        {node.status}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { dagNode: DAGNodeCard };

interface Props {
  nodes: DAGNode[];
  onNodeClick?: (node: DAGNode) => void;
}

export default function DAGCanvas({ nodes, onNodeClick }: Props) {
  const rfNodes: Node[] = useMemo(
    () =>
      nodes.map((n, i) => ({
        id: n.id,
        type: "dagNode",
        position: { x: (i % 4) * 280, y: Math.floor(i / 4) * 180 },
        data: { node: n },
      })),
    [nodes]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      nodes.flatMap((n) =>
        n.prerequisites.map((prereq) => ({
          id: `${prereq}->${n.id}`,
          source: prereq,
          target: n.id,
          animated: n.status === "available",
          style: { stroke: STATUS_COLOR[n.status] ?? "#6b7280" },
        }))
      ),
    [nodes]
  );

  const handleClick = useCallback(
    (_: React.MouseEvent, rfNode: Node) => {
      const original = nodes.find((n) => n.id === rfNode.id);
      if (original) onNodeClick?.(original);
    },
    [nodes, onNodeClick]
  );

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleClick}
        fitView
      >
        <Background color="#334155" gap={24} />
        <Controls />
        <MiniMap nodeColor={(n) => STATUS_COLOR[(n.data?.node as DAGNode)?.status] ?? "#6b7280"} />
      </ReactFlow>
    </div>
  );
}
