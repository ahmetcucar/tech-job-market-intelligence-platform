"""Bronze-layer identity helpers for raw source payloads.

Bronze storage keeps exact source payload versions. These helpers define how
the project identifies a raw payload version without depending on databases,
network calls, or Greenhouse-specific code.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_payload_hash(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hash for a JSON-compatible payload.

    Args:
        payload: A dictionary that can be serialized to JSON.

    Returns:
        A hex-encoded SHA-256 digest of the canonical JSON representation.

    The JSON is serialized with sorted keys and compact separators so the same
    payload content hashes the same way even when dictionary key order differs.
    """
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def raw_payload_id(
    source_name: str,
    source_company: str,
    source_job_id: str,
    payload_hash: str,
) -> str:
    """Return a deterministic ID for one stored raw payload version.

    Args:
        source_name: The source system name, such as `greenhouse`.
        source_company: The company name from the source registry.
        source_job_id: The job ID assigned by the source system.
        payload_hash: The stable hash of the full raw job payload.

    Returns:
        A hex-encoded SHA-256 digest that can be used as `raw_payload_id`.
    """
    raw_identity = {
        "source_name": source_name,
        "source_company": source_company,
        "source_job_id": source_job_id,
        "payload_hash": payload_hash,
    }
    canonical_identity = json.dumps(raw_identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_identity.encode("utf-8")).hexdigest()
