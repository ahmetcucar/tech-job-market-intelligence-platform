CREATE TABLE IF NOT EXISTS raw_job_payloads (
    raw_payload_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_company TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    UNIQUE (source_name, source_company, source_job_id, payload_hash)
);
