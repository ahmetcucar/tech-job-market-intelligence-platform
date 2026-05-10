# Tech Job Market Intelligence Platform

An end-to-end data, software, and AI platform that collects public tech job postings, models the labor market, and turns raw hiring data into useful career intelligence.

The platform helps engineers answer questions such as:

- Which companies are hiring for my role in a specific city?
- What skills are rising fastest for data, software, and AI engineering roles?
- What salary ranges exist by city, company, role, and seniority?
- How well does my resume match a specific job posting?
- What skills should I learn next based on the roles I want?
- Which companies are increasing hiring activity over time?

## Why This Project

This project is designed to be serious enough to discuss in interviews from multiple angles:

- **Data engineering:** ingestion, orchestration, incremental loading, data modeling, quality checks, and analytics marts.
- **Software engineering:** backend APIs, search, user workflows, async workers, caching, CI/CD, and deployment.
- **AI engineering:** skill extraction, embeddings, semantic search, resume matching, RAG, recommendations, and evaluation.

## Documentation

- [Project Overview](docs/overview.md)
- [Product Requirements](docs/product.md)
- [System Architecture](docs/architecture.md)
- [Data Model](docs/data_model.md)
- [MVP Build Plan](docs/mvp_build_plan.md)
- [AI Design](docs/ai.md)
- [Resume Positioning](docs/resume_strategy.md)
- [Learning Context](docs/learning_context.md)

## MVP Scope

The first version should prove the core loop:

1. Ingest public job postings daily.
2. Normalize and store postings in a queryable database.
3. Extract companies, roles, locations, salaries, skills, and seniority.
4. Expose search and trend APIs.
5. Show a dashboard for hiring trends and skill demand.
6. Support AI-assisted resume-to-job matching.

## Getting Started With The MVP

The first build starts with Greenhouse source discovery, then Bronze raw payload storage in Postgres, then Streamlit.

Create a virtual environment and install the project:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Milestone 1: Fetch Greenhouse Jobs

Verify the Greenhouse config loader and API client:

```bash
python -m job_market_intel.preview_greenhouse
```

Expected output shape:

```text
Company: Databricks
Board token: databricks
Jobs fetched: 812
First job title: ...
First job ID: ...
```

The job count and first job may change as Greenhouse postings change. The important thing is that the command loads a configured company, fetches jobs, and prints a small summary without writing to the database.

The Greenhouse company list lives in `config/greenhouse_companies.yml`.

### Milestone 2: Store Bronze Raw Payloads

Start Postgres:

```bash
docker compose up -d
```

Create the initial raw table:

```bash
psql postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket -f sql/001_init.sql
```

Store raw Greenhouse payloads for all configured companies:

```bash
ingest-greenhouse
```

The command is idempotent for identical payload versions. Rerunning it should report skipped payloads instead of inserting duplicates.

## Target Stack

- **Ingestion:** Python, scheduled jobs, source-specific connectors
- **Orchestration:** Airflow or a lightweight scheduler for the MVP
- **Storage:** local Parquet/S3-style object storage plus Postgres
- **Transformations:** dbt-style models or SQL transformation scripts
- **Backend:** FastAPI
- **AI:** embeddings, vector search, LLM-powered extraction and RAG
- **Frontend:** Streamlit for MVP, Next.js for a polished product version
- **Infrastructure:** Docker, GitHub Actions, deployable demo environment
