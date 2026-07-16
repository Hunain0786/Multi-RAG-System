"""FastAPI dependency helpers."""

from __future__ import annotations

from pathlib import Path

from multirag.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


def uploads_dir_dep() -> Path:
    settings = get_settings()
    staging = Path(settings.docs_staging_dir) / "_uploads"
    staging.mkdir(parents=True, exist_ok=True)
    return staging
