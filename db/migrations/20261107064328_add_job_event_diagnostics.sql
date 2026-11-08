-- migrate:up

ALTER TABLE job_events
    ADD COLUMN exception_type VARCHAR(255),
    ADD COLUMN exception_message TEXT,
    ADD COLUMN traceback TEXT,
    ADD COLUMN exchange VARCHAR(255),
    ADD COLUMN routing_key VARCHAR(255);


-- migrate:down

ALTER TABLE job_events
    DROP COLUMN routing_key,
    DROP COLUMN exchange,
    DROP COLUMN traceback,
    DROP COLUMN exception_message,
    DROP COLUMN exception_type;