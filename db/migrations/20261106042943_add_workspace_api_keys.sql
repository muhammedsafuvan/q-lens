
-- migrate:up

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name VARCHAR(120) NOT NULL,
    key_prefix VARCHAR(24) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX ix_api_keys_workspace_id
    ON api_keys (workspace_id);

ALTER TABLE job_events
    ADD COLUMN workspace_id UUID
    REFERENCES workspaces(id) ON DELETE RESTRICT;

CREATE INDEX ix_job_events_workspace_occurred_at
    ON job_events (workspace_id, occurred_at DESC, task_id);


-- migrate:down

DROP INDEX IF EXISTS ix_job_events_workspace_occurred_at;

ALTER TABLE job_events
    DROP COLUMN IF EXISTS workspace_id;

DROP INDEX IF EXISTS ix_api_keys_workspace_id;

DROP TABLE IF EXISTS api_keys;
