"""Silver-layer identity, extraction, and normalization helpers.

The Silver layer turns raw source payloads into stable canonical fields that can
be stored and queried consistently. This module stays pure: it has no database,
network, or filesystem dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup


def canonical_job_id(source_name: str, source_company: str, source_job_id: str) -> str:
    """Return a deterministic ID for one canonical source job.

    Args:
        source_name: Source system name, such as `greenhouse`.
        source_company: Company name from the source registry.
        source_job_id: Job ID assigned by the source system.

    Returns:
        A hex-encoded SHA-256 digest that identifies the source job across raw
        payload versions.
    """
    identity = {
        "source_name": source_name,
        "source_company": source_company,
        "source_job_id": source_job_id,
    }
    canonical_identity = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_identity.encode("utf-8")).hexdigest()


def normalize_title(title: str | None) -> str:
    """Return a broad deterministic role family for a source job title."""
    text = _normalized_text(title)
    if not text:
        return "unknown"

    if "forward deployed engineer" in text or "forward deployed software engineer" in text:
        return "forward deployed engineer"
    if (
        "generative ai engineer" in text
        or "genai engineer" in text
        or "ai engineer" in text
        or "artificial intelligence engineer" in text
    ):
        return "ai engineer"
    if "machine learning" in text or re.search(r"\bml engineer\b", text):
        return "machine learning engineer"
    if "analytics engineer" in text:
        return "analytics engineer"
    if "data engineer" in text:
        return "data engineer"
    if "backend" in text or "back end" in text or "back-end" in text:
        return "backend engineer"
    if "frontend" in text or "front end" in text or "front-end" in text:
        return "frontend engineer"
    if "product manager" in text:
        return "product manager"
    if "software engineer" in text:
        return "software engineer"

    return "unknown"


def classify_remote_type(
    title: str | None,
    location_name: str | None,
    office_location: str | None,
    description_text: str | None,
) -> str:
    """Classify a job as remote, hybrid, onsite, or unknown from obvious signals."""
    combined_text = _normalized_text(
        " ".join(_present_values(title, location_name, office_location, description_text))
    )

    if re.search(r"\bremote\b", combined_text):
        return "remote"
    if re.search(r"\bhybrid\b", combined_text):
        return "hybrid"
    if _looks_like_physical_location(office_location) or _looks_like_physical_location(location_name):
        return "onsite"

    return "unknown"


def normalize_seniority(title: str | None) -> str:
    """Return a conservative seniority category from obvious title signals."""
    text = _normalized_text(title)
    if not text:
        return "unknown"

    if re.search(r"\bintern(ship)?\b", text):
        return "intern"
    if re.search(r"\b(junior|jr)\b", text):
        return "junior"
    if re.search(r"\b(mid|mid-level|intermediate)\b", text) or re.search(
        r"\b(software|backend|frontend|data|analytics|machine learning|ai) engineer ii\b",
        text,
    ):
        return "mid"
    if re.search(r"\bsenior\b|\bsr\b", text):
        return "senior"
    if re.search(r"\b(software|backend|frontend|data|analytics|machine learning|ai) engineer iii\b", text):
        return "senior"
    if re.search(r"\bstaff\b|principal", text):
        return "staff"
    if re.search(r"\bmanager\b|\bmanagement\b", text):
        return "manager"

    return "unknown"


def extract_location_name(payload: dict[str, Any]) -> str | None:
    """Extract Greenhouse `location.name` when present."""
    location = payload.get("location")
    if not isinstance(location, dict):
        return None
    return _clean_optional_string(location.get("name"))


def extract_office_location(payload: dict[str, Any]) -> str | None:
    """Extract the first usable Greenhouse `offices[].location` value."""
    offices = payload.get("offices")
    if not isinstance(offices, list):
        return None

    for office in offices:
        if not isinstance(office, dict):
            continue
        office_location = _clean_optional_string(office.get("location"))
        if office_location:
            return office_location

    return None


def extract_department_name(payload: dict[str, Any]) -> str | None:
    """Extract the first usable Greenhouse department name."""
    departments = payload.get("departments")
    if not isinstance(departments, list):
        return None

    for department in departments:
        if not isinstance(department, dict):
            continue
        department_name = _clean_optional_string(department.get("name"))
        if department_name:
            return department_name

    return None


def extract_job_url(payload: dict[str, Any]) -> str | None:
    """Extract the source job URL from a Greenhouse payload."""
    return _clean_optional_string(payload.get("absolute_url"))


def extract_description_html(payload: dict[str, Any]) -> str | None:
    """Extract Greenhouse description HTML from the payload."""
    return _clean_optional_string(payload.get("content"))


def description_text_from_html(description_html: str | None) -> str | None:
    """Convert source description HTML into readable plain text."""
    if not description_html:
        return None

    soup = BeautifulSoup(description_html, "html.parser")
    description_text = soup.get_text("\n")
    lines = [line.strip() for line in description_text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    if not non_empty_lines:
        return None

    return "\n".join(non_empty_lines)


def parse_source_timestamp(value: str | None) -> datetime | None:
    """Parse a source timestamp string into an aware UTC datetime."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalized_text(value: str | None) -> str:
    """Return lowercased text with compact whitespace for internal matching."""
    if not value:
        return ""
    return " ".join(value.casefold().split())


def _clean_optional_string(value: Any) -> str | None:
    """Return a stripped string or None for missing and non-string values."""
    if not isinstance(value, str):
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _present_values(*values: str | None) -> list[str]:
    """Return non-empty strings for internal combined text matching."""
    return [value for value in values if value]


def _looks_like_physical_location(location_name: str | None) -> bool:
    """Return whether location text looks like a concrete onsite location."""
    text = _normalized_text(location_name)
    if not text:
        return False
    return "remote" not in text and "hybrid" not in text
