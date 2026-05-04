# Product Requirements

The Tech Job Market Intelligence Platform is not a job board clone. It is a data product, software product, and AI product built around one valuable problem: helping engineers understand the labor market and act intelligently in their careers.

## Target Users

- Engineers looking for new roles
- Career switchers trying to understand skill demand
- Job seekers comparing cities, companies, and compensation
- Engineers tailoring resumes to specific postings
- Hiring market researchers who want trend data

## Core Jobs To Be Done

- Find companies hiring for a specific role, location, and tech stack.
- Understand which skills are becoming more or less valuable.
- Compare salary ranges across cities, companies, seniority levels, and roles.
- Evaluate whether a resume is a strong match for a job posting.
- Identify skill gaps and create a learning plan.
- Track companies that are increasing or decreasing hiring activity.

## Primary User Flows

### Explore Market Trends

1. User selects a role, location, date range, and optional skills.
2. Platform shows hiring volume, top companies, top skills, salary ranges, and remote/on-site mix.
3. User drills into companies, roles, or skills to inspect supporting postings.

### Search Jobs

1. User enters a structured or natural-language query.
2. Platform returns ranked postings using keyword filters and semantic search.
3. User filters by company, salary, location, seniority, remote status, and skill.

Example queries:

- "backend jobs using Go at startups"
- "high-paying analytics engineering roles remote"
- "data engineering roles in Dallas requiring Spark"

### Match Resume To Job

1. User uploads or pastes a resume.
2. User selects a target job posting.
3. Platform compares the resume to the posting.
4. Platform returns a match score, matched skills, missing skills, seniority fit, and suggested resume improvements.

### Ask AI Career Questions

1. User asks a question about jobs, skills, companies, or career positioning.
2. AI retrieves relevant structured data and job descriptions.
3. AI responds with citations back to matching postings, trends, or extracted signals.

Example questions:

- What am I missing for this role?
- Which companies fit my background?
- What should I learn over the next 90 days for a staff data engineer path?
- Which skills are rising fastest for backend engineers?

## MVP Features

- Daily job posting ingestion
- Searchable job database
- Role, city, company, salary, seniority, and skill filters
- Market trend dashboard
- Skill extraction from job descriptions
- Resume-to-job matching
- Basic AI question answering over job data

## Future Features

- Saved searches
- Email or Slack alerts
- Personalized job recommendations
- Skill gap analysis
- Company hiring velocity tracker
- Role-specific market reports
- Resume bullet rewrite suggestions
- User accounts and profile history
