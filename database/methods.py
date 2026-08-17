from typing import Any, List
import supabase
from models.song_model import Song

def _effective_client(client: Any | None) -> Any:
    return client if client is not None else supabase

def _extract_data(response: Any) -> List[dict[str, Any]]:
    if isinstance(response, dict):
        data = response.get("data")
    else:
        data = getattr(response, "data", None)

    if data is None:
        data = [{}]

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    raise RuntimeError("Unexpected Supabase data shape")

def _get_table(client, tableName: str):
    table_method = getattr(client, "table", None) or getattr(client, "from_", None)
    if table_method is None:
        raise AttributeError("Supabase client must expose table() or from_()")
    return table_method(tableName)


def _execute_query(query):
    response = query.execute()
    if isinstance(response, dict):
        error = response.get("error")
        data = response.get("data", [])
    else:
        error = getattr(response, "error", None)
        data = getattr(response, "data", [])
    if error:
        raise RuntimeError(f"Supabase error: {error}")
    return data or []

def _song_from_record(record: dict[str, Any]) -> Song:
    return Song.from_dict(record)