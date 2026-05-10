# Database Environment Separation Design

## Goal

Separate development, test, and production data so database work can be verified
without risking local exploration data or future production data.

This should be the next infrastructure milestone after the current canonical jobs
work. It is intentionally separate from Milestone 3 because it changes local database
setup and test configuration rather than canonical transformation logic.

## Decision

Use three logical databases:

- `jobmarket_dev` for local manual ingestion, exploration, and future Streamlit work
- `jobmarket_test` for automated integration tests only
- production Postgres for deployed or scheduled production runs

Local Docker should provide `jobmarket_dev` and `jobmarket_test`. Production should
not be represented by a local Docker database; it should be a separate managed
database URL when the project reaches deployment.

## Current State

The project currently defaults to one local Docker database:

```text
postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket
```

Integration tests can point at that same database through:

```text
JOB_MARKET_TEST_DATABASE_URL=postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket
```

Tests reduce risk by using generated company names and cleaning up their own rows.
That is acceptable during early MVP work, but it still means test data and development
data can share one database.

## Target Configuration

Local development should use:

```text
DATABASE_URL=postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket_dev
```

Integration tests should use:

```text
JOB_MARKET_TEST_DATABASE_URL=postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket_test
```

Future production should use a separate production `DATABASE_URL` supplied by the
deployment environment.

## Scope

This milestone should include:

- update local Docker/Postgres initialization so both `jobmarket_dev` and
  `jobmarket_test` exist
- update `.env.example` with the local development database URL
- update test documentation to point `JOB_MARKET_TEST_DATABASE_URL` at
  `jobmarket_test`
- ensure integration tests apply schema files to `jobmarket_test`
- keep application code selecting databases by explicit URL or environment variable

This milestone should not add a production deployment, managed database provisioning,
or a full migration framework. Schema migration tracking can be considered later if
the ordered SQL-file approach becomes too limited.

## Why Three Databases

Two databases, development and production, would still leave automated tests sharing
state with development data. That is too risky once integration tests become more
comprehensive.

Three databases keep responsibilities clear:

```text
dev   -> human exploration and local product work
test  -> automated tests that can insert, delete, and reset data
prod  -> real production data
```

The test database should be disposable. The development database should preserve local
work and exploratory ingestions. The production database should be isolated from both.

## Verification

This milestone is done when:

- Docker Postgres starts with both `jobmarket_dev` and `jobmarket_test` available
- application commands default to or document `jobmarket_dev` for local development
- integration tests run against `jobmarket_test`
- applying checked-in SQL files works against both local databases
- test cleanup no longer needs to protect local development data as carefully because
  tests do not share the development database
