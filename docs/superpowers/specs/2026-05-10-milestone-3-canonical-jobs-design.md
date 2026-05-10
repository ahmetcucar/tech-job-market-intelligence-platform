# Milestone 3 Canonical Jobs Design

## Goal

Build the first Silver layer by transforming Bronze Greenhouse raw payload rows into
clean canonical job records in Postgres.

Milestone 3 should prove that raw source payloads can become stable, queryable job
records without losing reproducibility. Bronze remains the source of truth and keeps
exact payload version history. Silver represents the latest normalized state for each
source job.

## Scope

This milestone covers the full first canonical path:

- create the `canonical_jobs` table
- define deterministic canonical job identity
- extract core Greenhouse fields from Bronze `payload_json`
- normalize a small set of deterministic fields
- upsert canonical rows from Bronze rows
- add a command-line transform entry point
- verify reruns update existing canonical rows instead of duplicating them

This milestone does not add skill extraction, Streamlit UI work, company dimensions,
location dimensions, salary parsing rules, years-of-experience extraction, language
detection, or job closing logic. Those belong to future milestones. Nullable columns
may exist for fields such as salary and detected language when the data model already
calls for them.

## Data Flow

The intended flow is:

```text
raw_job_payloads
        ↓
Bronze row reader
        ↓
Greenhouse canonical mapper
        ↓
deterministic normalization helpers
        ↓
canonical_jobs upsert
```

`raw_job_payloads` is append-only version history for observed source payloads. The
canonical transform reads Bronze rows and writes one current Silver row per source job.
If a source job appears in multiple Bronze versions, all versions can map to the same
canonical `job_id`; the latest processed version updates the Silver row.

The first implementation can process all Bronze rows in deterministic order:

```text
source_name, source_company, source_job_id, fetched_at, raw_payload_id
```

For a source job with multiple Bronze versions, this means the most recently fetched
payload wins. A future optimization can process only raw rows that are new or changed
since the previous canonical run.

## Canonical Job Identity

`canonical_jobs.job_id` will be deterministic from:

- `source_name`
- `source_company`
- `source_job_id`

It will not include `payload_hash`.

This identity means a changed Greenhouse payload updates the same canonical job
instead of creating a duplicate canonical row. Bronze keeps version history through
`payload_hash`; Silver keeps the latest canonical state for the source job.

The table should also enforce a unique constraint on:

```text
source_name, source_company, source_job_id
```

That constraint is the database-level idempotency key for canonical upserts.

## `canonical_jobs` Table

The first table should follow the existing data model closely:

```text
canonical_jobs
- job_id
- source_name
- source_company
- source_job_id
- source_internal_job_id
- requisition_id
- company_name
- title
- normalized_title
- source_language
- detected_language
- location_name
- office_location
- department_name
- remote_type
- seniority
- job_url
- source_published_at
- source_updated_at
- description_html
- description_text
- salary_min
- salary_max
- currency
- first_seen_at
- last_seen_at
- is_active
```

The MVP should use text fields for source identifiers and normalized category fields.
Timestamps should use `TIMESTAMPTZ`. Salary fields should be nullable numeric fields.
`is_active` should default to true for rows produced from currently stored Bronze
payloads.

## Greenhouse Field Mapping

The Greenhouse mapper should extract fields conservatively:

- Greenhouse `id` becomes `source_job_id`
- Greenhouse `internal_job_id` becomes `source_internal_job_id`
- Greenhouse `requisition_id` becomes `requisition_id`
- Greenhouse `company_name` becomes `company_name`
- Greenhouse `title` becomes `title`
- Greenhouse `language` becomes `source_language`
- Greenhouse `location.name` becomes `location_name`
- Greenhouse `offices[0].location` becomes `office_location` when present
- Greenhouse `departments[0].name` becomes `department_name` when present
- Greenhouse `absolute_url` becomes `job_url`
- Greenhouse `first_published` becomes `source_published_at`
- Greenhouse `updated_at` becomes `source_updated_at`
- Greenhouse `content` becomes `description_html`
- cleaned text from `content` becomes `description_text`

Missing or malformed optional fields should produce `None` or `unknown` instead of
dropping the job.

## Deterministic Normalization

Normalization should start simple and rules-based. These helpers should be pure
functions with no database or network dependency.

### Title Normalization

`normalized_title` should map obvious role titles into broad families:

- `software engineer`
- `backend engineer`
- `frontend engineer`
- `data engineer`
- `analytics engineer`
- `machine learning engineer`
- `ai engineer`
- `forward deployed engineer`
- `product manager`
- `unknown`

Rules should prefer more specific matches before broad matches. For example, "Senior
Backend Software Engineer" should normalize to `backend engineer`, not
`software engineer`.

### Remote Type

`remote_type` should be one of:

- `remote`
- `hybrid`
- `onsite`
- `unknown`

The first version can classify from title, location text, office location, and
description text. Obvious remote and hybrid signals should win over generic office
signals. Ambiguous records should remain `unknown`.

### Department

`department_name` should use the first Greenhouse department name when the source
provides departments as a non-empty list. If no department exists, store `None`.

### Location

`location_name` should come from `payload_json.location.name` when available.
`office_location` should come from the first usable `offices[].location` value. No
geocoding or location parsing is included in this milestone.

### Job URL

`job_url` should come from `absolute_url` when available. The transform should not
construct Greenhouse URLs from IDs in this milestone.

### Description

`description_html` should preserve Greenhouse `content` as provided in the payload.
`description_text` should strip HTML into readable plain text using the existing
BeautifulSoup dependency.

### Seniority

`seniority` should start as `unknown` unless an obvious title rule applies. The first
allowed values are:

- `intern`
- `junior`
- `mid`
- `senior`
- `staff`
- `manager`
- `unknown`

This should remain conservative. Ambiguous or non-English titles can stay `unknown`.
Plain titles such as "Software Engineer" should not imply `mid`. Only explicit signals
such as "mid-level", "intermediate", or common level markers such as "Engineer II"
should normalize to `mid`.

### Years Of Experience

Years-of-experience requirements should be deferred. They are useful, but extracting
them from descriptions needs separate parsing rules for ranges, minimums, preferred
requirements, and ambiguous phrasing. A future milestone can add fields such as
`min_years_experience`, `max_years_experience`, and `years_experience_text`.

## Files And Responsibilities

### `sql/002_canonical_jobs.sql`

Adds the `canonical_jobs` table after the Bronze schema from `sql/001_init.sql`.

Milestone 3 should start the habit of one schema-change file per milestone instead of
continually expanding the original Bronze bootstrap file. A clean local database should
apply SQL files in order:

```text
sql/001_init.sql
sql/002_canonical_jobs.sql
```

The `002` file should include the primary key and uniqueness constraints needed for
idempotent canonical upserts.

### `src/job_market_intel/silver.py`

Pure Silver identity and normalization helpers.

Expected public functions:

- `canonical_job_id(source_name, source_company, source_job_id)`
- `normalize_title(title)`
- `classify_remote_type(title, location_name, office_location, description_text)`
- `normalize_seniority(title)`
- `extract_location_name(payload)`
- `extract_office_location(payload)`
- `extract_department_name(payload)`
- `extract_job_url(payload)`
- `extract_description_html(payload)`
- `description_text_from_html(description_html)`
- `parse_source_timestamp(value)`

This module should have no database dependency. It should be heavily unit tested
because it defines the deterministic behavior of the Silver layer.

### `src/job_market_intel/canonical_jobs.py`

Database write behavior for canonical jobs.

This module should own the `INSERT ... ON CONFLICT ... DO UPDATE` statement for
`canonical_jobs`. It should accept a canonical job record object or explicit fields
and return whether a row was inserted or updated when that can be determined cleanly.

Upserts should preserve `first_seen_at` and update `last_seen_at`.

### `src/job_market_intel/transform_canonical_jobs.py`

Command-line transformation entry point.

This module should read Bronze rows, map each row into canonical fields, and call the
canonical upsert function. It should expose a console command so the transform can be
run after Bronze ingestion.

The first command can process all Bronze rows. It should print counts for rows read,
canonical rows inserted or updated, and rows skipped if any malformed payload cannot
be safely mapped.

### `tests/test_silver.py`

Unit tests for identity, extraction, normalization, HTML-to-text cleanup, and timestamp
parsing.

These tests should be written first and should cover realistic Greenhouse-shaped
payload fragments.

### `tests/test_canonical_jobs.py`

Unit tests for canonical upsert SQL construction and parameters using a small fake
connection, following the existing `raw_payloads` test style.

### `tests/test_postgres_integration.py`

Adds focused Postgres integration coverage for canonical upsert idempotency and
rerun behavior.

The tests should prove that:

- a canonical row is inserted for a source job
- rerunning with the same source job updates the existing row
- `first_seen_at` is preserved
- `last_seen_at` changes to the most recent transform timestamp
- only one canonical row exists for the source job

## Upsert Behavior

The canonical upsert should conflict on:

```text
source_name, source_company, source_job_id
```

On conflict, it should update fields derived from the latest processed raw payload:

- source internal IDs
- requisition ID
- company name
- title
- normalized title
- language fields
- location and department fields
- remote type
- seniority
- job URL
- source timestamps
- description fields
- salary fields
- currency
- `last_seen_at`
- `is_active`

It should not overwrite `first_seen_at` on conflict.

## Error Handling

The transform should keep MVP behavior explicit and visible. Database failures should
fail the command. Optional missing Greenhouse fields should not fail the command.

Malformed payloads that do not contain a usable source job ID should be skipped and
counted, because they cannot be safely assigned canonical identity. The command should
report skipped counts so data quality issues remain visible.

## Verification

Milestone 3 will be verified by:

- failing-first unit tests for Silver identity and normalization helpers
- unit tests for canonical upsert SQL behavior
- Postgres integration tests for canonical idempotency
- `ruff`
- `pytest`
- a local transform run against Bronze rows after applying `sql/001_init.sql` and
  `sql/002_canonical_jobs.sql`
- a rerun showing canonical rows are updated rather than duplicated

## Implementation Order

Implementation should proceed in small commits:

1. Add Silver helper tests and pure helper implementation.
2. Add `canonical_jobs` schema and focused database upsert behavior.
3. Add Bronze-to-Silver mapping and transform command.
4. Add Postgres integration coverage for rerun/idempotency behavior.
5. Run full verification and update docs only if observed behavior differs from this
   design.

Each code file should keep the project documentation rule: module docstring at the top
and clear docstrings for public functions.
