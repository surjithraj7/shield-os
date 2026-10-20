"""Environment-driven runtime configuration for local and hosted deployments."""

from __future__ import annotations

import os


def environment() -> str:
    return (os.environ.get("SHIELD_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()


def is_production() -> bool:
    return environment() == "production" or bool(os.environ.get("RENDER"))


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def render_external_url() -> str:
    return (os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
