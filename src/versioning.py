from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


def get_current_version(default: str = "0.3.0") -> str:
    # Priorité aux variables d'environnement pour les tests et le déploiement
    env_version = os.getenv("OPENINDEX_APP_VERSION")
    if env_version:
        return env_version
    
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or default
    except OSError:
        return default
