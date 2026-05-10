"""Tests for Bronze-layer raw payload identity rules."""

from job_market_intel.bronze import raw_payload_id, stable_payload_hash


def test_stable_payload_hash_ignores_json_key_order() -> None:
    """Equivalent JSON objects should hash identically even when key order differs."""
    first_payload = {
        "id": 123,
        "title": "Data Engineer",
        "location": {"name": "San Francisco, CA"},
    }
    same_payload_different_order = {
        "location": {"name": "San Francisco, CA"},
        "title": "Data Engineer",
        "id": 123,
    }

    assert stable_payload_hash(first_payload) == stable_payload_hash(same_payload_different_order)


def test_stable_payload_hash_changes_when_payload_changes() -> None:
    """A meaningful source payload change should create a different payload hash."""
    original_payload = {"id": 123, "title": "Data Engineer"}
    changed_payload = {"id": 123, "title": "Senior Data Engineer"}

    assert stable_payload_hash(original_payload) != stable_payload_hash(changed_payload)


def test_raw_payload_id_is_deterministic() -> None:
    """The same source identity and payload hash should always produce the same row ID."""
    payload_hash = "abc123"

    first_id = raw_payload_id("greenhouse", "Databricks", "123", payload_hash)
    second_id = raw_payload_id("greenhouse", "Databricks", "123", payload_hash)

    assert first_id == second_id


def test_raw_payload_id_preserves_identity_field_boundaries() -> None:
    """Different identity fields should not collide when values contain delimiters."""
    first_id = raw_payload_id("greenhouse", "Data|bricks", "123", "abc")
    second_id = raw_payload_id("greenhouse", "Data", "bricks|123", "abc")

    assert first_id != second_id
