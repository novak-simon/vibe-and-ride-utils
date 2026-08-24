from __future__ import annotations

from typing import Any, Iterable

from database.admin_client import get_admin_supabase
from models.song_model import Song

AUDIUS_URL = "https://audius.co"


def _first(response: Any) -> dict | None:
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def _find_or_create(
    client: Any,
    table: str,
    name: str | None,
    create_missing: bool,
) -> int | None:
    name = (name or "").strip()
    if not name:
        return None

    row = _first(
        client.table(table)
        .select("id")
        .ilike("name", name)
        .limit(1)
        .execute()
    )
    if row:
        return row["id"]

    if not create_missing:
        return None

    row = _first(
        client.table(table)
        .insert({"name": name})
        .execute()
    )
    return row["id"] if row else None


def upload_songs(
    songs: Iterable[Song],
    *,
    create_artists: bool = True,
    create_albums: bool = True,
    update_existing: bool = False,
) -> tuple[int, int]:
    client = get_admin_supabase()
    inserted = 0
    skipped = 0

    for song in songs:
        if not song.audius_id:
            continue

        existing = _first(
            client.table("audius_song_data")
            .select("song_id")
            .eq("audius_id", song.audius_id)
            .limit(1)
            .execute()
        )

        if existing and not update_existing:
            skipped += 1
            continue

        artist_id = _find_or_create(
            client,
            "artists",
            song.artist,
            create_artists,
        )

        genre = ", ".join(song.genre or [])
        share_url = (
            f"{AUDIUS_URL}{song.audius_permalink}"
            if song.audius_permalink
            else None
        )

        song_record = {
            "title": song.title,
            "artist_id": artist_id,
            "duration": song.duration,
            "genre": genre or None,
            "mood": song.audius_mood,
            "bpm": song.bpm,
            "release_date": song.release_date,
            "image": song.image,
            "share_url": share_url,
            "tags": song.audius_tags or [],
        }

        if existing:
            song_id = existing["song_id"]
            client.table("songs").update(song_record).eq(
                "id", song_id
            ).execute()
            inserted += 1
        else:
            created = _first(
                client.table("songs").insert(song_record).execute()
            )
            if not created:
                continue
            song_id = created["id"]

        audius_record = {
            "song_id": song_id,
            "audius_id": song.audius_id,
            "track_cid": song.audius_track_cid,
            "audius_user_id": song.audius_user_id,
            "audius_permalink": song.audius_permalink,
            "audius_license": song.audius_license,
            "audius_license_url": song.audius_license_url,
            "audius_mood": song.audius_mood,
            "audius_tags": song.audius_tags or [],
            "audius_play_count": song.audius_play_count,
            "audius_repost_count": song.audius_repost_count,
            "audius_favorite_count": song.audius_favorite_count,
            "audius_comment_count": song.audius_comment_count,
            "audius_is_downloadable": song.audius_is_downloadable,
        }

        if existing:
            client.table("audius_song_data").update(
                audius_record
            ).eq("song_id", song_id).execute()
        else:
            client.table("audius_song_data").insert(
                audius_record
            ).execute()
            inserted += 1

    return inserted, skipped