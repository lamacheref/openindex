from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


def get_current_version(default: str = "0.3.0") -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or default
    except OSError:
        return default
