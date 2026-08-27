from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.audio_analysis_model import AudioAnalysis
from models.song_model import Song
from database.methods import (
    _effective_client,
    _extract_data,
    _get_table,
    _execute_query,
    _song_from_record,
)

SONG_SELECT = (
    "*, artists(*), albums(*), jamendo_song_data(*), audius_song_data(*)"
)

def _find_or_create_named(client: Any, table: str, name: Optional[str]) -> Optional[int]:
    name = (name or "").strip()
    if not name:
        return None
    rows = _execute_query(client.table(table).select("id").ilike("name", name).limit(1))
    if rows:
        return rows[0]["id"]
    rows = _execute_query(client.table(table).insert({"name": name}))
    return rows[0]["id"] if rows else None

def get_song_by_id(id: int, client: Any | None = None) -> Optional[Song]:
    client = _effective_client(client)
    response = (
        client.table("songs")
        .select(SONG_SELECT)
        .eq("id", id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _song_from_record(records[0]) if records else None

def get_jamendo_song_data_by_song_id(id: int, client: Any | None = None) -> Optional[Song]:
    client = _effective_client(client)
    response = (
        client.table("songs")
        .select(SONG_SELECT)
        .eq("id", id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _song_from_record(records[0]) if records else None


def jamendo_id_exists(jamendo_id: str, client: Any | None = None) -> bool:
    client = _effective_client(client)
    response = (
        client.table("jamendo_song_data")
        .select("song_id")
        .eq("jamendo_id", int(jamendo_id))
        .limit(1)
        .execute()
    )
    return bool(_extract_data(response))


def add_song(song: Song, client: Any | None = None, force: bool = False) -> Song:
    if not song.jamendo_id:
        raise ValueError("Song must have a jamendo_id")

    client = _effective_client(client)
    artist_id = _find_or_create_named(client, "artists", song.artist)
    album_id = _find_or_create_named(client, "albums", song.jamendo_album_name)
    data = {
        "title": song.title,
        "artist_id": artist_id,
        "album_id": album_id,
        "duration": song.duration,
        "genre": ", ".join(song.genre or []) or None,
        "release_date": song.release_date,
        "image": song.image,
        "share_url": song.shareurl,
        "tags": song.vartags or [],
        "bpm": song.bpm or None,
        "start_time": song.start_time,
        "end_time": song.end_time,
    }
    if not force:
        if jamendo_id_exists(song.jamendo_id, client=client):
                raise ValueError(f"Song with jamendo_id={song.jamendo_id} already exists")
        response = client.table("songs").insert(data).select("*").execute()
    else:
        existing = _execute_query(
            client.table("jamendo_song_data")
            .select("song_id")
            .eq("jamendo_id", int(song.jamendo_id))
            .limit(1)
        )
        if existing:
            song_id = existing[0]["song_id"]
            _execute_query(client.table("songs").update(data).eq("id", song_id))
            response = client.table("songs").select("*").eq("id", song_id).execute()
        else:
            response = client.table("songs").insert(data).select("*").execute()
    records = _extract_data(response)
    if not records:
        raise RuntimeError("Failed to insert song")

    song_id = records[0]["id"]
    provider_data = {
        "song_id": song_id,
        "jamendo_id": int(song.jamendo_id),
        "audio_url": song.audio_url,
        "download_url": song.download_url,
        "waveform": song.waveform or [],
    }
    client.table("jamendo_song_data").upsert(
        provider_data, on_conflict="song_id"
    ).execute()
    return _song_from_record({**records[0], "id": song_id, "jamendo_song_data": provider_data})

def fetch_unanalyzed_songs(client, limit: int = 50) -> List[Song]:
    table = _get_table(client, "songs")
    try:
        query = (
            table.select(SONG_SELECT)
            .or_("bpm.is.null")
            .limit(limit)
        )
        rows = _execute_query(query)
    except Exception:
        fallback_limit = max(limit * 4, 100)
        rows = _execute_query(table.select(SONG_SELECT).limit(fallback_limit))
        rows = [
            row
            for row in rows
            if row.get("bpm") is None
        ][:limit]

    return [_song_from_record(row) for row in rows]

def fetch_songs(client, limit: int = 10) -> List[Song]:
    table = _get_table(client, "songs")
    try:
        query = (
            table.select(SONG_SELECT)
            .limit(limit)
        )
        rows = _execute_query(query)
    except Exception:
        fallback_limit = max(limit * 4, 1000)
        rows = _execute_query(table.select(SONG_SELECT).limit(fallback_limit))
        rows = rows[:limit]

    return [_song_from_record(row) for row in rows]



def update_song_analysis(client, song_id: int, analysis: AudioAnalysis) -> None:
    table = _get_table(client, "songs")
    record: Dict[str, Any] = {
        "bpm": analysis.bpm,
        "start_time": analysis.start_time,
        "end_time": analysis.end_time,
    }
    query = table.update(record).eq("id", song_id)
    _execute_query(query)