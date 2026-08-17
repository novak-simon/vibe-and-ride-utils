from __future__ import annotations
import supabase
import os
import dotenv
from typing import Any

_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        dotenv.load_dotenv()
        _ENV_LOADED = True


def _get_env_value(name: str) -> str:
    _ensure_env_loaded()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not configured. Add it to .env or the environment."
        )
    return value


def _get_supabase_url() -> str:
    _ensure_env_loaded()
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    if not url:
        raise RuntimeError(
            "SUPABASE_URL is not configured. Add it to .env or the environment."
        )
    return url


def create_admin_supabase() -> Any:
    supabase_url = _get_supabase_url()
    secret_key = _get_env_value("SUPABASE_SECRET_KEY")
    return supabase.create_client(supabase_url, secret_key)


def get_admin_supabase() -> Any:
    return create_admin_supabase()