"""Tests for transforming Bronze raw payloads into Silver canonical jobs."""

from datetime import UTC, datetime
from typing import Any

from job_market_intel.canonical_jobs import CanonicalJobRecord, CanonicalJobUpsertResult
from job_market_intel.silver import canonical_job_id
from job_market_intel.transform_canonical_jobs import (
    RawPayloadRow,
    canonical_record_from_raw_payload,
    iter_raw_payload_rows,
    transform_canonical_jobs,
)


class FakeCursor:
    """Small cursor test double that returns configured rows."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def __iter__(self):
        """Return an iterator over fake database rows."""
        return iter(self.rows)


class FakeConnection:
    """Small connection test double that records executed SQL."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.sql: str | None = None

    def execute(self, sql: str) -> FakeCursor:
        """Record the executed statement and return row data."""
        self.sql = sql
        return FakeCursor(self.rows)


def greenhouse_payload() -> dict[str, Any]:
    """Return a realistic Greenhouse-shaped payload fragment."""
    return {
        "id": 123,
        "internal_job_id": 456,
        "requisition_id": "REQ-789",
        "company_name": "Databricks",
        "title": "Senior Backend Software Engineer",
        "language": "en",
        "location": {"name": "San Francisco, CA"},
        "offices": [
            {"name": "San Francisco", "location": "San Francisco, California, United States"}
        ],
        "departments": [{"name": "Engineering"}],
        "absolute_url": "https://boards.greenhouse.io/databricks/jobs/123",
        "first_published": "2026-05-01T12:30:00-05:00",
        "updated_at": "2026-05-02T14:45:00-05:00",
        "content": "<p>Build data systems.</p><p>This role is hybrid in San Francisco.</p>",
    }


def raw_payload_row(payload: dict[str, Any] | None = None) -> RawPayloadRow:
    """Return one Bronze row for transform tests."""
    return RawPayloadRow(
        raw_payload_id="raw-123",
        source_name="greenhouse",
        source_company="Databricks",
        source_job_id="123",
        fetched_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        payload_json=payload or greenhouse_payload(),
    )


def test_canonical_record_from_raw_payload_maps_greenhouse_fields() -> None:
    """A Bronze Greenhouse row should map to a complete canonical job record."""
    record = canonical_record_from_raw_payload(raw_payload_row())

    assert record == CanonicalJobRecord(
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
        description_html="<p>Build data systems.</p><p>This role is hybrid in San Francisco.</p>",
        description_text="Build data systems.\nThis role is hybrid in San Francisco.",
        salary_min=None,
        salary_max=None,
        currency=None,
        first_seen_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        is_active=True,
    )


def test_iter_raw_payload_rows_reads_bronze_rows_in_deterministic_order() -> None:
    """Bronze rows should be read in the order defined by the Milestone 3 spec."""
    connection = FakeConnection(
        rows=[
            {
                "raw_payload_id": "raw-123",
                "source_name": "greenhouse",
                "source_company": "Databricks",
                "source_job_id": "123",
                "fetched_at": datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
                "payload_json": greenhouse_payload(),
            }
        ]
    )

    rows = list(iter_raw_payload_rows(connection))

    assert rows == [raw_payload_row()]
    assert connection.sql is not None
    assert "FROM raw_job_payloads" in connection.sql
    assert "ORDER BY source_name, source_company, source_job_id, fetched_at, raw_payload_id" in (
        connection.sql
    )


def test_transform_canonical_jobs_counts_written_and_skipped_rows() -> None:
    """Transform summary should report read, written, and skipped raw rows."""
    valid_row = raw_payload_row()
    malformed_row = raw_payload_row(payload={"title": "Missing source id"})
    written_records: list[CanonicalJobRecord] = []

    def upsert_job(connection: object, record: CanonicalJobRecord) -> CanonicalJobUpsertResult:
        written_records.append(record)
        return CanonicalJobUpsertResult(job_id=record.job_id, written=True)

    summary = transform_canonical_jobs(
        connection=object(),
        raw_rows=[valid_row, malformed_row],
        upsert_job=upsert_job,
    )

    assert summary.raw_rows_read == 2
    assert summary.canonical_rows_written == 1
    assert summary.raw_rows_skipped == 1
    assert len(written_records) == 1
    assert written_records[0].source_job_id == "123"
