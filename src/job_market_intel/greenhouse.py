from __future__ import annotations

from typing import Any

import requests


GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"


def fetch_greenhouse_jobs(board_token: str) -> list[dict[str, Any]]:
    url = GREENHOUSE_JOBS_URL.format(board_token=board_token)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["jobs"]
