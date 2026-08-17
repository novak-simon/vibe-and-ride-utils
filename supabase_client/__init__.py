from __future__ import annotations

import importlib

__all__ = ["create_client", "supabase"]


def __getattr__(name: str):
    if name in __all__:
        module = importlib.import_module(".client", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")