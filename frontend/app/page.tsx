"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { ComprehensionResult, DAGNode } from "@/types/dag";
import { useWebSocket } from "@/hooks/useWebSocket";

const DAGCanvas = dynamic(() => import("@/components/DAGCanvas"), { ssr: false });
const VoiceCheck = dynamic(() => import("@/components/VoiceCheck"), { ssr: false });
const NodePanel = dynamic(() => import("@/components/NodePanel"), { ssr: false });

const SESSION_ID = "default";

export default function HomePage() {
  const { nodes, connected } = useWebSocket(SESSION_ID);
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [panelNode, setPanelNode] = useState<DAGNode | null>(null);
  const [checkNode, setCheckNode] = useState<DAGNode | null>(null);

  async function handleGenerate() {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      await fetch("/api/dag/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, session_id: SESSION_ID }),
      });
    } finally {
      setLoading(false);
    }
  }

  function handleNodeClick(node: DAGNode) {
    setPanelNode(node); // bug 6 fix: open detail panel instead of VoiceCheck directly
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Header */}
      <header style={{
        padding: "16px 24px", background: "#1e293b",
        borderBottom: "1px solid #334155", display: "flex",
        alignItems: "center", gap: 16, flexShrink: 0,
      }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: "#3b82f6", flexShrink: 0 }}>
          Learnograph
        </h1>
        <div style={{ display: "flex", gap: 8, flex: 1 }}>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            placeholder="Enter a developer topic (e.g. Learn React)"
            style={{
              flex: 1, padding: "8px 14px", borderRadius: 8,
              border: "1px solid #334155", background: "#0f172a",
              color: "#f1f5f9", fontSize: 14, outline: "none",
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "8px 20px", borderRadius: 8, border: "none",
              background: loading ? "#475569" : "#3b82f6", color: "#fff",
              cursor: loading ? "default" : "pointer", fontWeight: 600, fontSize: 14,
            }}
          >
            {loading ? "Generating…" : "Generate"}
          </button>
        </div>
        <div style={{ fontSize: 12, color: connected ? "#10b981" : "#ef4444", flexShrink: 0 }}>
          {connected ? "● Live" : "○ Connecting…"}
        </div>
      </header>

      {/* DAG Canvas — bug 1 fix: minHeight:0 so flex child doesn't collapse */}
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        {nodes.length === 0 ? (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: 12, color: "#475569",
          }}>
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4l3 3" />
            </svg>
            <p style={{ fontSize: 16 }}>Enter a topic above to generate your learning roadmap</p>
          </div>
        ) : (
          <DAGCanvas nodes={nodes} onNodeClick={handleNodeClick} />
        )}
      </div>

      {/* Legend */}
      {nodes.length > 0 && (
        <div style={{
          padding: "8px 24px", background: "#1e293b",
          borderTop: "1px solid #334155", display: "flex",
          gap: 20, fontSize: 12, color: "#94a3b8", flexShrink: 0,
        }}>
          {[
            ["#6b7280", "Locked"],
            ["#3b82f6", "Available — click to view"],
            ["#f59e0b", "Seen — click to review"],
            ["#10b981", "Mastered"],
          ].map(([color, label]) => (
            <span key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 10, height: 10, borderRadius: "50%",
                background: color, display: "inline-block",
              }} />
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Node detail panel — shows resources + start check button */}
      {panelNode && !checkNode && (
        <NodePanel
          node={panelNode}
          onStartCheck={() => {
            setCheckNode(panelNode);
            setPanelNode(null);
          }}
          onClose={() => setPanelNode(null)}
        />
      )}

      {/* Comprehension check modal */}
      {checkNode && (
        <VoiceCheck
          node={checkNode}
          sessionId={SESSION_ID}
          onResult={(r) => {
            if (r.verdict === "pass") setCheckNode(null);
          }}
          onClose={() => setCheckNode(null)}
        />
      )}
    </div>
  );
}
