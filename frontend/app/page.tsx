"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { ComprehensionResult, DAGNode } from "@/types/dag";
import { useWebSocket } from "@/hooks/useWebSocket";

const DAGCanvas = dynamic(() => import("@/components/DAGCanvas"), { ssr: false });
const VoiceCheck = dynamic(() => import("@/components/VoiceCheck"), { ssr: false });
const NodePanel = dynamic(() => import("@/components/NodePanel"), { ssr: false });

const SESSION_ID = "default";

export default function HomePage() {
  const { nodes, connected, refresh } = useWebSocket(SESSION_ID);
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [panelNode, setPanelNode] = useState<DAGNode | null>(null);
  const [checkNode, setCheckNode] = useState<DAGNode | null>(null);

  // Keep panelNode in sync with live WebSocket updates (so resources appear as they load)
  useEffect(() => {
    if (panelNode) {
      const updated = nodes.find((n) => n.id === panelNode.id);
      if (updated) setPanelNode(updated);
    }
  }, [nodes]);

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
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "var(--bg)" }}>
      {/* Header */}
      <header style={{
        padding: "16px 24px",
        background: "rgba(255,255,255,0.82)",
        borderBottom: "1px solid rgba(148,163,184,0.2)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        flexShrink: 0,
        backdropFilter: "blur(16px)",
        boxShadow: "0 1px 0 rgba(15,23,42,0.03)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 12,
            background: "linear-gradient(135deg, #2563eb, #60a5fa)",
            boxShadow: "0 10px 24px rgba(37,99,235,0.18)",
          }} />
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", lineHeight: 1.1 }}>
              Learnograph
            </h1>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
              Minimal learning map
            </div>
          </div>
        </div>
        <div style={{
          display: "flex",
          gap: 10,
          flex: 1,
          maxWidth: 760,
          margin: "0 auto",
          background: "rgba(241,245,249,0.9)",
          border: "1px solid rgba(148,163,184,0.18)",
          borderRadius: 16,
          padding: 8,
          boxShadow: "0 10px 30px rgba(15,23,42,0.04)",
        }}>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            placeholder="Enter a developer topic (e.g. Learn React)"
            style={{
              flex: 1,
              padding: "11px 14px",
              borderRadius: 12,
              border: "1px solid rgba(148,163,184,0.18)",
              background: "rgba(255,255,255,0.94)",
              color: "#0f172a",
              fontSize: 14,
              outline: "none",
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "11px 18px",
              borderRadius: 12,
              border: "1px solid transparent",
              background: loading ? "#cbd5e1" : "linear-gradient(135deg, #2563eb, #3b82f6)",
              color: loading ? "#475569" : "#fff",
              cursor: loading ? "default" : "pointer",
              fontWeight: 600,
              fontSize: 14,
              boxShadow: loading ? "none" : "0 10px 24px rgba(37,99,235,0.14)",
            }}
          >
            {loading ? "Generating…" : "Generate"}
          </button>
        </div>
        <div style={{
          fontSize: 12,
          color: connected ? "#059669" : "#dc2626",
          flexShrink: 0,
          padding: "8px 12px",
          borderRadius: 999,
          background: connected ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.08)",
          border: connected ? "1px solid rgba(16,185,129,0.16)" : "1px solid rgba(239,68,68,0.14)",
        }}>
          {connected ? "● Live" : "○ Connecting…"}
        </div>
      </header>

      {/* DAG Canvas — bug 1 fix: minHeight:0 so flex child doesn't collapse */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", background: "var(--bg)" }}>
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
          padding: "10px 24px",
          background: "rgba(255,255,255,0.78)",
          borderTop: "1px solid rgba(148,163,184,0.2)",
          display: "flex",
          gap: 20,
          fontSize: 12,
          color: "#64748b",
          flexShrink: 0,
          backdropFilter: "blur(16px)",
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
            if (r.verdict === "pass") {
              setCheckNode(null);
              // Fetch fresh node state immediately — don't wait for the WS pipeline
              refresh();
            }
          }}
          onClose={() => setCheckNode(null)}
        />
      )}
    </div>
  );
}
