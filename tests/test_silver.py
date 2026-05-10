"""Tests for Silver canonical identity and normalization helpers."""

from datetime import UTC, datetime

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


def greenhouse_payload() -> dict:
    """Return a realistic Greenhouse-shaped payload fragment."""
    return {
        "id": 123,
        "internal_job_id": 456,
        "requisition_id": "REQ-789",
        "company_name": "Databricks",
        "title": "Senior Backend Software Engineer",
        "language": "en",
        "location": {"name": "San Francisco, CA"},
        "offices": [
            {"name": "San Francisco", "location": "San Francisco, California, United States"}
        ],
        "departments": [{"name": "Engineering"}],
        "absolute_url": "https://boards.greenhouse.io/databricks/jobs/123",
        "first_published": "2026-05-01T12:30:00-05:00",
        "updated_at": "2026-05-02T14:45:00-05:00",
        "content": "<p>Build data systems.</p><p>This role is hybrid in San Francisco.</p>",
    }


def test_canonical_job_id_is_deterministic_without_payload_hash() -> None:
    """Canonical identity should represent the source job, not a raw payload version."""
    first = canonical_job_id("greenhouse", "Databricks", "123")
    second = canonical_job_id("greenhouse", "Databricks", "123")
    different_job = canonical_job_id("greenhouse", "Databricks", "124")

    assert first == second
    assert first != different_job


def test_normalize_title_prefers_specific_engineering_roles() -> None:
    """Specific role families should win over broad software engineer matches."""
    assert normalize_title("Senior Backend Software Engineer") == "backend engineer"
    assert normalize_title("Frontend Engineer, Growth") == "frontend engineer"
    assert normalize_title("Machine Learning Engineer") == "machine learning engineer"
    assert normalize_title("Generative AI Engineer") == "ai engineer"
    assert normalize_title("Forward Deployed Engineer") == "forward deployed engineer"
    assert normalize_title("Product Manager, Data Platform") == "product manager"
    assert normalize_title("Customer Success Lead") == "unknown"


def test_classify_remote_type_uses_obvious_text_signals() -> None:
    """Remote classification should be conservative and deterministic."""
    assert classify_remote_type("Engineer", "Remote - US", None, "") == "remote"
    assert classify_remote_type("Engineer", None, "Remote", "") == "remote"
    assert classify_remote_type("Engineer", "Remote - US", "New York, NY", "") == "remote"
    assert classify_remote_type("Engineer", "San Francisco", None, "Hybrid role in office") == "hybrid"
    assert classify_remote_type("Engineer", None, "Hybrid - London", "") == "hybrid"
    assert classify_remote_type("Engineer", "Hybrid", "New York, NY", "") == "hybrid"
    assert classify_remote_type("Engineer", "New York, NY", "New York, NY", "") == "onsite"
    assert classify_remote_type("Engineer", None, None, "") == "unknown"


def test_normalize_seniority_uses_obvious_title_signals() -> None:
    """Seniority should stay unknown unless the title has a clear signal."""
    assert normalize_seniority("Software Engineer Intern") == "intern"
    assert normalize_seniority("Junior Data Engineer") == "junior"
    assert normalize_seniority("Mid-Level Software Engineer") == "mid"
    assert normalize_seniority("Software Engineer II") == "mid"
    assert normalize_seniority("Senior Backend Engineer") == "senior"
    assert normalize_seniority("Software Engineer III") == "senior"
    assert normalize_seniority("Staff Software Engineer") == "staff"
    assert normalize_seniority("Engineering Manager") == "manager"
    assert normalize_seniority("Software Engineer") == "unknown"


def test_extract_greenhouse_payload_fields() -> None:
    """Greenhouse extraction helpers should return optional fields without mutating payloads."""
    payload = greenhouse_payload()

    assert extract_location_name(payload) == "San Francisco, CA"
    assert extract_office_location(payload) == "San Francisco, California, United States"
    assert extract_department_name(payload) == "Engineering"
    assert extract_job_url(payload) == "https://boards.greenhouse.io/databricks/jobs/123"
    assert extract_description_html(payload) == payload["content"]


def test_description_text_from_html_returns_readable_text() -> None:
    """Description cleanup should convert Greenhouse HTML into plain text."""
    assert description_text_from_html("<p>Build data systems.</p><p>Use Python &amp; SQL.</p>") == (
        "Build data systems.\nUse Python & SQL."
    )
    assert description_text_from_html(None) is None


def test_parse_source_timestamp_handles_greenhouse_iso_strings() -> None:
    """Source timestamps should parse to aware UTC datetimes."""
    parsed = parse_source_timestamp("2026-05-01T12:30:00-05:00")

    assert parsed == datetime(2026, 5, 1, 17, 30, tzinfo=UTC)
    assert parse_source_timestamp(None) is None
    assert parse_source_timestamp("") is None
    assert parse_source_timestamp("not-a-timestamp") is None
