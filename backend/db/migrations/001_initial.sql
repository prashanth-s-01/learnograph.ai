-- Learnograph initial schema

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY DEFAULT 'default',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sessions (id) VALUES ('default') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS dag_nodes (
    session_id          TEXT        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    node_id             TEXT        NOT NULL,
    title               TEXT        NOT NULL,
    description         TEXT        NOT NULL,
    prerequisites       JSONB       NOT NULL DEFAULT '[]',
    difficulty          TEXT        NOT NULL,
    estimated_hours     FLOAT       NOT NULL DEFAULT 1.0,
    success_criteria    TEXT        NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'locked',
    resources           JSONB       NOT NULL DEFAULT '[]',
    completed_at        TIMESTAMPTZ,
    triggering_content  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, node_id)
);

CREATE INDEX IF NOT EXISTS idx_dag_nodes_session ON dag_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_dag_nodes_status  ON dag_nodes(session_id, status);
