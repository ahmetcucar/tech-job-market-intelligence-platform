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

    def __init__(self, rowcounts: int | list[int]) -> None:
        self.rowcounts = rowcounts if isinstance(rowcounts, list) else [rowcounts]
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def execute(self, sql: str, params: dict[str, Any]) -> FakeCursor:
        """Record the executed statement and return a cursor-like object."""
        self.statements.append((sql, params))
        return FakeCursor(self.rowcounts[len(self.statements) - 1])


def test_insert_raw_job_payload_builds_identity_and_insert_statement() -> None:
    """A new raw payload should be inserted with deterministic Bronze identity fields."""
    payload = {"id": 123, "title": "Data Engineer"}
    fetched_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    connection = FakeConnection(rowcounts=1)

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
    assert len(connection.statements) == 1
    insert_sql, insert_params = connection.statements[0]
    assert "ON CONFLICT (source_name, source_company, source_job_id, payload_hash)" in insert_sql
    assert "DO NOTHING" in insert_sql
    assert insert_params["source_name"] == "greenhouse"
    assert insert_params["source_company"] == "Databricks"
    assert insert_params["source_job_id"] == "123"
    assert insert_params["fetched_at"] == fetched_at
    assert insert_params["last_seen_at"] == fetched_at


def test_insert_raw_job_payload_updates_last_seen_for_skipped_duplicate() -> None:
    """A duplicate raw payload version should advance last_seen_at metadata."""
    fetched_at = datetime(2026, 5, 10, 13, 0, tzinfo=UTC)
    connection = FakeConnection(rowcounts=[0, 1])

    result = insert_raw_job_payload(
        connection,
        source_name="greenhouse",
        source_company="Databricks",
        source_job_id="123",
        payload={"id": 123},
        fetched_at=fetched_at,
    )

    assert result.inserted is False
    assert len(connection.statements) == 2
    update_sql, update_params = connection.statements[1]
    assert "UPDATE raw_job_payloads" in update_sql
    assert "last_seen_at = GREATEST(last_seen_at, %(last_seen_at)s)" in update_sql
    assert update_params["last_seen_at"] == fetched_at
