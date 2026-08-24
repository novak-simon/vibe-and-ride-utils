from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import dotenv
import requests

from models.song_model import Song

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

AUDIUS_API = "https://api.audius.co/v1"
PAGE_SIZE = 100

# Explicitly commercial-compatible licenses only.
COMMERCIAL_LICENSES = {
    "cc0",
    "cc-by",
    "cc-by-sa",
    "creative commons attribution",
    "creative commons attribution-sharealike",
    "public domain",
}


def load_audius_api_key() -> str:
    value = os.getenv("AUDIUS_API_KEY")
    if not value:
        raise RuntimeError("AUDIUS_API_KEY is not configured.")
    return value


def _license_is_commercial(value: Any) -> bool:
    # Audius null licenses use the platform's default commercially viable license.
    if value is None:
        return True

    license_name = str(value).lower().strip()
    if not license_name:
        return False

    if "nc" in license_name or "nd" in license_name:
        return False

    return any(
        allowed in license_name
        for allowed in COMMERCIAL_LICENSES
    )


def _as_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _artwork_url(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        return (
            value.get("1000x1000")
            or value.get("480x480")
            or value.get("150x150")
        )
    return str(value) if value else None


def audius_track_to_song(track: Dict[str, Any]) -> Song:
    user = track.get("user") or {}

    return Song.from_dict(
        {
            "title": track.get("title") or "Untitled",
            "audius_id": track.get("id"),
            "audius_track_cid": track.get("track_cid"),
            "audius_user_id": user.get("id"),
            "audius_permalink": track.get("permalink"),
            "artist": user.get("name") or user.get("handle"),
            "release_date": track.get("release_date"),
            "duration": track.get("duration"),
            "genre": _as_list(track.get("genre")),
            "audius_mood": track.get("mood"),
            "audius_tags": _as_list(track.get("tags")),
            "audius_license": track.get("license"),
            "audius_license_url": track.get("license_url"),
            "audius_play_count": track.get("play_count"),
            "audius_repost_count": track.get("repost_count"),
            "audius_favorite_count": track.get("favorite_count"),
            "audius_comment_count": track.get("comment_count"),
            "audius_is_downloadable": track.get("is_downloadable"),
            "image": _artwork_url(track.get("artwork")),
            "shareurl": track.get("permalink"),
            "audio_url": None,
            "download_url": None,
        }
    )


def _fetch_page(
    session: requests.Session,
    api_key: str,
    endpoint: str,
    *,
    limit: int,
    offset: int = 0,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params = {
        "api_key": api_key,
        "app_name": "vibe-and-ride-utils",
        "limit": min(limit, PAGE_SIZE),
        "offset": offset,
    }
    if query:
        params["query"] = query

    response = session.get(
        f"{AUDIUS_API}/{endpoint}",
        params=params,
        headers={"x-api-key": api_key},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", payload)

    if not isinstance(data, list):
        raise RuntimeError("Audius response did not contain a track list")

    return [item for item in data if isinstance(item, dict)]


def fetch_audius_tracks(
    api_key: str,
    limit: int,
    queries: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Fetch trending tracks and optional workout-oriented searches.

    Requests use the maximum page size and one Session to minimize overhead.
    Results are deduplicated locally before license filtering.
    """
    if limit <= 0:
        return []

    queries = [query.strip() for query in queries if query.strip()]
    tracks: Dict[str, Dict[str, Any]] = {}

    with requests.Session() as session:
        endpoints = [("tracks/trending", None)]
        endpoints.extend(("tracks/search", query) for query in queries)

        for endpoint, query in endpoints:
            offset = 0
            while len(tracks) < limit:
                page = _fetch_page(
                    session,
                    api_key,
                    endpoint,
                    limit=min(PAGE_SIZE, limit - len(tracks)),
                    offset=offset,
                    query=query,
                )
                if not page:
                    break

                for track in page:
                    track_id = str(track.get("id", "")).strip()
                    if track_id:
                        tracks.setdefault(track_id, track)

                if len(page) < PAGE_SIZE:
                    break
                offset += len(page)

    return list(tracks.values())


def import_audius_tracks(
    limit: int,
    queries: Iterable[str] = (),
    include_unlicensed: bool = False,
    include_non_commercial: bool = False,
) -> List[Song]:
    api_key = load_audius_api_key()
    raw_tracks = fetch_audius_tracks(api_key, limit, queries)

    songs: List[Song] = []
    for track in raw_tracks:
        if not include_unlicensed and not _license_is_commercial(
            track.get("license")
        ):
            continue

        try:
            songs.append(audius_track_to_song(track))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed Audius track: %s", exc)

        if len(songs) >= limit:
            break

    return songs


def write_songs_json(songs: Iterable[Song], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            [song.to_record() for song in songs],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )