-- migrate:up

ALTER TABLE job_events
    ALTER COLUMN workspace_id SET NOT NULL;

CREATE INDEX ix_job_events_workspace_task_occurred_at
    ON job_events (workspace_id, task_id, occurred_at);

-- migrate:down

DROP INDEX IF EXISTS ix_job_events_workspace_task_occurred_at;

ALTER TABLE job_events
    ALTER COLUMN workspace_id DROP NOT NULL;