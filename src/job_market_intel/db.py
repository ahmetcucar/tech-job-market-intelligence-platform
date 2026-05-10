"""Shared Postgres connection helpers.

This module centralizes how the project chooses and opens a Postgres
connection. Ingestion and future app code should use this module instead of
duplicating connection-string handling.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

import psycopg


DEFAULT_DATABASE_URL = "postgresql://jobmarket:jobmarket@127.0.0.1:5433/jobmarket"


def database_url(
    explicit_url: str | None = None,
    env: Mapping[str, str] = os.environ,
) -> str:
    """Choose the Postgres connection URL for this process.

    Args:
        explicit_url: A caller-provided connection string. This is mainly useful
            for tests or commands that accept a CLI override.
        env: Environment variables to read when no explicit URL is provided.
            Production code uses `os.environ`; tests can pass a small mapping.

    Returns:
        The explicit URL, `DATABASE_URL` from the environment, or the local
        Docker Compose default, in that order.
    """
    return explicit_url or env.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def connect(explicit_url: str | None = None) -> psycopg.Connection:
    """Open a Postgres connection using the configured database URL.

    Args:
        explicit_url: Optional connection string override.

    Returns:
        An open psycopg connection. Callers should use it as a context manager
        or close it when finished.

    Raises:
        psycopg.OperationalError: If Postgres cannot be reached or rejects the
        connection.
    """
    return psycopg.connect(database_url(explicit_url))
