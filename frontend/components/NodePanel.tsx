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
  article: "📝",
};

const RESOURCE_LABEL: Record<string, string> = {
  github: "GitHub Repository",
  doc: "Official Documentation",
  youtube: "YouTube Tutorial",
  article: "Tutorial Article",
};

interface Props {
  node: DAGNode;
  onStartCheck: () => void;
  onClose: () => void;
}

/**
 * Fire-and-forget POST to /api/resource-visit when the user clicks a resource link.
 * This ensures even users without the Chrome extension get credit for consuming resources.
 */
function reportResourceClick(nodeId: string, resourceUrl: string, sessionId = "default") {
  fetch("/api/resource-visit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      node_id: nodeId,
      resource_url: resourceUrl,
    }),
  }).catch(() => {
    // Silently ignore — backend may not be reachable
  });
}

export default function NodePanel({ node, onStartCheck, onClose }: Props) {
  const color = STATUS_COLOR[node.status] ?? "#6b7280";
  // Gate: only allow comprehension check when the node has been "seen" (at least 1 resource visited)
  const canCheck = node.status === "seen";
  const needsResources = node.status === "available";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.24)",
        backdropFilter: "blur(14px)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: "rgba(255,255,255,0.96)",
        borderRadius: 20,
        padding: 32,
        maxWidth: 540,
        width: "90%",
        color: "#0f172a",
        position: "relative",
        maxHeight: "88vh",
        overflowY: "auto",
        border: "1px solid rgba(148,163,184,0.16)",
        boxShadow: "0 24px 80px rgba(15,23,42,0.16)",
      }}>
        {/* Close */}
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 14, right: 14, background: "rgba(241,245,249,0.9)",
            border: "1px solid rgba(148,163,184,0.18)", color: "#64748b", fontSize: 22, cursor: "pointer",
            lineHeight: 1, padding: 4, borderRadius: 4,
          }}
          title="Close"
        >
          ✕
        </button>

        {/* Status badge */}
        <div style={{
          display: "inline-block", fontSize: 10, background: color + "22",
          border: `1px solid ${color}55`, borderRadius: 999, padding: "4px 10px",
          textTransform: "uppercase", letterSpacing: 1, color, marginBottom: 10,
        }}>
          {node.status}
        </div>

        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6, color: "#0f172a", lineHeight: 1.3 }}>
          {node.title}
        </h2>

        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#64748b", marginBottom: 18 }}>
          <span>🎯 {node.difficulty}</span>
          <span>⏱ {node.estimated_hours}h estimated</span>
          {node.prerequisites.length > 0 && (
            <span>🔗 {node.prerequisites.length} prerequisite{node.prerequisites.length > 1 ? "s" : ""}</span>
          )}
        </div>

        <p style={{ fontSize: 14, lineHeight: 1.75, color: "#475569", marginBottom: 22 }}>
          {node.description}
        </p>

        {/* Success criteria */}
        <div style={{
          background: "#f8fafc", borderRadius: 14, padding: "12px 16px",
          marginBottom: 24, border: "1px solid rgba(148,163,184,0.16)",
        }}>
          <strong style={{
            fontSize: 11, color: "#64748b", display: "block",
            marginBottom: 6, letterSpacing: 1, textTransform: "uppercase",
          }}>
            Success Criteria
          </strong>
          <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0, color: "#0f172a" }}>{node.success_criteria}</p>
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
                onClick={() => reportResourceClick(node.id, r.url)}
                style={{
                  display: "flex", alignItems: "flex-start", gap: 12,
                  background: "#f8fafc", borderRadius: 14, padding: "12px 14px",
                  textDecoration: "none", color: "#0f172a",
                  border: "1px solid rgba(148,163,184,0.16)", transition: "border-color 0.15s, transform 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(37,99,235,0.32)";
                  e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(148,163,184,0.16)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>
                  {RESOURCE_ICON[r.type] ?? "🔗"}
                </span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: "#64748b", marginBottom: 2 }}>
                    {RESOURCE_LABEL[r.type] ?? r.type}
                  </div>
                  <div style={{
                    fontSize: 13, fontWeight: 600, color: "#2563eb",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>
                    {r.title}
                  </div>
                  {r.reason && (
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 4, lineHeight: 1.5 }}>
                      {r.reason}
                    </div>
                  )}
                </div>
              </a>
            ))}
          </div>
        ) : (
          <div style={{
            background: "#f8fafc", borderRadius: 14, padding: "12px 16px",
            marginBottom: 24, fontSize: 13, color: "#64748b", fontStyle: "italic",
            border: "1px solid rgba(148,163,184,0.16)",
          }}>
            Resources are being fetched — they appear here once the enrichment step completes.
          </div>
        )}

        {/* Actions */}
        {canCheck && (
          <button
            onClick={onStartCheck}
            style={{
              background: "linear-gradient(135deg, #2563eb, #3b82f6)", color: "#fff", border: "none", borderRadius: 12,
              padding: "12px 24px", cursor: "pointer", fontSize: 15, fontWeight: 600,
              width: "100%",
              boxShadow: "0 10px 24px rgba(37,99,235,0.14)",
            }}
          >
            🎙 Start Comprehension Check
          </button>
        )}

        {needsResources && node.resources.length > 0 && (
          <div style={{
            background: "#3b82f622", border: "1px solid #3b82f655",
            borderRadius: 8, padding: "12px 16px", fontSize: 14, color: "#93c5fd",
            textAlign: "center",
          }}>
            📖 Review at least one resource above to unlock the comprehension check
          </div>
        )}

        {node.status === "mastered" && (
          <div style={{
            background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
            borderRadius: 14, padding: "12px 16px", fontSize: 14, color: "#047857",
            textAlign: "center",
          }}>
            ✓ You have already mastered this node!
          </div>
        )}

        {node.status === "locked" && (
          <div style={{
            background: "rgba(100,116,139,0.08)", border: "1px solid rgba(100,116,139,0.18)",
            borderRadius: 14, padding: "12px 16px", fontSize: 14, color: "#64748b",
            textAlign: "center",
          }}>
            🔒 Complete all prerequisites before this node unlocks.
          </div>
        )}
      </div>
    </div>
  );
}
