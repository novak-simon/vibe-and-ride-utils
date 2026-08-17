from __future__ import annotations

import os
import dotenv
from supabase import create_client

dotenv.load_dotenv()


def _get_env_value(name: str, alternate: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if alternate:
        value = os.getenv(alternate)
        if value:
            return value
    raise RuntimeError(
        f"{name} is not configured. Add it to .env or the environment."
    )


supabase_url = _get_env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
supabase_publishable_key = _get_env_value(
    "SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"
)

supabase = create_client(supabase_url, supabase_publishable_key)