from __future__ import annotations
import json
from pathlib import Path
from typing import Any

SAVE_DIR = Path("saves")
SAVE_DIR.mkdir(exist_ok=True)

def save_json(filename: str, data: dict[str, Any]) -> None:
    path = SAVE_DIR / filename
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_json(filename: str) -> dict[str, Any] | None:
    path = SAVE_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))