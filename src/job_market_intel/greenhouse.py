"""Greenhouse public job board API client.

This module owns network access to Greenhouse. It returns raw job dictionaries
from the public boards API and leaves storage or normalization decisions to
other modules.
"""

from __future__ import annotations

from typing import Any

import requests


GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"


def fetch_greenhouse_jobs(board_token: str) -> list[dict[str, Any]]:
    """Fetch all public jobs for one Greenhouse board token.

    Args:
        board_token: The Greenhouse board identifier, such as `databricks` or
            `cloudflare`.

    Returns:
        The raw `jobs` list from the Greenhouse API response, with full job
        content included because the request uses `content=true`.

    Raises:
        requests.HTTPError: If Greenhouse returns an unsuccessful HTTP status.
        requests.RequestException: If the network request itself fails.
        KeyError: If the response does not contain the expected `jobs` field.
    """
    url = GREENHOUSE_JOBS_URL.format(board_token=board_token)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["jobs"]
