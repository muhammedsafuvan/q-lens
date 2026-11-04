-- migrate:up

CREATE TABLE job_events (
    event_id UUID PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    worker_name VARCHAR(255),
    queue_name VARCHAR(255),
    attempt INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_job_events_attempt_positive
        CHECK (attempt >= 1),

    CONSTRAINT ck_job_events_event_type
        CHECK (
            event_type IN (
                'received',
                'started',
                'succeeded',
                'failed',
                'retried'
            )
        )
);

CREATE INDEX ix_job_events_task_id_occurred_at
    ON job_events (task_id, occurred_at);

CREATE INDEX ix_job_events_event_type_occurred_at
    ON job_events (event_type, occurred_at);


-- migrate:down

DROP TABLE job_events;