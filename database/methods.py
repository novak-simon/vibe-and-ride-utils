from typing import Any, List
from models.song_model import Song

try:
    import supabase
except ImportError:  # Keep record helpers usable for offline tests/tools.
    supabase = None

def _effective_client(client: Any | None) -> Any:
    if client is not None:
        return client
    if supabase is None:
        raise RuntimeError("supabase-py is required when no client is supplied")
    return supabase

def _extract_data(response: Any) -> List[dict[str, Any]]:
    if isinstance(response, dict):
        data = response.get("data")
    else:
        data = getattr(response, "data", None)

    if data is None:
        return []

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
    """Flatten a normalized Supabase song response for the domain model."""
    flattened = dict(record)
    for relation in ("artists", "albums", "jamendo_song_data", "audius_song_data"):
        related = flattened.pop(relation, None)
        if isinstance(related, list):
            related = related[0] if related else None
        if isinstance(related, dict):
            flattened.update(
                {key: value for key, value in related.items() if key not in {"id", "song_id"}}
            )

    artist = record.get("artists")
    if isinstance(artist, list):
        artist = artist[0] if artist else None
    if isinstance(artist, dict):
        flattened["artist"] = artist.get("name")

    album = record.get("albums")
    if isinstance(album, list):
        album = album[0] if album else None
    if isinstance(album, dict):
        flattened["jamendo_album_name"] = album.get("name")

    # Provider tables have a shared song_id, not the fields on songs.
    flattened.setdefault("id", record.get("id"))
    return Song.from_dict(flattened)