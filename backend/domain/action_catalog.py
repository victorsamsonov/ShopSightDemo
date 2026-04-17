from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_action_catalog() -> list[dict[str, Any]]:
    """
    Load the constrained action metadata used by the lightweight agent.
    The JSON entries must contain at least: action_type, output_type.
    """

    path = Path(__file__).with_name("action_catalog.json")
    return json.loads(path.read_text(encoding="utf-8"))

