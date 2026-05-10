"""Postgres writes for Bronze raw job payloads.

This module owns the `raw_job_payloads` insert path. It keeps the Bronze table
write separate from source-specific fetching so other sources can eventually
reuse the same storage behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from psycopg.types.json import Jsonb

from job_market_intel.bronze import raw_payload_id, stable_payload_hash


class ConnectionLike(Protocol):
    """Minimal connection behavior needed to insert a raw payload row."""

    def execute(self, sql: str, params: dict[str, Any]) -> Any:
        """Execute a SQL statement and return a cursor-like object."""


@dataclass(frozen=True)
class RawPayloadInsertResult:
    """Result metadata for one raw payload insert attempt."""

    raw_payload_id: str
    payload_hash: str
    inserted: bool


def insert_raw_job_payload(
    connection: ConnectionLike,
    *,
    source_name: str,
    source_company: str,
    source_job_id: str,
    payload: dict[str, Any],
    fetched_at: datetime | None = None,
) -> RawPayloadInsertResult:
    """Insert one raw job payload version if it has not already been stored.

    Args:
        connection: Open database connection with an `execute` method.
        source_name: Source system name, such as `greenhouse`.
        source_company: Company name from the source registry.
        source_job_id: Job ID assigned by the source system.
        payload: Exact raw job payload returned by the source.
        fetched_at: Timestamp for when the source payload was fetched. If not
            provided, the current UTC time is used.

    Returns:
        Insert metadata with deterministic raw ID, payload hash, and whether a
        new row was inserted. `inserted` is false when the same source job ID
        and payload hash were already present.
    """
    payload_hash = stable_payload_hash(payload)
    raw_id = raw_payload_id(source_name, source_company, source_job_id, payload_hash)
    fetched_timestamp = fetched_at or datetime.now(UTC)

    cursor = connection.execute(
        """
        INSERT INTO raw_job_payloads (
            raw_payload_id,
            source_name,
            source_company,
            source_job_id,
            fetched_at,
            payload_hash,
            payload_json
        )
        VALUES (
            %(raw_payload_id)s,
            %(source_name)s,
            %(source_company)s,
            %(source_job_id)s,
            %(fetched_at)s,
            %(payload_hash)s,
            %(payload_json)s
        )
        ON CONFLICT DO NOTHING
        """,
        {
            "raw_payload_id": raw_id,
            "source_name": source_name,
            "source_company": source_company,
            "source_job_id": source_job_id,
            "fetched_at": fetched_timestamp,
            "payload_hash": payload_hash,
            "payload_json": Jsonb(payload),
        },
    )

    return RawPayloadInsertResult(
        raw_payload_id=raw_id,
        payload_hash=payload_hash,
        inserted=cursor.rowcount == 1,
    )
