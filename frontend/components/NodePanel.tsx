"use client";

import type { DAGNode } from "@/types/dag";

const STATUS_COLOR: Record<string, string> = {
  locked: "#6b7280",
  available: "#3b82f6",
  seen: "#f59e0b",
  mastered: "#10b981",
};

const RESOURCE_ICON: Record<string, string> = {
  github: "🐙",
  doc: "📖",
  youtube: "▶️",
};

const RESOURCE_LABEL: Record<string, string> = {
  github: "GitHub Repository",
  doc: "Official Documentation",
  youtube: "YouTube Tutorial",
};

interface Props {
  node: DAGNode;
  onStartCheck: () => void;
  onClose: () => void;
}

export default function NodePanel({ node, onStartCheck, onClose }: Props) {
  const color = STATUS_COLOR[node.status] ?? "#6b7280";
  const canCheck = node.status === "available" || node.status === "seen";

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.72)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: "#1e293b", borderRadius: 14, padding: 32, maxWidth: 540,
        width: "90%", color: "#f1f5f9", position: "relative",
        maxHeight: "88vh", overflowY: "auto",
      }}>
        {/* Close */}
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 14, right: 14, background: "none",
            border: "none", color: "#64748b", fontSize: 22, cursor: "pointer",
            lineHeight: 1, padding: 4, borderRadius: 4,
          }}
          title="Close"
        >
          ✕
        </button>

        {/* Status badge */}
        <div style={{
          display: "inline-block", fontSize: 10, background: color + "22",
          border: `1px solid ${color}55`, borderRadius: 4, padding: "2px 8px",
          textTransform: "uppercase", letterSpacing: 1, color, marginBottom: 10,
        }}>
          {node.status}
        </div>

        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6, color, lineHeight: 1.3 }}>
          {node.title}
        </h2>

        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#64748b", marginBottom: 18 }}>
          <span>🎯 {node.difficulty}</span>
          <span>⏱ {node.estimated_hours}h estimated</span>
          {node.prerequisites.length > 0 && (
            <span>🔗 {node.prerequisites.length} prerequisite{node.prerequisites.length > 1 ? "s" : ""}</span>
          )}
        </div>

        <p style={{ fontSize: 14, lineHeight: 1.75, color: "#cbd5e1", marginBottom: 22 }}>
          {node.description}
        </p>

        {/* Success criteria */}
        <div style={{
          background: "#0f172a", borderRadius: 8, padding: "12px 16px",
          marginBottom: 24, borderLeft: "3px solid #3b82f6",
        }}>
          <strong style={{
            fontSize: 11, color: "#64748b", display: "block",
            marginBottom: 6, letterSpacing: 1, textTransform: "uppercase",
          }}>
            Success Criteria
          </strong>
          <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>{node.success_criteria}</p>
        </div>

        {/* Resources */}
        <strong style={{
          fontSize: 11, color: "#64748b", display: "block",
          marginBottom: 10, letterSpacing: 1, textTransform: "uppercase",
        }}>
          Learning Resources
        </strong>

        {node.resources.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
            {node.resources.map((r, i) => (
              <a
                key={i}
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex", alignItems: "flex-start", gap: 12,
                  background: "#0f172a", borderRadius: 8, padding: "12px 14px",
                  textDecoration: "none", color: "#f1f5f9",
                  border: "1px solid #1e3a5f", transition: "border-color 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#3b82f6")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1e3a5f")}
              >
                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>
                  {RESOURCE_ICON[r.type] ?? "🔗"}
                </span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>
                    {RESOURCE_LABEL[r.type] ?? r.type}
                  </div>
                  <div style={{
                    fontSize: 13, fontWeight: 600, color: "#60a5fa",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>
                    {r.title}
                  </div>
                  {r.reason && (
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4, lineHeight: 1.5 }}>
                      {r.reason}
                    </div>
                  )}
                </div>
              </a>
            ))}
          </div>
        ) : (
          <div style={{
            background: "#0f172a", borderRadius: 8, padding: "12px 16px",
            marginBottom: 24, fontSize: 13, color: "#475569", fontStyle: "italic",
            border: "1px solid #1e293b",
          }}>
            Resources are being fetched — they appear here once the enrichment step completes.
          </div>
        )}

        {/* Actions */}
        {canCheck && (
          <button
            onClick={onStartCheck}
            style={{
              background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8,
              padding: "12px 24px", cursor: "pointer", fontSize: 15, fontWeight: 600,
              width: "100%",
            }}
          >
            🎙 Start Comprehension Check
          </button>
        )}

        {node.status === "mastered" && (
          <div style={{
            background: "#10b98122", border: "1px solid #10b98155",
            borderRadius: 8, padding: "12px 16px", fontSize: 14, color: "#6ee7b7",
            textAlign: "center",
          }}>
            ✓ You have already mastered this node!
          </div>
        )}

        {node.status === "locked" && (
          <div style={{
            background: "#6b728022", border: "1px solid #6b728055",
            borderRadius: 8, padding: "12px 16px", fontSize: 14, color: "#9ca3af",
            textAlign: "center",
          }}>
            🔒 Complete all prerequisites before this node unlocks.
          </div>
        )}
      </div>
    </div>
  );
}
