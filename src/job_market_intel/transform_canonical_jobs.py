"""Transform Bronze raw payload rows into Silver canonical job records.

This module reads stored raw source payloads, maps Greenhouse job fields into
canonical records, and upserts those records into the Silver table. Bronze rows
remain unchanged.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from job_market_intel.canonical_jobs import (
    CanonicalJobRecord,
    CanonicalJobUpsertResult,
    upsert_canonical_job,
)
from job_market_intel.db import connect
from job_market_intel.silver import (
    canonical_job_id,
    classify_remote_type,
    description_text_from_html,
    extract_department_name,
    extract_description_html,
    extract_job_url,
    extract_location_name,
    extract_office_location,
    normalize_seniority,
    normalize_title,
    parse_source_timestamp,
)


class ConnectionLike(Protocol):
    """Minimal connection behavior needed by the canonical transform."""

    def execute(self, sql: str) -> Any:
        """Execute a SQL statement and return an iterable cursor-like object."""

    def commit(self) -> None:
        """Commit the current transaction."""

    def rollback(self) -> None:
        """Roll back the current transaction."""


class UpsertCanonicalJob(Protocol):
    """Callable shape for upserting one canonical job record."""

    def __call__(
        self,
        connection: object,
        record: CanonicalJobRecord,
    ) -> CanonicalJobUpsertResult:
        """Upsert a canonical job record and return write metadata."""


@dataclass(frozen=True)
class RawPayloadRow:
    """Bronze row fields needed to build one canonical job record."""

    raw_payload_id: str
    source_name: str
    source_company: str
    source_job_id: str
    fetched_at: datetime
    payload_json: dict[str, Any]


@dataclass(frozen=True)
class TransformSummary:
    """Counts produced by one Bronze-to-Silver transform run."""

    raw_rows_read: int
    canonical_rows_written: int
    raw_rows_skipped: int


def canonical_record_from_raw_payload(row: RawPayloadRow) -> CanonicalJobRecord:
    """Map one Bronze raw payload row into a canonical Silver job record.

    Args:
        row: Bronze row containing source identity, fetch timestamp, and raw
            Greenhouse payload JSON.

    Returns:
        A complete canonical job record ready for database upsert.

    Raises:
        ValueError: If the Bronze row does not contain a usable source job ID
            and cannot be safely assigned canonical identity.
    """
    source_job_id = _clean_optional_string(row.source_job_id)
    if source_job_id is None:
        raise ValueError("raw row does not contain a usable source job ID")

    description_html = extract_description_html(row.payload_json)
    description_text = description_text_from_html(description_html)
    location_name = extract_location_name(row.payload_json)
    office_location = extract_office_location(row.payload_json)
    title = _clean_optional_string(row.payload_json.get("title"))

    return CanonicalJobRecord(
        job_id=canonical_job_id(row.source_name, row.source_company, source_job_id),
        source_name=row.source_name,
        source_company=row.source_company,
        source_job_id=source_job_id,
        source_internal_job_id=_clean_optional_string(row.payload_json.get("internal_job_id")),
        requisition_id=_clean_optional_string(row.payload_json.get("requisition_id")),
        company_name=_clean_optional_string(row.payload_json.get("company_name")),
        title=title,
        normalized_title=normalize_title(title),
        source_language=_clean_optional_string(row.payload_json.get("language")),
        detected_language=None,
        location_name=location_name,
        office_location=office_location,
        department_name=extract_department_name(row.payload_json),
        remote_type=classify_remote_type(title, location_name, office_location, description_text),
        seniority=normalize_seniority(title),
        job_url=extract_job_url(row.payload_json),
        source_published_at=parse_source_timestamp(
            _clean_optional_string(row.payload_json.get("first_published"))
        ),
        source_updated_at=parse_source_timestamp(_clean_optional_string(row.payload_json.get("updated_at"))),
        description_html=description_html,
        description_text=description_text,
        salary_min=None,
        salary_max=None,
        currency=None,
        first_seen_at=row.fetched_at,
        last_seen_at=row.fetched_at,
        is_active=True,
    )


def iter_raw_payload_rows(connection: ConnectionLike) -> Iterable[RawPayloadRow]:
    """Yield Bronze raw payload rows in deterministic transform order."""
    cursor = connection.execute(
        """
        SELECT
            raw_payload_id,
            source_name,
            source_company,
            source_job_id,
            fetched_at,
            payload_json
        FROM raw_job_payloads
        ORDER BY source_name, source_company, source_job_id, fetched_at, raw_payload_id
        """
    )
    for row in cursor:
        yield _raw_payload_row_from_database_row(row)


def transform_canonical_jobs(
    connection: object,
    *,
    raw_rows: Iterable[RawPayloadRow] | None = None,
    upsert_job: UpsertCanonicalJob = upsert_canonical_job,
) -> TransformSummary:
    """Transform Bronze raw rows into canonical jobs and upsert them.

    Args:
        connection: Open database connection used to read Bronze rows and write
            canonical rows.
        raw_rows: Optional iterable of raw rows for tests. When omitted, rows
            are read from `raw_job_payloads`.
        upsert_job: Function used to write one canonical job record.

    Returns:
        Summary counts for raw rows read, canonical rows written, and raw rows
        skipped because they could not be safely mapped.
    """
    rows = raw_rows if raw_rows is not None else iter_raw_payload_rows(connection)
    raw_rows_read = 0
    canonical_rows_written = 0
    raw_rows_skipped = 0

    for row in rows:
        raw_rows_read += 1
        try:
            record = canonical_record_from_raw_payload(row)
        except ValueError:
            raw_rows_skipped += 1
            continue

        result = upsert_job(connection, record)
        if result.written:
            canonical_rows_written += 1

    return TransformSummary(
        raw_rows_read=raw_rows_read,
        canonical_rows_written=canonical_rows_written,
        raw_rows_skipped=raw_rows_skipped,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for the canonical jobs transform."""
    parser = argparse.ArgumentParser(
        description="Transform Bronze raw job payloads into Silver canonical jobs.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres connection URL. Defaults to DATABASE_URL or the local Docker database.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Run the Bronze-to-Silver canonical jobs transform."""
    args = parse_args()

    with connect(args.database_url) as connection:
        try:
            summary = transform_canonical_jobs(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    print(f"Raw rows read: {summary.raw_rows_read}")
    print(f"Canonical rows written: {summary.canonical_rows_written}")
    print(f"Raw rows skipped: {summary.raw_rows_skipped}")


def _clean_optional_string(value: Any) -> str | None:
    """Return a stripped string representation or None for missing values."""
    if value is None:
        return None
    stripped_value = str(value).strip()
    return stripped_value or None


def _raw_payload_row_from_database_row(row: Any) -> RawPayloadRow:
    """Convert a database row object into a `RawPayloadRow`."""
    if isinstance(row, dict):
        return RawPayloadRow(
            raw_payload_id=row["raw_payload_id"],
            source_name=row["source_name"],
            source_company=row["source_company"],
            source_job_id=row["source_job_id"],
            fetched_at=row["fetched_at"],
            payload_json=row["payload_json"],
        )

    return RawPayloadRow(
        raw_payload_id=row[0],
        source_name=row[1],
        source_company=row[2],
        source_job_id=row[3],
        fetched_at=row[4],
        payload_json=row[5],
    )


if __name__ == "__main__":
    main()
