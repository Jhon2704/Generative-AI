from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "phi3:mini",
    "top_k": 5,
    "temperature": 0.2,
    "max_tokens": 512,
}


def resource_path(relative_path: str) -> str:
    """
    Resolve resource path for local execution and PyInstaller bundles.

    - Local: repository root (parent of /src).
    - Frozen: temporary extraction dir in sys._MEIPASS.
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    else:
        base_dir = Path(__file__).resolve().parent.parent

    return str((base_dir / relative_path).resolve())


def get_app_data_dir(app_name: str = "LegalSearchOffline") -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / app_name
    for folder in ("documents", "chroma_db", "logs"):
        (app_dir / folder).mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    return get_app_data_dir() / "config.json"


def load_config() -> dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with config_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise ValueError("Formato invalido")
        merged = dict(DEFAULT_CONFIG)
        merged.update(loaded)
        return merged
    except Exception:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    config_path = get_config_path()
    merged = dict(DEFAULT_CONFIG)
    merged.update(config or {})
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
