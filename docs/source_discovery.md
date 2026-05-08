# Source Discovery

This document records what we observe from real job source responses before designing ingestion tables or normalization logic.

## Greenhouse

Greenhouse public job boards expose job postings as JSON.

Example endpoint shape:

```text
https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
```

The top-level response contains a `jobs` array. Each item in `jobs` is a job posting object.

### Observed Job Fields

From an observed Databricks Greenhouse posting, useful fields include:

- `id`
- `internal_job_id`
- `requisition_id`
- `title`
- `company_name`
- `location.name`
- `departments`
- `offices`
- `absolute_url`
- `updated_at`
- `first_published`
- `content`
- `metadata`

### Field Notes

- `id` appears to be the public Greenhouse job ID.
- `internal_job_id` appears to be a Greenhouse internal identifier.
- `requisition_id` appears to be the company's requisition identifier.
- `title` is the original job title shown to applicants.
- `company_name` may be available directly from the source.
- `location.name` can be broad, such as `Japan`.
- `offices` can contain more specific office names and locations, such as `Tokyo, Japan`.
- `departments` is an array, even when a job has only one department.
- `metadata` is an array of flexible source-specific fields.
- `absolute_url` is the public job posting URL.
- `updated_at` is the source-provided update timestamp.
- `first_published` is the source-provided publish timestamp.
- `content` contains HTML-escaped job description content.

### Schema Implications

The first database layer should preserve the full source object as raw JSON. This lets us reprocess historical payloads when we improve parsing or normalization.

The first canonical job table should only extract fields we clearly understand:

- source job ID
- company name
- title
- location name
- department name
- office name or office location
- job URL
- source update timestamp
- source publish timestamp
- description HTML
- description text

### Open Questions

- Should canonical location prefer `location.name`, `offices[].location`, or both?
- Should departments and offices be stored as arrays in the first canonical table, or normalized into separate tables later?
- Which metadata fields are consistent enough across companies to promote into canonical fields?
- How often do Greenhouse postings include salary information?
- How should non-English descriptions affect title normalization and skill extraction?
