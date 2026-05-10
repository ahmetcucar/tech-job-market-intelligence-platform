"""Command for storing Greenhouse jobs as Bronze raw payloads.

This module wires together company configuration, Greenhouse fetching, database
connection management, and raw payload insertion. The transformation stays
minimal: each fetched Greenhouse job is stored exactly as a raw payload.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
    ) -> RawPayloadInsertResult:
        """Insert one source job payload and return insert metadata."""


@dataclass(frozen=True)
class IngestSummary:
    """Counts produced by one Greenhouse Bronze ingestion run."""

    companies_processed: int
    jobs_fetched: int
    payloads_inserted: int
    payloads_skipped: int


def ingest_greenhouse_companies(
    *,
    connection: object,
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
        jobs_fetched += len(jobs)

        for job in jobs:
            result = insert_job(
                connection,
                source_name="greenhouse",
                source_company=company_name,
                source_job_id=str(job["id"]),
                payload=job,
            )
            if result.inserted:
                payloads_inserted += 1
            else:
                payloads_skipped += 1

    return IngestSummary(
        companies_processed=len(companies),
        jobs_fetched=jobs_fetched,
        payloads_inserted=payloads_inserted,
        payloads_skipped=payloads_skipped,
    )


def main() -> None:
    """Run Greenhouse Bronze ingestion for every configured company."""
    companies = load_greenhouse_companies()

    with connect() as connection:
        summary = ingest_greenhouse_companies(connection=connection, companies=companies)
        connection.commit()

    print(f"Companies processed: {summary.companies_processed}")
    print(f"Jobs fetched: {summary.jobs_fetched}")
    print(f"Payloads inserted: {summary.payloads_inserted}")
    print(f"Payloads skipped: {summary.payloads_skipped}")


if __name__ == "__main__":
    main()
