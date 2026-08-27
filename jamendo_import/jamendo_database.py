from __future__ import annotations

from typing import Any, Iterable

from database.admin_client import get_admin_supabase
from models.song_model import Song


def _first(response: Any) -> dict | None:
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


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
) -> tuple[int, int, int]:
    client = get_admin_supabase()
    inserted = skipped = failed = 0

    for song in songs:
        if not song.jamendo_id:
            failed += 1
            continue

        existing = _first(
            client.table("jamendo_song_data")
            .select("song_id")
            .eq("jamendo_id", int(song.jamendo_id))
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

        album_id = _find_or_create(
            client,
            "albums",
            song.jamendo_album_name,
            create_albums,
        )

        song_data = {
            "title": song.title,
            "artist_id": artist_id,
            "album_id": album_id,
            "duration": song.duration,
            "genre": ", ".join(song.genre or []) or None,
            "mood": song.vartags[0] if song.vartags else None,
            "description": None,
            "release_date": song.release_date,
            "image": song.image,
            "share_url": song.shareurl,
            "tags": song.vartags or [],
        }

        jamendo_data = {
            "jamendo_id": int(song.jamendo_id),
            "audio_url": song.audio_url,
            "download_url": song.download_url,
            "waveform": song.waveform,
        }

        try:
            if existing:
                song_id = existing["song_id"]

                client.table("songs").update(song_data).eq(
                    "id", song_id
                ).execute()

                client.table("jamendo_song_data").update(
                    jamendo_data
                ).eq("song_id", song_id).execute()
            else:
                created = _first(
                    client.table("songs")
                    .insert(song_data)
                    .execute()
                )
                if not created:
                    failed += 1
                    continue

                song_id = created["id"]
                jamendo_data["song_id"] = song_id

                client.table("jamendo_song_data").insert(
                    jamendo_data
                ).execute()

                inserted += 1

        except Exception as e:
            print(f"Error occurred while processing song {song.jamendo_id}: {e}")
            failed += 1

    return inserted, skipped, failed