"""Tests for shared Postgres connection configuration."""

from job_market_intel.db import DEFAULT_DATABASE_URL, database_url


def test_database_url_uses_explicit_value_first() -> None:
    """An explicit database URL should override environment and defaults."""
    explicit_url = "postgresql://explicit:explicit@localhost:5432/explicit"

    assert database_url(explicit_url, env={}) == explicit_url


def test_database_url_uses_environment_value_when_explicit_value_is_missing() -> None:
    """The DATABASE_URL environment variable should be the normal configurable path."""
    env_url = "postgresql://env:env@localhost:5432/env"

    assert database_url(None, env={"DATABASE_URL": env_url}) == env_url


def test_database_url_uses_local_default_when_no_override_exists() -> None:
    """Local development should work with the Docker Compose Postgres defaults."""
    assert database_url(None, env={}) == DEFAULT_DATABASE_URL
