"""Configuration loading for local ingestion commands.

This module keeps file-path decisions and YAML parsing in one place so command
modules can ask for configured companies without knowing where the project root
or config files live.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GREENHOUSE_CONFIG = PROJECT_ROOT / "config" / "greenhouse_companies.yml"


def load_greenhouse_companies(config_path: Path = DEFAULT_GREENHOUSE_CONFIG) -> list[dict[str, Any]]:
    """Load the configured Greenhouse companies from a YAML file.

    Args:
        config_path: Path to a YAML file with a top-level `companies` list.

    Returns:
        The company dictionaries from the config file. Each entry is expected to
        include at least a human-readable `name` and a Greenhouse `board_token`.
    """
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["companies"]
