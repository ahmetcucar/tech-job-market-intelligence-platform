# Milestone 2 Bronze Raw Payloads Design

## Goal

Persist exact raw Greenhouse job payloads into Postgres incrementally.

Milestone 2 focuses only on the Bronze layer. The Bronze layer stores source payloads with minimal interpretation so later normalization can be rerun or debugged from the original source data.

## Scope

This milestone will ingest every company listed in `config/greenhouse_companies.yml`.

The system will not attempt broad company discovery in this milestone. Company discovery is a separate future concern. For now, the configured company list is the source registry.

## Data Identity

Each raw job version is identified by:

- `source_name`: the source system, initially `greenhouse`
- `source_company`: the configured company name
- `source_job_id`: the source job ID from Greenhouse
- `payload_hash`: a stable hash of the full raw job JSON payload

`raw_payload_id` is a deterministic ID derived from those identity fields.

Same source job ID plus same payload hash means the exact payload version has already been seen. Same source job ID plus a different payload hash means the source job changed and should create a new Bronze row.

## Files And Responsibilities

### `src/job_market_intel/bronze.py`

Pure Bronze identity helpers.

- `stable_payload_hash(payload)` returns a deterministic hash of a JSON-compatible payload.
- `raw_payload_id(source_name, source_company, source_job_id, payload_hash)` returns a deterministic raw payload row ID.

This file has no database or network dependency. It is easy to test and explains the Bronze identity rules directly.

### `tests/test_bronze.py`

Unit tests for Bronze identity.

The tests prove that payload hashing is stable across JSON key order, changes when payload content changes, and produces deterministic raw payload IDs.

### `src/job_market_intel/db.py`

Shared Postgres connection helper.

This keeps database connection details in one place so Bronze storage, future canonical storage, and later app code do not duplicate connection strings or environment variable handling.

### `src/job_market_intel/raw_payloads.py`

Bronze Postgres write behavior.

This module will insert rows into `raw_job_payloads` using `ON CONFLICT DO NOTHING`. It owns the database insert statement and returns enough information for the ingest command to report inserted versus skipped payload versions.

### `src/job_market_intel/ingest_greenhouse.py`

Command-line ingestion entry point.

This module will load all configured Greenhouse companies, fetch each company's jobs, and store each raw job payload. It wires existing config and Greenhouse fetch code to the new Bronze storage layer.

### `pyproject.toml`

Adds the `ingest-greenhouse` console command once the ingest entry point exists.

## Error Handling

Network and database exceptions will be allowed to fail the command visibly during the MVP. Silent partial success would be more confusing at this stage.

The insert path itself will be idempotent for identical payload versions because the table has a unique constraint on `(source_name, source_company, source_job_id, payload_hash)`.

## Verification

Milestone 2 will be verified by:

- unit tests for stable payload hashing and deterministic raw payload IDs
- a database check that `raw_job_payloads` exists after applying `sql/001_init.sql`
- an ingestion run against all configured Greenhouse companies
- a rerun that does not create duplicate rows for identical payload versions
