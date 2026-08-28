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

def fetch_unanalyzed_songs(client, limit: int = 50) -> List[Song]:
    table = _get_table(client, "songs")
    try:
        query = (
            table.select(SONG_SELECT)
            .or_("bpm.is.null,start_time.is.null,start_time.eq.0,end_time.is.null,end_time.eq.0")
            .limit(limit)
        )
        rows = _execute_query(query)
    except Exception:
        fallback_limit = max(limit * 4, 100)
        rows = _execute_query(table.select(SONG_SELECT).limit(fallback_limit))
        rows = [
            row
            for row in rows
            if (
                row.get("bpm") is None
                or not row.get("start_time")
                or not row.get("end_time")
            )
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


def update_song_timing(client, song_id: int, analysis: AudioAnalysis) -> None:
    """Persist only timing fields for providers whose BPM is already known."""
    query = _get_table(client, "songs").update(
        {
            "start_time": analysis.start_time,
            "end_time": analysis.end_time,
        }
    ).eq("id", song_id)
    _execute_query(query)