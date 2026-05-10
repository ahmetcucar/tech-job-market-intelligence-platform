# MVP Build Plan

The first MVP should prove the smallest useful product loop:

> Ingest real public job postings, normalize them into Postgres, extract basic market signals, and make those signals searchable in Streamlit.

This version intentionally starts without FastAPI. Streamlit can read from Postgres directly while the data model and product queries are still taking shape. FastAPI becomes the next layer once the MVP proves which queries and workflows matter.

## Starting Scope

### Source

Start with one source:

- Greenhouse public job boards

Use a small company allowlist at first. The goal is reliable ingestion, not broad coverage.

Example initial companies:

- Stripe
- Databricks
- Cloudflare
- DoorDash
- Reddit
- Ramp
- Notion

### First Product Questions

The MVP should answer:

- Which companies are hiring for a role?
- Which skills appear most often in current postings?
- Which jobs are remote, hybrid, or onsite?
- Which roles are most common across the ingested companies?
- What skills does a specific job posting appear to require?

## Architecture For Version 0

```text
Greenhouse public boards
        ↓
Python ingestion script
        ↓
Bronze raw payload storage
        ↓
Silver canonical job records
        ↓
Rules-based normalization
        ↓
Rules-based skill extraction
        ↓
Streamlit search and dashboard UI
```

The first data model should follow a simple Bronze/Silver/Gold progression:

- **Bronze:** preserve raw Greenhouse job objects for reproducibility.
- **Silver:** extract stable canonical job fields for search, filtering, and skill extraction.
- **Gold:** start as dashboard SQL queries; promote to tables or views later if needed.

International and non-English postings should be included by default. The MVP should preserve the original text, store source language when available, and expose uncertainty in normalized fields instead of dropping records.

## Milestone 1: Fetch Greenhouse Jobs

Build the smallest source access layer that:

- reads a configured list of Greenhouse companies
- fetches public job postings from Greenhouse boards
- returns Greenhouse job objects as Python dictionaries
- prints a small preview summary for one company

Done when:

- the project can fetch jobs for at least one verified Greenhouse board
- the project can load the company config and use a board token from it
- the preview command can print job count, first job title, and first job ID
- no database writes are required yet

## Milestone 2: Store Bronze Raw Payloads

Build the first persistent ingestion layer.

Create the Bronze table:

```text
raw_job_payloads
- raw_payload_id
- source_name
- source_company
- source_job_id
- fetched_at
- payload_hash
- payload_json
```

The raw table stores the full source job object so parsing and normalization can be rerun later.

Incremental ingestion approach:

- compute a stable `payload_hash` for each raw job object
- insert raw payloads with `ON CONFLICT DO NOTHING`
- treat same job ID plus same hash as already seen
- treat same job ID plus different hash as a changed job version
- use new raw versions as the trigger for later Silver normalization

Done when:

- raw Greenhouse payloads land in `raw_job_payloads`
- repeated runs do not create duplicate raw payload versions
- same job ID plus same hash is skipped
- same job ID plus different hash is stored as a new raw version

## Milestone 3: Build Canonical Jobs

Create the first Silver table for normalized job records. The schema should be based on fields observed in real Greenhouse responses, not guessed in advance.

Initial canonical table:

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

The canonical table is the first Silver layer. It extracts fields we clearly understand from the source:

- Greenhouse `id` becomes `source_job_id`
- Greenhouse `internal_job_id` becomes `source_internal_job_id`
- Greenhouse `requisition_id` becomes `requisition_id`
- Greenhouse `company_name` becomes `company_name`
- Greenhouse `language` becomes `source_language`
- Greenhouse `location.name` becomes `location_name`
- Greenhouse `offices[].location` can inform `office_location`
- Greenhouse `departments[].name` can inform `department_name`
- Greenhouse `absolute_url` becomes `job_url`
- Greenhouse `first_published` becomes `source_published_at`
- Greenhouse `updated_at` becomes `source_updated_at`
- Greenhouse `content` becomes `description_html`, then cleaned into `description_text`

Fields such as `normalized_title`, `remote_type`, `seniority`, `detected_language`, and salary fields are derived or normalized fields. They can start as `unknown` or `NULL` when the source does not clearly provide them.

Done when:

- cleaned job records land in `canonical_jobs`
- each canonical job has a stable unique ID
- rerunning ingestion updates `last_seen_at` for existing jobs
- source-provided timestamps are preserved separately from ingestion timestamps
- international and non-English postings are retained rather than skipped

## Milestone 4: Normalize Core Fields

Start with simple deterministic normalization.

Normalize titles into broad role families such as:

- software engineer
- backend engineer
- frontend engineer
- data engineer
- analytics engineer
- machine learning engineer
- product manager
- unknown

Normalize remote status into:

- remote
- hybrid
- onsite
- unknown

Normalize seniority into:

- intern
- junior
- mid
- senior
- staff
- manager
- unknown

Done when:

- most ingested jobs have a usable `normalized_title`
- remote/hybrid/onsite status can be filtered in the UI
- seniority is populated when obvious from the title or description
- non-English or ambiguous postings can remain `unknown` without being treated as failures
- unknown values are allowed and visible instead of hidden

## Milestone 5: Add Rules-Based Skill Extraction

Rules-based skill extraction means maintaining a known list of skills and aliases, then scanning job titles and descriptions for those terms.

Example:

```python
SKILLS = {
    "python": ["python"],
    "sql": ["sql", "postgres", "postgresql", "mysql"],
    "spark": ["spark", "apache spark", "pyspark"],
    "aws": ["aws", "amazon web services"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt"],
    "react": ["react", "react.js", "reactjs"],
    "typescript": ["typescript", "ts"],
    "go": ["go", "golang"],
}
```

Initial skill tables:

```text
skills
- skill_id
- skill_name
- skill_category
```

```text
job_skills
- job_id
- skill_id
- extraction_method
- confidence
```

For the first version, `extraction_method` can be `rules` and `confidence` can be `1.0`.

Done when:

- each job can show extracted skills
- the app can rank top skills across all jobs
- skill filters can be used in search

## Milestone 6: Build Streamlit MVP UI

Streamlit should connect directly to Postgres for the first MVP.

Build three views:

### Job Search

Filters:

- company
- normalized role
- location
- remote type
- skill

Results:

- title
- company
- location
- remote type
- extracted skills
- source URL

### Market Overview

Charts:

- jobs by company
- jobs by normalized role
- top skills
- remote vs hybrid vs onsite

### Job Detail

Show:

- original title
- normalized title
- company
- location
- remote type
- extracted skills
- cleaned description
- source URL

Done when:

- a user can explore real ingested jobs without touching the database
- the dashboard exposes at least 3 useful market signals
- the UI makes data quality issues visible enough to improve the pipeline

## Milestone 7: Add Resume Match Prototype

After job search and skill extraction work, add a simple resume matching workflow.

First version:

- user pastes resume text
- user selects one job
- app extracts skills from resume using the same rules-based skill list
- app compares resume skills against job skills

Output:

- match score
- matched skills
- missing skills
- job skills found

Simple scoring:

```text
match_score = matched_job_skills / total_job_skills
```

Done when:

- the user can compare one resume against one job
- the result is explainable without an LLM
- the same skill taxonomy powers both job analysis and resume matching

## Add FastAPI After Version 0

Add FastAPI once the Streamlit MVP reveals the most important data access patterns.

Likely first endpoints:

```text
GET /health
GET /jobs
GET /jobs/{job_id}
GET /skills/top
GET /companies
GET /market/overview
```

FastAPI is a Phase 2 step because it should wrap proven queries rather than speculative ones.

## Definition Of Done For Initial MVP

The initial MVP is complete when the project can demonstrate this:

> I can ingest real public Greenhouse job postings, store raw and normalized records in Postgres, extract skills with deterministic rules, and explore hiring trends through a Streamlit UI.

That is the foundation. After this, the project can grow naturally into backend APIs, semantic search, resume intelligence, and AI-assisted career recommendations.
