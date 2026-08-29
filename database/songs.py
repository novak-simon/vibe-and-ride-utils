from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.audio_analysis_model import AudioAnalysis
from models.song_model import Song
from models.song_segment_model import SongSegment
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


def fetch_unsegmented_songs(client, limit: int = 50) -> List[Song]:
    """Fetches songs that do not yet have structural segments in song_segments table."""
    client = _effective_client(client)
    # 1. Fetch song_ids already in song_segments
    segments_table = _get_table(client, "song_segments")
    existing_records = _execute_query(segments_table.select("song_id"))
    existing_ids = set(row.get("song_id") for row in existing_records if row.get("song_id") is not None)

    # 2. Fetch candidate songs
    songs_table = _get_table(client, "songs")
    query = songs_table.select(SONG_SELECT).limit(max(limit * 3, 200))
    all_songs = [_song_from_record(row) for row in _execute_query(query)]

    unsegmented = [song for song in all_songs if song.id is not None and song.id not in existing_ids]
    return unsegmented[:limit]


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


def save_song_segments(client, song_id: int, segments: List[SongSegment]) -> None:
    """Persists structural musical segments with OpenL3 embeddings to Supabase."""
    if not segments:
        return
    client = _effective_client(client)
    table = _get_table(client, "song_segments")

    # Delete existing segments for this song to allow idempotent re-analysis
    try:
        delete_query = table.delete().eq("song_id", song_id)
        _execute_query(delete_query)
    except Exception:
        pass

    # Batch insert new segments
    records = [seg.to_record() for seg in segments]
    insert_query = table.insert(records)
    _execute_query(insert_query)


def fetch_song_segments(client, song_id: int) -> List[SongSegment]:
    """Fetches all structural segments for a given song ordered by segment_index."""
    client = _effective_client(client)
    table = _get_table(client, "song_segments")
    query = table.select("*").eq("song_id", song_id).order("segment_index")
    rows = _execute_query(query)
    return [SongSegment.from_dict(row) for row in rows]


def update_segment_loudness(client, segment_id: int, loudness_lufs: float) -> None:
    """Updates only the loudness_lufs field of an existing song_segments row."""
    table = _get_table(client, "song_segments")
    query = table.update({"loudness_lufs": round(float(loudness_lufs), 2)}).eq("id", segment_id)
    _execute_query(query)


def fetch_segmented_songs(client, limit: int = 50) -> List[Song]:
    """Fetches songs that have at least one segment with a null loudness_lufs value."""
    client = _effective_client(client)
    segments_table = _get_table(client, "song_segments")
    existing_records = _execute_query(segments_table.select("song_id").is_("loudness_lufs", "null"))
    segmented_ids = list({row.get("song_id") for row in existing_records if row.get("song_id") is not None})

    if not segmented_ids:
        return []

    songs_table = _get_table(client, "songs")
    rows = _execute_query(songs_table.select(SONG_SELECT).in_("id", segmented_ids).limit(limit))
    return [_song_from_record(row) for row in rows]