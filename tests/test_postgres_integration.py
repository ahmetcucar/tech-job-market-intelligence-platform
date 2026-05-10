"""Postgres-backed integration tests for Bronze storage behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from os import environ
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from job_market_intel.db import connect
from job_market_intel.ingest_greenhouse import ingest_greenhouse_companies
from job_market_intel.raw_payloads import insert_raw_job_payload
from job_market_intel.transform_canonical_jobs import transform_canonical_jobs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = PROJECT_ROOT / "sql" / "001_init.sql"
CANONICAL_JOBS_SQL = PROJECT_ROOT / "sql" / "002_canonical_jobs.sql"
TEST_DATABASE_ENV_VAR = "JOB_MARKET_TEST_DATABASE_URL"


def open_test_connection() -> psycopg.Connection:
    """Open an explicit test database connection or skip when it is unavailable."""
    test_database_url = environ.get(TEST_DATABASE_ENV_VAR)
    if not test_database_url:
        pytest.skip(f"{TEST_DATABASE_ENV_VAR} is not set")

    try:
        return connect(test_database_url)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres integration database is unavailable: {exc}")


def ensure_schema(connection: psycopg.Connection) -> None:
    """Ensure the Bronze and Silver tables exist using checked-in SQL files."""
    connection.execute(INIT_SQL.read_text(encoding="utf-8"))
    connection.execute(CANONICAL_JOBS_SQL.read_text(encoding="utf-8"))
    connection.commit()


def cleanup_company(connection: psycopg.Connection, source_company: str) -> None:
    """Delete Bronze and Silver rows for one integration-test company name."""
    connection.execute(
        "DELETE FROM canonical_jobs WHERE source_company = %s",
        (source_company,),
    )
    connection.execute(
        "DELETE FROM raw_job_payloads WHERE source_company = %s",
        (source_company,),
    )
    connection.commit()


def count_company_rows(connection: psycopg.Connection, source_company: str) -> int:
    """Count Bronze rows stored for one integration-test company name."""
    cursor = connection.execute(
        "SELECT count(*) FROM raw_job_payloads WHERE source_company = %s",
        (source_company,),
    )
    return cursor.fetchone()[0]


def canonical_company_row(connection: psycopg.Connection, source_company: str) -> tuple:
    """Fetch canonical row metadata for one integration-test company name."""
    cursor = connection.execute(
        """
        SELECT count(*), min(first_seen_at), max(last_seen_at), max(title)
        FROM canonical_jobs
        WHERE source_company = %s
        """,
        (source_company,),
    )
    return cursor.fetchone()


def test_insert_raw_job_payload_uses_real_postgres_idempotency() -> None:
    """Real Postgres should insert new versions and skip identical duplicates."""
    source_company = f"IntegrationRawPayloads-{uuid4()}"
    payload = {"id": "integration-job-1", "title": "Data Engineer"}
    changed_payload = {"id": "integration-job-1", "title": "Senior Data Engineer"}
    fetched_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)

    with open_test_connection() as connection:
        ensure_schema(connection)
        cleanup_company(connection, source_company)

        first = insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=payload,
            fetched_at=fetched_at,
        )
        duplicate = insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=payload,
            fetched_at=fetched_at,
        )
        changed = insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=changed_payload,
            fetched_at=fetched_at,
        )
        connection.commit()

        assert first.inserted is True
        assert duplicate.inserted is False
        assert changed.inserted is True
        assert count_company_rows(connection, source_company) == 2

        cleanup_company(connection, source_company)


def test_ingest_greenhouse_keeps_committed_company_when_later_company_fails() -> None:
    """A later company failure should not roll back an earlier committed company."""
    successful_company = f"IntegrationCommitted-{uuid4()}"
    failing_company = f"IntegrationRolledBack-{uuid4()}"
    companies = [
        {"name": successful_company, "board_token": "successful"},
        {"name": failing_company, "board_token": "failing"},
    ]

    def fetch_jobs(board_token: str) -> list[dict[str, str]]:
        return [{"id": board_token, "title": "Data Engineer"}]

    def insert_then_fail_for_second_company(
        connection: psycopg.Connection,
        *,
        source_name: str,
        source_company: str,
        source_job_id: str,
        payload: dict[str, str],
        fetched_at: datetime,
    ):
        result = insert_raw_job_payload(
            connection,
            source_name=source_name,
            source_company=source_company,
            source_job_id=source_job_id,
            payload=payload,
            fetched_at=fetched_at,
        )
        if source_company == failing_company:
            raise RuntimeError("simulated later company failure")
        return result

    with pytest.raises(RuntimeError, match="simulated later company failure"):
        with open_test_connection() as connection:
            ensure_schema(connection)
            cleanup_company(connection, successful_company)
            cleanup_company(connection, failing_company)
            ingest_greenhouse_companies(
                connection=connection,
                companies=companies,
                fetch_jobs=fetch_jobs,
                insert_job=insert_then_fail_for_second_company,
            )

    with open_test_connection() as connection:
        assert count_company_rows(connection, successful_company) == 1
        assert count_company_rows(connection, failing_company) == 0
        cleanup_company(connection, successful_company)
        cleanup_company(connection, failing_company)


def test_transform_canonical_jobs_updates_existing_job_for_new_raw_version() -> None:
    """Canonical transform reruns should update a source job instead of duplicating it."""
    source_company = f"IntegrationCanonical-{uuid4()}"
    first_payload = {
        "id": "integration-job-1",
        "title": "Backend Engineer",
        "company_name": source_company,
        "location": {"name": "Remote - US"},
        "content": "<p>Build APIs.</p>",
    }
    changed_payload = {
        "id": "integration-job-1",
        "title": "Senior Backend Engineer",
        "company_name": source_company,
        "location": {"name": "Remote - US"},
        "content": "<p>Build APIs and mentor engineers.</p>",
    }

    with open_test_connection() as connection:
        ensure_schema(connection)
        cleanup_company(connection, source_company)

        insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=first_payload,
            fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        )
        insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=changed_payload,
            fetched_at=datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
        )
        connection.commit()

        first_summary = transform_canonical_jobs(connection, source_company=source_company)
        connection.commit()
        first_row = canonical_company_row(connection, source_company)

        second_summary = transform_canonical_jobs(connection, source_company=source_company)
        connection.commit()
        second_row = canonical_company_row(connection, source_company)

        assert first_summary.raw_rows_read == 2
        assert first_summary.canonical_rows_written == 2
        assert first_summary.raw_rows_skipped == 0
        assert second_summary.raw_rows_read == 2
        assert second_summary.canonical_rows_written == 2
        assert second_summary.raw_rows_skipped == 0
        assert first_row == (
            1,
            datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
            datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
            "Senior Backend Engineer",
        )
        assert second_row == first_row

        cleanup_company(connection, source_company)


def test_transform_canonical_jobs_uses_duplicate_payload_last_seen_at() -> None:
    """Canonical last_seen_at should advance when the same payload is observed again."""
    source_company = f"IntegrationCanonicalSeen-{uuid4()}"
    payload = {
        "id": "integration-job-1",
        "title": "Backend Engineer",
        "company_name": source_company,
        "location": {"name": "Remote - US"},
        "content": "<p>Build APIs.</p>",
    }

    with open_test_connection() as connection:
        ensure_schema(connection)
        cleanup_company(connection, source_company)

        first = insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=payload,
            fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        )
        duplicate = insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=payload,
            fetched_at=datetime(2026, 5, 10, 14, 0, tzinfo=UTC),
        )
        connection.commit()

        summary = transform_canonical_jobs(connection, source_company=source_company)
        connection.commit()
        row = canonical_company_row(connection, source_company)

        assert first.inserted is True
        assert duplicate.inserted is False
        assert count_company_rows(connection, source_company) == 1
        assert summary.raw_rows_read == 1
        assert summary.canonical_rows_written == 1
        assert summary.raw_rows_skipped == 0
        assert row == (
            1,
            datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
            datetime(2026, 5, 10, 14, 0, tzinfo=UTC),
            "Backend Engineer",
        )

        cleanup_company(connection, source_company)


def test_transform_canonical_jobs_uses_latest_observed_payload_version() -> None:
    """Canonical current state should follow the raw version seen most recently."""
    source_company = f"IntegrationCanonicalReobserved-{uuid4()}"
    first_payload = {
        "id": "integration-job-1",
        "title": "Backend Engineer",
        "company_name": source_company,
        "location": {"name": "Remote - US"},
        "content": "<p>Build APIs.</p>",
    }
    changed_payload = {
        "id": "integration-job-1",
        "title": "Senior Backend Engineer",
        "company_name": source_company,
        "location": {"name": "Remote - US"},
        "content": "<p>Build APIs and mentor engineers.</p>",
    }

    with open_test_connection() as connection:
        ensure_schema(connection)
        cleanup_company(connection, source_company)

        insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=first_payload,
            fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        )
        insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=changed_payload,
            fetched_at=datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
        )
        insert_raw_job_payload(
            connection,
            source_name="greenhouse",
            source_company=source_company,
            source_job_id="integration-job-1",
            payload=first_payload,
            fetched_at=datetime(2026, 5, 10, 14, 0, tzinfo=UTC),
        )
        connection.commit()

        summary = transform_canonical_jobs(connection, source_company=source_company)
        connection.commit()
        row = canonical_company_row(connection, source_company)

        assert count_company_rows(connection, source_company) == 2
        assert summary.raw_rows_read == 2
        assert summary.canonical_rows_written == 2
        assert summary.raw_rows_skipped == 0
        assert row == (
            1,
            datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
            datetime(2026, 5, 10, 14, 0, tzinfo=UTC),
            "Backend Engineer",
        )

        cleanup_company(connection, source_company)
