# Milestone 3 Canonical Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Silver canonical jobs layer from Bronze Greenhouse raw payloads.

**Architecture:** Add pure Silver helpers first, then a migration-style SQL file for `canonical_jobs`, then a database upsert module, then a transform command that reads Bronze rows in deterministic order and upserts one current canonical row per source job. Bronze remains immutable source history.

**Tech Stack:** Python 3.11, psycopg 3, Postgres JSONB, BeautifulSoup, pytest, ruff.

---

## File Map

- Create `tests/test_silver.py`: failing-first tests for deterministic Silver identity, extraction, normalization, HTML cleanup, and timestamp parsing.
- Create `src/job_market_intel/silver.py`: pure Silver helpers with no database or network dependency.
- Create `sql/002_canonical_jobs.sql`: schema file for the canonical Silver table.
- Create `tests/test_canonical_jobs.py`: unit tests for canonical upsert SQL behavior using fake connections.
- Create `src/job_market_intel/canonical_jobs.py`: canonical record dataclass and Postgres upsert function.
- Modify `tests/test_postgres_integration.py`: apply both SQL files and add real Postgres idempotency coverage.
- Create `tests/test_transform_canonical_jobs.py`: unit tests for Bronze row mapping and transform orchestration.
- Create `src/job_market_intel/transform_canonical_jobs.py`: Bronze-to-Silver transform command.
- Modify `pyproject.toml`: add `transform-canonical-jobs` console command.

## Task 1: Silver Helper Tests

**Files:**
- Create: `tests/test_silver.py`

- [ ] **Step 1: Write failing tests for identity and normalization**

Create `tests/test_silver.py` with:

```python
"""Tests for Silver canonical identity and normalization helpers."""

from datetime import UTC, datetime

from job_market_intel.silver import (
    canonical_job_id,
    classify_remote_type,
    description_text_from_html,
    extract_department_name,
    extract_description_html,
    extract_job_url,
    extract_location_name,
    extract_office_location,
    normalize_seniority,
    normalize_title,
    parse_source_timestamp,
)


def greenhouse_payload() -> dict:
    """Return a realistic Greenhouse-shaped payload fragment."""
    return {
        "id": 123,
        "internal_job_id": 456,
        "requisition_id": "REQ-789",
        "company_name": "Databricks",
        "title": "Senior Backend Software Engineer",
        "language": "en",
        "location": {"name": "San Francisco, CA"},
        "offices": [{"name": "San Francisco", "location": "San Francisco, California, United States"}],
        "departments": [{"name": "Engineering"}],
        "absolute_url": "https://boards.greenhouse.io/databricks/jobs/123",
        "first_published": "2026-05-01T12:30:00-05:00",
        "updated_at": "2026-05-02T14:45:00-05:00",
        "content": "<p>Build data systems.</p><p>This role is hybrid in San Francisco.</p>",
    }


def test_canonical_job_id_is_deterministic_without_payload_hash() -> None:
    """Canonical identity should represent the source job, not a raw payload version."""
    first = canonical_job_id("greenhouse", "Databricks", "123")
    second = canonical_job_id("greenhouse", "Databricks", "123")
    different_job = canonical_job_id("greenhouse", "Databricks", "124")

    assert first == second
    assert first != different_job


def test_normalize_title_prefers_specific_engineering_roles() -> None:
    """Specific role families should win over broad software engineer matches."""
    assert normalize_title("Senior Backend Software Engineer") == "backend engineer"
    assert normalize_title("Frontend Engineer, Growth") == "frontend engineer"
    assert normalize_title("Machine Learning Engineer") == "machine learning engineer"
    assert normalize_title("Generative AI Engineer") == "ai engineer"
    assert normalize_title("Forward Deployed Engineer") == "forward deployed engineer"
    assert normalize_title("Product Manager, Data Platform") == "product manager"
    assert normalize_title("Customer Success Lead") == "unknown"


def test_classify_remote_type_uses_obvious_text_signals() -> None:
    """Remote classification should be conservative and deterministic."""
    assert classify_remote_type("Engineer", "Remote - US", None, "") == "remote"
    assert classify_remote_type("Engineer", "San Francisco", None, "Hybrid role in office") == "hybrid"
    assert classify_remote_type("Engineer", "New York, NY", "New York, NY", "") == "onsite"
    assert classify_remote_type("Engineer", None, None, "") == "unknown"


def test_normalize_seniority_uses_obvious_title_signals() -> None:
    """Seniority should stay unknown unless the title has a clear signal."""
    assert normalize_seniority("Software Engineer Intern") == "intern"
    assert normalize_seniority("Junior Data Engineer") == "junior"
    assert normalize_seniority("Mid-Level Software Engineer") == "mid"
    assert normalize_seniority("Software Engineer II") == "mid"
    assert normalize_seniority("Senior Backend Engineer") == "senior"
    assert normalize_seniority("Software Engineer III") == "senior"
    assert normalize_seniority("Staff Software Engineer") == "staff"
    assert normalize_seniority("Engineering Manager") == "manager"
    assert normalize_seniority("Software Engineer") == "unknown"


def test_extract_greenhouse_payload_fields() -> None:
    """Greenhouse extraction helpers should return optional fields without mutating payloads."""
    payload = greenhouse_payload()

    assert extract_location_name(payload) == "San Francisco, CA"
    assert extract_office_location(payload) == "San Francisco, California, United States"
    assert extract_department_name(payload) == "Engineering"
    assert extract_job_url(payload) == "https://boards.greenhouse.io/databricks/jobs/123"
    assert extract_description_html(payload) == payload["content"]


def test_description_text_from_html_returns_readable_text() -> None:
    """Description cleanup should convert Greenhouse HTML into plain text."""
    assert description_text_from_html("<p>Build data systems.</p><p>Use Python &amp; SQL.</p>") == (
        "Build data systems.\nUse Python & SQL."
    )
    assert description_text_from_html(None) is None


def test_parse_source_timestamp_handles_greenhouse_iso_strings() -> None:
    """Source timestamps should parse to aware UTC datetimes."""
    parsed = parse_source_timestamp("2026-05-01T12:30:00-05:00")

    assert parsed == datetime(2026, 5, 1, 17, 30, tzinfo=UTC)
    assert parse_source_timestamp(None) is None
    assert parse_source_timestamp("") is None
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
pytest tests/test_silver.py -v
```

Expected: FAIL because `job_market_intel.silver` does not exist.

## Task 2: Silver Helper Implementation

**Files:**
- Create: `src/job_market_intel/silver.py`

- [ ] **Step 1: Implement minimal pure helpers**

Create `src/job_market_intel/silver.py` with module and public function docstrings. Use `hashlib` and canonical JSON for `canonical_job_id`, BeautifulSoup for HTML cleanup, and conservative string matching for normalized categories.

- [ ] **Step 2: Run focused tests to verify GREEN**

Run:

```bash
pytest tests/test_silver.py -v
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
ruff check src/job_market_intel/silver.py tests/test_silver.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/job_market_intel/silver.py tests/test_silver.py
git commit -m "feat: add silver normalization helpers"
```

## Task 3: Canonical Schema

**Files:**
- Create: `sql/002_canonical_jobs.sql`

- [ ] **Step 1: Add schema file**

Create `sql/002_canonical_jobs.sql`:

```sql
CREATE TABLE IF NOT EXISTS canonical_jobs (
    job_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_company TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    source_internal_job_id TEXT,
    requisition_id TEXT,
    company_name TEXT,
    title TEXT,
    normalized_title TEXT NOT NULL,
    source_language TEXT,
    detected_language TEXT,
    location_name TEXT,
    office_location TEXT,
    department_name TEXT,
    remote_type TEXT NOT NULL,
    seniority TEXT NOT NULL,
    job_url TEXT,
    source_published_at TIMESTAMPTZ,
    source_updated_at TIMESTAMPTZ,
    description_html TEXT,
    description_text TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    currency TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (source_name, source_company, source_job_id)
);
```

- [ ] **Step 2: Commit schema**

Run:

```bash
git add sql/002_canonical_jobs.sql
git commit -m "feat: add canonical jobs schema"
```

## Task 4: Canonical Upsert Unit Tests

**Files:**
- Create: `tests/test_canonical_jobs.py`

- [ ] **Step 1: Write failing upsert tests**

Create tests that construct a `CanonicalJobRecord`, call `upsert_canonical_job`, and assert:

- SQL contains `ON CONFLICT (source_name, source_company, source_job_id) DO UPDATE`
- SQL does not set `first_seen_at` in the update clause
- params include deterministic `job_id`, timestamps, category fields, and nullable salary fields
- rowcount `1` reports a written row

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
pytest tests/test_canonical_jobs.py -v
```

Expected: FAIL because `job_market_intel.canonical_jobs` does not exist.

## Task 5: Canonical Upsert Implementation

**Files:**
- Create: `src/job_market_intel/canonical_jobs.py`

- [ ] **Step 1: Implement dataclass and upsert function**

Create:

- `CanonicalJobRecord`
- `CanonicalJobUpsertResult`
- `upsert_canonical_job(connection, record)`

Use a single `INSERT ... ON CONFLICT ... DO UPDATE` statement. Preserve the earliest known `first_seen_at` with `LEAST(...)`. Update `last_seen_at` and all source-derived fields from the latest observed raw version.

- [ ] **Step 2: Run focused tests**

Run:

```bash
pytest tests/test_canonical_jobs.py -v
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
ruff check src/job_market_intel/canonical_jobs.py tests/test_canonical_jobs.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/job_market_intel/canonical_jobs.py tests/test_canonical_jobs.py
git commit -m "feat: upsert canonical job records"
```

## Task 6: Transform Tests

**Files:**
- Create: `tests/test_transform_canonical_jobs.py`

- [ ] **Step 1: Write failing transform tests**

Create tests for:

- `canonical_record_from_raw_payload(...)` maps a Bronze row and Greenhouse payload into `CanonicalJobRecord`
- `transform_canonical_jobs(...)` reads raw rows in deterministic order
- malformed raw rows without source job IDs are skipped and counted
- summary counts include raw rows read, canonical rows written, and skipped rows

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
pytest tests/test_transform_canonical_jobs.py -v
```

Expected: FAIL because `job_market_intel.transform_canonical_jobs` does not exist.

## Task 7: Transform Implementation And CLI

**Files:**
- Create: `src/job_market_intel/transform_canonical_jobs.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Implement transform module**

Create:

- `RawPayloadRow`
- `TransformSummary`
- `canonical_record_from_raw_payload(...)`
- `iter_raw_payload_rows(connection, source_company=None)`
- `transform_canonical_jobs(connection, upsert_job=upsert_canonical_job, source_company=None)`
- `parse_args(argv=None)`
- `main()`

Read Bronze rows ordered by:

```sql
source_name, source_company, source_job_id, last_seen_at, fetched_at, raw_payload_id
```

Select both `fetched_at` and `last_seen_at`. `fetched_at` becomes canonical
`first_seen_at`; Bronze `last_seen_at` becomes canonical `last_seen_at`. Order raw
versions by `last_seen_at`, then `fetched_at`, then `raw_payload_id` within each
source job so a re-observed older payload version can become the current canonical
state.

- [ ] **Step 2: Add console command**

Add to `pyproject.toml`:

```toml
transform-canonical-jobs = "job_market_intel.transform_canonical_jobs:main"
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
pytest tests/test_transform_canonical_jobs.py -v
```

Expected: PASS.

- [ ] **Step 4: Run existing ingest tests**

Run:

```bash
pytest tests/test_ingest_greenhouse.py tests/test_raw_payloads.py tests/test_bronze.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/job_market_intel/transform_canonical_jobs.py tests/test_transform_canonical_jobs.py pyproject.toml
git commit -m "feat: transform bronze payloads to canonical jobs"
```

## Task 8: Postgres Integration Coverage

**Files:**
- Modify: `tests/test_postgres_integration.py`

- [ ] **Step 1: Update integration schema helper**

Change `ensure_schema(connection)` to apply both:

```python
INIT_SQL = PROJECT_ROOT / "sql" / "001_init.sql"
CANONICAL_JOBS_SQL = PROJECT_ROOT / "sql" / "002_canonical_jobs.sql"
```

and execute both files before committing.

- [ ] **Step 2: Add canonical rerun test**

Add a test that:

- inserts two Bronze versions for the same source job
- runs `transform_canonical_jobs`
- asserts one canonical row exists
- asserts the title reflects the later Bronze version
- runs `transform_canonical_jobs` again
- asserts the canonical row count remains one
- asserts `first_seen_at` stayed stable and `last_seen_at` reflects the latest Bronze
  observation timestamp, including unchanged duplicate payload sightings
- asserts a re-observed older payload version wins over a newer-but-less-recently-seen
  payload version

- [ ] **Step 3: Run integration tests**

Run:

```bash
JOB_MARKET_TEST_DATABASE_URL=postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket pytest tests/test_postgres_integration.py -v
```

Expected: PASS when Docker Postgres is running; SKIP only if the env var or database is unavailable.

- [ ] **Step 4: Commit**

Run:

```bash
git add tests/test_postgres_integration.py
git commit -m "test: cover canonical postgres idempotency"
```

## Task 9: Full Verification

**Files:**
- No expected file changes unless verification reveals a defect.

- [ ] **Step 1: Run unit test suite**

Run:

```bash
pytest -v
```

Expected: PASS, with integration tests skipped if `JOB_MARKET_TEST_DATABASE_URL` is not set.

- [ ] **Step 2: Run ruff**

Run:

```bash
ruff check .
```

Expected: PASS.

- [ ] **Step 3: Run local database verification**

With Docker Postgres running and Bronze rows available, apply:

```bash
psql postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket -f sql/001_init.sql
psql postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket -f sql/002_canonical_jobs.sql
transform-canonical-jobs --database-url postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket
transform-canonical-jobs --database-url postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket
```

Expected: first transform writes canonical rows; second transform does not create duplicate canonical jobs.

- [ ] **Step 4: Final status**

Run:

```bash
git status --short --branch
```

Expected: clean tracked tree except known untracked local files if they still exist.
