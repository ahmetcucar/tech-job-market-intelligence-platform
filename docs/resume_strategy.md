# Resume Positioning

This project should be described differently depending on the role being targeted. The goal is to present one polished project as evidence that you can build modern data and AI systems end to end.

## Data Engineering Angle

Emphasize the data foundation: ingestion, orchestration, data quality, modeling, and analytics.

What to build:

- Multi-source ingestion from company career pages, Greenhouse, Lever, APIs, and salary datasets
- Scheduled pipelines with retries and source freshness tracking
- Incremental loading using payload hashes and first-seen/last-seen timestamps
- Bronze, silver, and gold data layers
- Dimensional models such as `fact_job_postings`, `dim_company`, `dim_location`, `dim_skill`, and `dim_time`
- Data quality checks for freshness, duplicates, schema drift, and missing salary fields

Example resume bullets:

- Built ETL pipelines ingesting public job posting data from multiple ATS sources into a modeled analytics warehouse.
- Designed incremental loading logic using source IDs, payload hashes, and first-seen/last-seen tracking to detect new, changed, and closed postings.
- Modeled job market data into fact and dimension tables supporting skill demand, salary, company, and location trend analysis.
- Implemented data quality checks for freshness, duplicate postings, schema drift, and missing salary fields.

## Software Engineering Angle

Emphasize the application layer: APIs, search, performance, background jobs, and deployment.

What to build:

- FastAPI backend
- Job search APIs
- Analytics endpoints
- Resume upload workflow
- Async ingestion and enrichment workers
- Pagination, caching, and query optimization
- Dockerized local environment
- CI checks and deployment workflow

Example resume bullets:

- Designed backend APIs powering job search, market analytics, resume matching, and AI-assisted career workflows.
- Built async worker services for ingestion, enrichment, embedding generation, and resume matching.
- Optimized search and analytics endpoints with indexed queries, pagination, and caching.
- Containerized the platform with Docker and added CI checks for tests, linting, and build validation.

## AI Engineering Angle

Emphasize practical AI: extraction, retrieval, recommendations, and evaluation.

What to build:

- Skill extraction from job descriptions
- Seniority classification
- Embeddings-based semantic search
- Resume-to-job matching
- RAG assistant over job postings and trend data
- Evaluation sets for extraction, matching, and grounded answers

Example resume bullets:

- Built an LLM-powered job intelligence assistant using RAG over structured job market data and raw job descriptions.
- Developed embeddings-based semantic search for natural-language job discovery and resume-to-job matching.
- Automated skill extraction from raw job postings using a hybrid rules and LLM pipeline with confidence scoring.
- Created evaluation checks for extraction quality, search relevance, match explanations, and grounded AI responses.

## Best Overall Framing

Use this sentence when introducing the project:

> Built an end-to-end job market intelligence platform that ingests public tech job postings, models hiring trends, and uses AI to power semantic search, resume matching, and career recommendations.

