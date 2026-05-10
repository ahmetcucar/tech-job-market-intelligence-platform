"""Tests for the Greenhouse Bronze ingestion command orchestration."""

from dataclasses import dataclass
from typing import Any

from job_market_intel.ingest_greenhouse import ingest_greenhouse_companies


@dataclass(frozen=True)
class FakeInsertResult:
    """Small result object matching the fields the command reports."""

    inserted: bool


class FakeConnection:
    """Connection test double that records commit calls."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        """Record one transaction commit."""
        self.commits += 1


def test_ingest_greenhouse_companies_processes_all_configured_companies() -> None:
    """Every configured company and fetched job should be passed to Bronze storage."""
    companies = [
        {"name": "Databricks", "board_token": "databricks"},
        {"name": "Cloudflare", "board_token": "cloudflare"},
    ]
    jobs_by_board = {
        "databricks": [{"id": 1, "title": "Data Engineer"}, {"id": 2, "title": "Backend Engineer"}],
        "cloudflare": [{"id": 3, "title": "Systems Engineer"}],
    }
    inserted_jobs: list[tuple[str, str]] = []

    def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
        return jobs_by_board[board_token]

    def insert_job(
        connection: object,
        *,
        source_name: str,
        source_company: str,
        source_job_id: str,
        payload: dict[str, Any],
    ) -> FakeInsertResult:
        inserted_jobs.append((source_company, source_job_id))
        return FakeInsertResult(inserted=True)

    summary = ingest_greenhouse_companies(
        connection=FakeConnection(),
        companies=companies,
        fetch_jobs=fetch_jobs,
        insert_job=insert_job,
    )

    assert inserted_jobs == [
        ("Databricks", "1"),
        ("Databricks", "2"),
        ("Cloudflare", "3"),
    ]
    assert summary.companies_processed == 2
    assert summary.jobs_fetched == 3
    assert summary.payloads_inserted == 3
    assert summary.payloads_skipped == 0


def test_ingest_greenhouse_companies_counts_skipped_payloads() -> None:
    """Duplicate payload versions should be counted separately from inserted rows."""
    companies = [{"name": "Databricks", "board_token": "databricks"}]

    def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
        return [{"id": 1, "title": "Data Engineer"}]

    def insert_job(
        connection: object,
        *,
        source_name: str,
        source_company: str,
        source_job_id: str,
        payload: dict[str, Any],
    ) -> FakeInsertResult:
        return FakeInsertResult(inserted=False)

    summary = ingest_greenhouse_companies(
        connection=FakeConnection(),
        companies=companies,
        fetch_jobs=fetch_jobs,
        insert_job=insert_job,
    )

    assert summary.jobs_fetched == 1
    assert summary.payloads_inserted == 0
    assert summary.payloads_skipped == 1


def test_ingest_greenhouse_companies_commits_after_each_company() -> None:
    """Each company batch should commit independently after its jobs are stored."""
    companies = [
        {"name": "Databricks", "board_token": "databricks"},
        {"name": "Cloudflare", "board_token": "cloudflare"},
    ]
    connection = FakeConnection()

    def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
        return [{"id": board_token, "title": "Data Engineer"}]

    def insert_job(
        connection: object,
        *,
        source_name: str,
        source_company: str,
        source_job_id: str,
        payload: dict[str, Any],
    ) -> FakeInsertResult:
        return FakeInsertResult(inserted=True)

    ingest_greenhouse_companies(
        connection=connection,
        companies=companies,
        fetch_jobs=fetch_jobs,
        insert_job=insert_job,
    )

    assert connection.commits == 2
