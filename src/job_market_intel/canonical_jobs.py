"""Postgres writes for Silver canonical job records.

This module owns the `canonical_jobs` upsert path. It keeps canonical write
behavior separate from Bronze reading and source-specific mapping so the
Silver table has one clear database boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol


class ConnectionLike(Protocol):
    """Minimal connection behavior needed to upsert a canonical job row."""

    def execute(self, sql: str, params: dict[str, Any]) -> Any:
        """Execute a SQL statement and return a cursor-like object."""


@dataclass(frozen=True)
class CanonicalJobRecord:
    """Canonical Silver representation of one source job."""

    job_id: str
    source_name: str
    source_company: str
    source_job_id: str
    source_internal_job_id: str | None
    requisition_id: str | None
    company_name: str | None
    title: str | None
    normalized_title: str
    source_language: str | None
    detected_language: str | None
    location_name: str | None
    office_location: str | None
    department_name: str | None
    remote_type: str
    seniority: str
    job_url: str | None
    source_published_at: datetime | None
    source_updated_at: datetime | None
    description_html: str | None
    description_text: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    currency: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool


@dataclass(frozen=True)
class CanonicalJobUpsertResult:
    """Result metadata for one canonical job upsert attempt."""

    job_id: str
    written: bool


def upsert_canonical_job(
    connection: ConnectionLike,
    record: CanonicalJobRecord,
) -> CanonicalJobUpsertResult:
    """Insert or update one canonical job row by source identity.

    Args:
        connection: Open database connection with an `execute` method.
        record: Complete canonical job record to write.

    Returns:
        Upsert metadata with the canonical job ID and whether Postgres reported
        that a row was written.

    Existing rows keep the earliest known `first_seen_at`; all source-derived
    fields and `last_seen_at` are refreshed from the new record.
    """
    cursor = connection.execute(
        """
        INSERT INTO canonical_jobs (
            job_id,
            source_name,
            source_company,
            source_job_id,
            source_internal_job_id,
            requisition_id,
            company_name,
            title,
            normalized_title,
            source_language,
            detected_language,
            location_name,
            office_location,
            department_name,
            remote_type,
            seniority,
            job_url,
            source_published_at,
            source_updated_at,
            description_html,
            description_text,
            salary_min,
            salary_max,
            currency,
            first_seen_at,
            last_seen_at,
            is_active
        )
        VALUES (
            %(job_id)s,
            %(source_name)s,
            %(source_company)s,
            %(source_job_id)s,
            %(source_internal_job_id)s,
            %(requisition_id)s,
            %(company_name)s,
            %(title)s,
            %(normalized_title)s,
            %(source_language)s,
            %(detected_language)s,
            %(location_name)s,
            %(office_location)s,
            %(department_name)s,
            %(remote_type)s,
            %(seniority)s,
            %(job_url)s,
            %(source_published_at)s,
            %(source_updated_at)s,
            %(description_html)s,
            %(description_text)s,
            %(salary_min)s,
            %(salary_max)s,
            %(currency)s,
            %(first_seen_at)s,
            %(last_seen_at)s,
            %(is_active)s
        )
        ON CONFLICT (source_name, source_company, source_job_id)
        DO UPDATE SET
            source_internal_job_id = EXCLUDED.source_internal_job_id,
            requisition_id = EXCLUDED.requisition_id,
            company_name = EXCLUDED.company_name,
            title = EXCLUDED.title,
            normalized_title = EXCLUDED.normalized_title,
            source_language = EXCLUDED.source_language,
            detected_language = EXCLUDED.detected_language,
            location_name = EXCLUDED.location_name,
            office_location = EXCLUDED.office_location,
            department_name = EXCLUDED.department_name,
            remote_type = EXCLUDED.remote_type,
            seniority = EXCLUDED.seniority,
            job_url = EXCLUDED.job_url,
            source_published_at = EXCLUDED.source_published_at,
            source_updated_at = EXCLUDED.source_updated_at,
            description_html = EXCLUDED.description_html,
            description_text = EXCLUDED.description_text,
            salary_min = EXCLUDED.salary_min,
            salary_max = EXCLUDED.salary_max,
            currency = EXCLUDED.currency,
            first_seen_at = LEAST(canonical_jobs.first_seen_at, EXCLUDED.first_seen_at),
            last_seen_at = EXCLUDED.last_seen_at,
            is_active = EXCLUDED.is_active
        """,
        asdict(record),
    )

    return CanonicalJobUpsertResult(job_id=record.job_id, written=cursor.rowcount == 1)
