from typing import Any, Optional, List
import ast

def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)

def _optional_float(value: Any, default: float = 0) -> float:
    if value is None:
        return default
    return float(value)


def _optional_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def _optional_float_list(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(item) for item in list(value)]

def _str_to_list(value: str) -> List:
    """Convert string representation of list to actual list. Handles None, empty strings, and actual lists."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        result = ast.literal_eval(value)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []

def estimate_cadence_from_power(power: float) -> Optional[float]:
    """
    Simple documented approximation mapping power -> cadence (fallback).
    Formula (first minimal implementation):
      max(75, min(115, 70 + 30 * p))
    Clamped to [75, 115] RPM.

    Rationale: 80 RPM is a reasonable mid-point for many structured workouts.
    This is only a heuristic fallback for intervals that specify power but not cadence.
    """
    if power == 0:
        power = None
    try:
        p = float(power)
    except Exception:
        return 80 #Default cadence value if there is literally no information
    cadence = round(max(75, min(115, 70 + 30 * p)))
    return cadence

def _is_bike_sport(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"bike", "bicycle", "cycling", "true", "yes", "1"}