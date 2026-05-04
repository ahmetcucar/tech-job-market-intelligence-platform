# Project Overview

The Tech Job Market Intelligence Platform is a serious end-to-end project that ingests public tech job market data and turns it into career intelligence.

The system continuously collects job postings, stores and models them, extracts useful signals, and lets users explore trends through dashboards, search, and AI-assisted workflows.

## Core Vision

Help engineers understand the labor market, improve their positioning, and make smarter career decisions.

Users should be able to answer questions like:

- Which companies are hiring data engineers in Dallas, Seattle, or California?
- What skills are trending for data engineers, software engineers, and AI engineers?
- What salary ranges exist by city, company, role, and seniority?
- How well does my resume match a specific job posting?
- What skills should I learn next?
- Which companies increased hiring recently?
- Which stack combinations appear in the highest-paying roles?

## Positioning

This project is intentionally broad enough to support three different interview narratives while still feeling like one coherent product.

### Data Engineering Narrative

Demonstrates:

- Multi-source ingestion
- Batch and incremental pipelines
- CDC-style change detection
- Bronze, silver, and gold data layers
- Fact and dimension modeling
- dbt transformations
- Airflow orchestration
- Data quality checks and observability

### Software Engineering Narrative

Demonstrates:

- Backend API design
- Search services
- User accounts and authentication
- Async workers
- Query performance optimization
- Caching
- Dockerized deployment
- CI/CD
- Scalable system design

### AI Engineering Narrative

Demonstrates:

- LLM integrations
- Skill and seniority extraction
- Embeddings-based semantic search
- Resume-to-job matching
- RAG over job market data
- Recommendation systems
- Evaluation pipelines

## MVP

The MVP should focus on the smallest useful version of the product:

- Daily ingestion of public job postings
- Cleaned searchable database
- Dashboard with hiring trends
- Filters by role, city, company, skill, salary, and seniority
- Skill extraction from job descriptions
- Basic resume-to-job match scoring

## Later Features

- Personalized job recommendations
- Skill gap analysis
- Saved searches and alerts
- AI career copilot chat
- Company hiring velocity analysis
- Market reports by role, region, or technology

## Definition of Real

This project should avoid feeling like a toy demo. The finished version should include:

- Live demo
- Public GitHub repo
- Clear documentation
- Screenshots
- Architecture diagram
- Tests
- Data quality checks
- Sample metrics
- Deployed endpoint or reproducible local environment
