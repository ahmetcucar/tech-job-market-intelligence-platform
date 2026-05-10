"""Preview command for the Greenhouse source integration.

This command proves that the config loader and Greenhouse client can work
together. It fetches the first configured company and prints a small summary
without writing anything to Postgres.
"""

from __future__ import annotations

from job_market_intel.config import load_greenhouse_companies
from job_market_intel.greenhouse import fetch_greenhouse_jobs


def main() -> None:
    """Run a read-only Greenhouse ingestion preview for the first configured company."""
    companies = load_greenhouse_companies()
    first_company = companies[0]

    jobs = fetch_greenhouse_jobs(first_company["board_token"])

    print(f"Company: {first_company['name']}")
    print(f"Board token: {first_company['board_token']}")
    print(f"Jobs fetched: {len(jobs)}")

    if jobs:
        first_job = jobs[0]
        print(f"First job title: {first_job['title']}")
        print(f"First job ID: {first_job['id']}")


if __name__ == "__main__":
    main()
