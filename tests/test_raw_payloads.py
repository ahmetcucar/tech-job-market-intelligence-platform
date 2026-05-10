"""Tests for inserting Bronze raw payload rows."""

from datetime import UTC, datetime
from typing import Any

from job_market_intel.bronze import raw_payload_id, stable_payload_hash
from job_market_intel.raw_payloads import insert_raw_job_payload


class FakeCursor:
    """Small cursor test double that exposes psycopg's rowcount behavior."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class FakeConnection:
    """Small connection test double that records the SQL and parameters."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount
        self.sql: str | None = None
        self.params: dict[str, Any] | None = None

    def execute(self, sql: str, params: dict[str, Any]) -> FakeCursor:
        """Record the executed statement and return a cursor-like object."""
        self.sql = sql
        self.params = params
        return FakeCursor(self.rowcount)


def test_insert_raw_job_payload_builds_identity_and_insert_statement() -> None:
    """A new raw payload should be inserted with deterministic Bronze identity fields."""
    payload = {"id": 123, "title": "Data Engineer"}
    fetched_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    connection = FakeConnection(rowcount=1)

    result = insert_raw_job_payload(
        connection,
        source_name="greenhouse",
        source_company="Databricks",
        source_job_id="123",
        payload=payload,
        fetched_at=fetched_at,
    )

    expected_hash = stable_payload_hash(payload)
    assert result.inserted is True
    assert result.payload_hash == expected_hash
    assert result.raw_payload_id == raw_payload_id("greenhouse", "Databricks", "123", expected_hash)
    assert connection.sql is not None
    assert "ON CONFLICT DO NOTHING" in connection.sql
    assert connection.params is not None
    assert connection.params["source_name"] == "greenhouse"
    assert connection.params["source_company"] == "Databricks"
    assert connection.params["source_job_id"] == "123"
    assert connection.params["fetched_at"] == fetched_at


def test_insert_raw_job_payload_reports_skipped_duplicate() -> None:
    """A duplicate raw payload version should report inserted=False."""
    connection = FakeConnection(rowcount=0)

    result = insert_raw_job_payload(
        connection,
        source_name="greenhouse",
        source_company="Databricks",
        source_job_id="123",
        payload={"id": 123},
        fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert result.inserted is False
