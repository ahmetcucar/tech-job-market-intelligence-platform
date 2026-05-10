from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GREENHOUSE_CONFIG = PROJECT_ROOT / "config" / "greenhouse_companies.yml"


def load_greenhouse_companies(config_path: Path = DEFAULT_GREENHOUSE_CONFIG) -> list[dict[str, Any]]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["companies"]
