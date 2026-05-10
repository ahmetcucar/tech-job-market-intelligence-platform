"""Postgres-backed integration tests for Bronze storage behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from job_market_intel.db import connect
from job_market_intel.ingest_greenhouse import ingest_greenhouse_companies
from job_market_intel.raw_payloads import insert_raw_job_payload


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_job_payloads (
    raw_payload_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_company TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    UNIQUE (source_name, source_company, source_job_id, payload_hash)
);
"""


def open_test_connection() -> psycopg.Connection:
    """Open a test database connection or skip when local Postgres is unavailable."""
    try:
        return connect()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres integration database is unavailable: {exc}")


def ensure_schema(connection: psycopg.Connection) -> None:
    """Ensure the Bronze table exists for integration tests."""
    connection.execute(SCHEMA_SQL)
    connection.commit()


def cleanup_company(connection: psycopg.Connection, source_company: str) -> None:
    """Delete rows for one integration-test company name."""
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
