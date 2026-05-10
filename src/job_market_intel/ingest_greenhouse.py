"""Command for storing Greenhouse jobs as Bronze raw payloads.

This module wires together company configuration, Greenhouse fetching, database
connection management, and raw payload insertion. The transformation stays
minimal: each fetched Greenhouse job is stored exactly as a raw payload.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from job_market_intel.config import load_greenhouse_companies
from job_market_intel.db import connect
from job_market_intel.greenhouse import fetch_greenhouse_jobs
from job_market_intel.raw_payloads import RawPayloadInsertResult, insert_raw_job_payload


class InsertRawJob(Protocol):
    """Callable shape for inserting one fetched job into Bronze storage."""

    def __call__(
        self,
        connection: object,
        *,
        source_name: str,
        source_company: str,
        source_job_id: str,
        payload: dict[str, Any],
        fetched_at: datetime,
    ) -> RawPayloadInsertResult:
        """Insert one source job payload and return insert metadata."""


class CommitConnection(Protocol):
    """Minimal connection behavior needed by the ingest command."""

    def commit(self) -> None:
        """Commit the current transaction."""


@dataclass(frozen=True)
class IngestSummary:
    """Counts produced by one Greenhouse Bronze ingestion run."""

    companies_processed: int
    jobs_fetched: int
    payloads_inserted: int
    payloads_skipped: int


def ingest_greenhouse_companies(
    *,
    connection: CommitConnection,
    companies: Sequence[dict[str, Any]],
    fetch_jobs: Callable[[str], list[dict[str, Any]]] = fetch_greenhouse_jobs,
    insert_job: InsertRawJob = insert_raw_job_payload,
) -> IngestSummary:
    """Fetch and store raw Greenhouse jobs for every configured company.

    Args:
        connection: Open database connection used for all raw payload inserts.
        companies: Configured Greenhouse company dictionaries with `name` and
            `board_token` values.
        fetch_jobs: Function used to fetch raw jobs for one board token.
        insert_job: Function used to store one fetched raw job payload.

    Returns:
        A summary of how many companies and jobs were processed, split into new
        raw payload rows and skipped duplicate payload versions.
    """
    jobs_fetched = 0
    payloads_inserted = 0
    payloads_skipped = 0

    for company in companies:
        company_name = company["name"]
        board_token = company["board_token"]
        jobs = fetch_jobs(board_token)
        fetched_at = datetime.now(UTC)
        jobs_fetched += len(jobs)

        for job in jobs:
            result = insert_job(
                connection,
                source_name="greenhouse",
                source_company=company_name,
                source_job_id=str(job["id"]),
                payload=job,
                fetched_at=fetched_at,
            )
            if result.inserted:
                payloads_inserted += 1
            else:
                payloads_skipped += 1

        connection.commit()

    return IngestSummary(
        companies_processed=len(companies),
        jobs_fetched=jobs_fetched,
        payloads_inserted=payloads_inserted,
        payloads_skipped=payloads_skipped,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line options for Greenhouse Bronze ingestion."""
    parser = argparse.ArgumentParser(
        description="Store raw Greenhouse job payloads for configured companies.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a Greenhouse company YAML config. Defaults to the repo config file.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres connection URL. Defaults to DATABASE_URL or the local Docker database.",
    )
    return parser.parse_args()


def main() -> None:
    """Run Greenhouse Bronze ingestion for every configured company."""
    args = parse_args()
    companies = load_greenhouse_companies(args.config) if args.config else load_greenhouse_companies()

    with connect(args.database_url) as connection:
        summary = ingest_greenhouse_companies(connection=connection, companies=companies)

    print(f"Companies processed: {summary.companies_processed}")
    print(f"Jobs fetched: {summary.jobs_fetched}")
    print(f"Payloads inserted: {summary.payloads_inserted}")
    print(f"Payloads skipped: {summary.payloads_skipped}")


if __name__ == "__main__":
    main()
