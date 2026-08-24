from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dotenv
from database.admin_client import get_admin_supabase
from database import songs as songs_repo
from models.song_model import Song
from models.model_methods import _str_to_dict
from jamendo_import.jamendo_database import upload_songs
dotenv.load_dotenv()

try:
    import requests
except ImportError as exc:
    raise RuntimeError(
        "The requests library is required to run the Jamendo importer. "
        "Install it with `py -m pip install requests`."
    ) from exc

logger = logging.getLogger(__name__)

JAMENDO_ENDPOINT = "https://api.jamendo.com/v3.0/tracks/"
SPEED_MAP = {
    "low": 1,
    "medium": 2,
    "high": 4,
    "veryhigh": 5,
}


def load_jamendo_client_id() -> str:
    client_id = os.getenv("JAMENDO_CLIENT_ID")
    if not client_id:
        raise RuntimeError(
            "JAMENDO_CLIENT_ID is not configured. Add it to .env or the environment."
        )
    return client_id


def fetch_jamendo_tracks(client_id: str, limit: int, boost: str, groupby: str = "artist_id") -> List[Dict[str, Any]]:
    if groupby not in ["artist_id", "album_id"]:
        params = {
            "client_id": client_id,
            "format": "jsonpretty",
            "limit": limit,
            "include": "musicinfo",
            "boost": boost
        }
    else:
        params = {
            "client_id": client_id,
            "format": "jsonpretty",
            "limit": limit,
            "include": "musicinfo",
            "groupby": groupby,
            "boost": boost
        }

    response = requests.get(JAMENDO_ENDPOINT, params=params, timeout=30)
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Jamendo request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Jamendo returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Jamendo response has unexpected top-level shape")

    headers = payload.get("headers", {})
    if headers.get("status") != "success":
        error_message = headers.get("error_message") or str(headers.get("status"))
        raise RuntimeError(f"Jamendo API error: {error_message}")

    results = payload.get("results")
    if results is None:
        raise RuntimeError("Jamendo response missing results field")

    if not isinstance(results, list):
        raise RuntimeError("Jamendo results field must be a list")

    return results[:limit]


def _normalize_list(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, str):
        processed = value.strip()
        return processed or None
    if isinstance(value, Iterable):
        return value
    return str(value).strip() or None


def jamendo_speed_to_int(speed_value: Any) -> int:
    if not speed_value:
        return 0
    speed_key = str(speed_value).lower().strip()
    return SPEED_MAP.get(speed_key, 0)


def jamendo_result_to_song(result: Dict[str, Any]) -> Song:
    if not isinstance(result, dict):
        raise ValueError("Jamendo track result must be a JSON object")

    result = dict(result)
    result["jamendo_id"] = result.get("id")
    result["jamendo_artist_id"] = result.get("artist_id")
    result["jamendo_album_name"] = (
        result.get("album_name")
        or (result.get("album") or {}).get("name")
    )
    result["title"] = result.get("name") or "Untitled"
    result["artist"] = result.get("artist_name")

    musicinfo = result.get("musicinfo") or {}
    if not isinstance(musicinfo, dict):
        musicinfo = {}

    tags = musicinfo.get("tags") or {}
    if not isinstance(tags, dict):
        tags = {}

    result["lang"] = musicinfo.get("lang")
    result["gender"] = musicinfo.get("gender")
    result["is_instrumental"] = (
        musicinfo.get("vocalinstrumental") == "instrumental"
    )
    result["is_electric"] = (
        musicinfo.get("acousticelectric") == "electric"
    )
    result["genre"] = _normalize_list(tags.get("genres"))
    result["instruments"] = _normalize_list(tags.get("instruments"))
    result["vartags"] = _normalize_list(tags.get("vartags"))
    result["speed"] = jamendo_speed_to_int(musicinfo.get("speed"))

    result["audio_url"] = result.get("audio")
    result["download_url"] = result.get("audiodownload")
    result["waveform"] = _str_to_dict(result.get("waveform")).get("peaks")

    return Song.from_dict(result)


def _jamendo_id_exists(jamendo_id: str, client: Any) -> bool:
    return songs_repo.jamendo_id_exists(jamendo_id, client=client)


def import_jamendo_tracks(
    results: Iterable[Dict[str, Any]],
    force: bool = False,
    create_artists: bool = True,
    create_albums: bool = True,
) -> Dict[str, int]:
    results = list(results)
    songs: List[Song] = []
    failed = 0

    for result in results:
        try:
            songs.append(jamendo_result_to_song(result))
        except (TypeError, ValueError, KeyError):
            failed += 1

    inserted, skipped, upload_failed = upload_songs(
        songs,
        create_artists=create_artists,
        create_albums=create_albums,
        update_existing=force,
    )

    return {
        "fetched": len(results),
        "inserted": inserted,
        "skipped": skipped,
        "failed": failed + upload_failed,
    }

BOOST_OPTIONS = ["buzzrate", "downloads_week", "downloads_month", "downloads_total", "listens_week", "listens_month", "listens_total", "popularity_week", "popularity_month", "popularity_total"]

def run_importer(limit, force: bool = False, boost: str = "popularity_total", groupby: str = "artist_id", create_artists: bool = True, create_albums: bool = True) -> int:
    client_id = load_jamendo_client_id()
    tracks = []
    print("Fetching songs from Jamendo...")
    if boost == "all":
        for boost_option in BOOST_OPTIONS:
            tracks.extend(fetch_jamendo_tracks(client_id, limit, boost_option, groupby))
    else:
        if boost not in BOOST_OPTIONS:
            print(f"Invalid boost option '{boost}'. Defaulting to 'popularity_total'.")
            boost = "popularity_total"
        tracks = fetch_jamendo_tracks(client_id, limit, boost, groupby)
    print(f"Received {len(tracks)} tracks.\n")
    print("Importing songs...\n")

    stats = import_jamendo_tracks(tracks, force, create_artists, create_albums)

    print("\nImport complete.\n")
    print(f"Fetched: {stats['fetched']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")

    return stats["failed"]