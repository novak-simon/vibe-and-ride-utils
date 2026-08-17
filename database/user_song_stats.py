from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from analysis.model import AudioAnalysis
from user.model import UserSongStats
from user.service import get_current_user
from database.methods import _effective_client, _extract_data, _get_table, _execute_query, _song_from_record, _song_stat_from_record

def get_stat_by_id(id: int, client: Any | None = None) -> Optional[UserSongStats]:
    client = _effective_client(client)
    response = (
        client.table("user_song_stats")
        .select("*")
        .eq("id", id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _song_stat_from_record(records[0]) if records else None

def get_stat_by_user_and_song_id(user_id: int, song_id: int, client: Any | None = None) -> Optional[UserSongStats]:
    client = _effective_client(client)
    response = (
        client.table("user_song_stats")
        .select("*")
        .eq("song_id", song_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    records = _extract_data(response)
    return _song_stat_from_record(records[0]) if records else None

def get_stats_by_user_id(user_id: int, limit: int = 50, client: Any | None = None) -> List[UserSongStats]:
    """
    Returns user_song_stats records from database that correspond to a certain user.
    Limit is 50 records by default, can be set to anything.
    If limit is set to None, all existing records will be returned.
    """
    client = _effective_client(client)
    if limit is None:
        response = (
            client.table("user_song_stats")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            )
    else:
        response = (
            client.table("user_song_stats")
            .select("*")
            .eq("user_id", user_id)
            .limit(limit)
            .execute()
        )
    records = _extract_data(response)
    return [_song_stat_from_record(record) for record in records]

def increment_stat(stat: str, song_id: int, user_id: int | None = None, client: Any | None = None, increment_by: int = 1) -> Optional[UserSongStats]:
    """
    Increments the specified statistic for the given song for the current user or provided user.
    If no stat row exists yet, creates one with the statistic set to 1.
    """
    client = _effective_client(client)
    if song_id is None:
        return None
    if user_id is None:
        user_id = get_current_user().id

    existing = get_stat_by_user_and_song_id(user_id, song_id, client=client)
    if existing is None:
        response = (
            client.table("user_song_stats")
            .insert({
                "user_id": user_id,
                "song_id": song_id,
                stat: increment_by,
            })
            .execute()
        )
        records = _extract_data(response)
        return _song_stat_from_record(records[0]) if records else None

    new_stat_value = (getattr(existing, stat, 0) or 0) + increment_by
    response = (
        client.table("user_song_stats")
        .update({stat: new_stat_value})
        .eq("user_id", user_id)
        .eq("song_id", song_id)
        .execute()
    )
    records = _extract_data(response)
    return _song_stat_from_record(records[0]) if records else None

def set_stat_datetime(
    stat: str,
    song_id: int,
    user_id: int | None,
    client: Any | None = None,
    value: datetime | None = None,
) -> Optional[UserSongStats]:
    """
    Set a datetime-valued stat on the user/song row to the given datetime
    (or now, if not provided).
    Example: set_stat_datetime("last_played_at", song_id, user_id, client)
    """
    client = _effective_client(client)
    if user_id is None:
        user_id = get_current_user().id
    if value is None:
        value = datetime.now(timezone.utc)

    row = {
        "song_id": song_id,
        "user_id": user_id,
        stat: value.isoformat(),
    }

    response = (
        client.table("user_song_stats")
        .update({stat: value.isoformat()})
        .eq("song_id", song_id)
        .eq("user_id", user_id)
        .execute()
    )
    records = _extract_data(response)
    return _song_stat_from_record(records[0]) if records else None