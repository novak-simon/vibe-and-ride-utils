from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.audio_analysis_model import AudioAnalysis
from models.song_model import Song
from database.methods import _effective_client, _extract_data, _get_table, _execute_query, _song_from_record

def get_song_by_id(id: int, client: Any | None = None) -> Optional[Song]:
    client = _effective_client(client)
    response = (
        client.table("songs")
        .select("*")
        .eq("id", id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _song_from_record(records[0]) if records else None


def jamendo_id_exists(jamendo_id: str, client: Any | None = None) -> bool:
    client = _effective_client(client)
    response = (
        client.table("songs")
        .select("id")
        .eq("jamendo_id", jamendo_id)
        .limit(1)
        .execute()
    )
    return bool(_extract_data(response))


def add_song(song: Song, client: Any | None = None, force: bool = False) -> Song:
    if not song.jamendo_id:
        raise ValueError("Song must have a jamendo_id")

    client = _effective_client(client)
    data = song.to_record()
    if not force:
        if jamendo_id_exists(song.jamendo_id, client=client):
                raise ValueError(f"Song with jamendo_id={song.jamendo_id} already exists")
        response = (
            client.table("songs")
            .insert(data)
            .select("*")
            .execute()
        )
    else:
        response = (
            client.table("songs")
            .upsert(data, on_conflict="jamendo_id")
            .select("*")
            .execute()
        )
    records = _extract_data(response)
    if not records:
        raise RuntimeError("Failed to insert song")

    return _song_from_record(records[0])

def fetch_unanalyzed_songs(client, limit: int = 50) -> List[Song]:
    table = _get_table(client, "songs")
    try:
        query = (
            table.select("*")
            .or_("bpm.is.null,beat_intervals.is.null")
            .limit(limit)
        )
        rows = _execute_query(query)
    except Exception:
        fallback_limit = max(limit * 4, 100)
        rows = _execute_query(table.select("*").limit(fallback_limit))
        rows = [
            row
            for row in rows
            if row.get("bpm") is None
            or row.get("beat_intervals") is None
        ][:limit]

    return [Song.from_dict(row) for row in rows]

def fetch_songs(client, limit: int = 10) -> List[Song]:
    table = _get_table(client, "songs")
    try:
        query = (
            table.select("*")
            .limit(limit)
        )
        rows = _execute_query(query)
    except Exception:
        fallback_limit = max(limit * 4, 1000)
        rows = _execute_query(table.select("*").limit(fallback_limit))
        rows = rows[:limit]

    return [Song.from_dict(row) for row in rows]



def update_song_analysis(client, song_id: int, analysis: AudioAnalysis) -> None:
    table = _get_table(client, "songs")
    record: Dict[str, Any] = {
        "bpm": analysis.bpm,
        "beat_intervals": analysis.beat_intervals,
        "bpm_confidence": analysis.bpm_confidence,
        "beat_timestamps": analysis.beat_timestamps,
        "start_time": analysis.start_time,
    }
    query = table.update(record).eq("id", song_id)
    _execute_query(query)