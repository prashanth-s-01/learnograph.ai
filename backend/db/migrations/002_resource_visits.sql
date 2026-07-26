-- Track which resources a user has visited per learning node.
-- A node transitions from "available" → "seen" on first resource visit.

CREATE TABLE IF NOT EXISTS resource_visits (
    session_id   TEXT        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    node_id      TEXT        NOT NULL,
    resource_url TEXT        NOT NULL,
    visited_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, node_id, resource_url),
    FOREIGN KEY (session_id, node_id) REFERENCES dag_nodes(session_id, node_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resource_visits_node ON resource_visits(session_id, node_id);
