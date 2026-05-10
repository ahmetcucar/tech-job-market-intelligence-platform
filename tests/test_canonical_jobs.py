"""Tests for upserting Silver canonical job records."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from job_market_intel.canonical_jobs import CanonicalJobRecord, upsert_canonical_job
from job_market_intel.silver import canonical_job_id


class FakeCursor:
    """Small cursor test double that exposes psycopg's rowcount behavior."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class FakeConnection:
    """Small connection test double that records SQL and parameters."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount
        self.sql: str | None = None
        self.params: dict[str, Any] | None = None

    def execute(self, sql: str, params: dict[str, Any]) -> FakeCursor:
        """Record the executed statement and return a cursor-like object."""
        self.sql = sql
        self.params = params
        return FakeCursor(self.rowcount)


def canonical_record() -> CanonicalJobRecord:
    """Return one complete canonical job record for upsert tests."""
    first_seen_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    last_seen_at = datetime(2026, 5, 10, 12, 5, tzinfo=UTC)

    return CanonicalJobRecord(
        job_id=canonical_job_id("greenhouse", "Databricks", "123"),
        source_name="greenhouse",
        source_company="Databricks",
        source_job_id="123",
        source_internal_job_id="456",
        requisition_id="REQ-789",
        company_name="Databricks",
        title="Senior Backend Software Engineer",
        normalized_title="backend engineer",
        source_language="en",
        detected_language=None,
        location_name="San Francisco, CA",
        office_location="San Francisco, California, United States",
        department_name="Engineering",
        remote_type="hybrid",
        seniority="senior",
        job_url="https://boards.greenhouse.io/databricks/jobs/123",
        source_published_at=datetime(2026, 5, 1, 17, 30, tzinfo=UTC),
        source_updated_at=datetime(2026, 5, 2, 19, 45, tzinfo=UTC),
        description_html="<p>Build data systems.</p>",
        description_text="Build data systems.",
        salary_min=Decimal("120000"),
        salary_max=Decimal("180000"),
        currency="USD",
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        is_active=True,
    )


def test_upsert_canonical_job_builds_conflict_update_statement() -> None:
    """Canonical jobs should upsert by source identity while preserving first_seen_at."""
    connection = FakeConnection(rowcount=1)

    result = upsert_canonical_job(connection, canonical_record())

    assert result.written is True
    assert connection.sql is not None
    assert "ON CONFLICT (source_name, source_company, source_job_id)" in connection.sql
    assert "DO UPDATE SET" in connection.sql
    update_clause = connection.sql.split("DO UPDATE SET", maxsplit=1)[1]
    assert "first_seen_at" not in update_clause
    assert "last_seen_at = EXCLUDED.last_seen_at" in update_clause


def test_upsert_canonical_job_passes_all_record_fields_as_params() -> None:
    """Canonical upsert params should include identity, normalized fields, and nullable fields."""
    connection = FakeConnection(rowcount=1)
    record = canonical_record()

    upsert_canonical_job(connection, record)

    assert connection.params is not None
    assert connection.params["job_id"] == canonical_job_id("greenhouse", "Databricks", "123")
    assert connection.params["source_name"] == "greenhouse"
    assert connection.params["source_company"] == "Databricks"
    assert connection.params["source_job_id"] == "123"
    assert connection.params["normalized_title"] == "backend engineer"
    assert connection.params["remote_type"] == "hybrid"
    assert connection.params["seniority"] == "senior"
    assert connection.params["salary_min"] == Decimal("120000")
    assert connection.params["salary_max"] == Decimal("180000")
    assert connection.params["detected_language"] is None
    assert connection.params["first_seen_at"] == record.first_seen_at
    assert connection.params["last_seen_at"] == record.last_seen_at


def test_upsert_canonical_job_reports_not_written_when_rowcount_is_zero() -> None:
    """Unexpected zero-row writes should be visible to the caller."""
    connection = FakeConnection(rowcount=0)

    result = upsert_canonical_job(connection, canonical_record())

    assert result.written is False
