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


def fetch_jamendo_tracks(client_id: str, limit: int, boost: str) -> List[Dict[str, Any]]:
    params = {
        "client_id": client_id,
        "format": "jsonpretty",
        "limit": limit,
        "include": "musicinfo",
        "groupby": "artist_id",
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

    result["jamendo_id"] = result.pop("id")
    result["title"] = result.pop("name")
    result["artist"] = result.pop("artist_name")
    license_ccurl = str(result.get("license_ccurl"))
    if "creativecommons.org" in license_ccurl:
        if "nc" in license_ccurl:
            result["license_nc"] = True
        else:
            result["license_nc"] = False
        if "sa" in license_ccurl:
            result["license_sa"] = True
        else:
            result["license_sa"] = False
        if "nd" in license_ccurl:
            result["license_nd"] = True
        else:
            result["license_nd"] = False
        if "4.0" in license_ccurl:
            result["license_version"] = 4.0
        elif "3.0" in license_ccurl:
            result["license_version"] = 3.0
        elif "2.5" in license_ccurl:
            result["license_version"] = 2.5
        elif "2.0" in license_ccurl:
            result["license_version"] = 2.0
        elif "1.0" in license_ccurl:
            result["license_version"] = 1.0
        else:
            result["license_version"] = None
    else:
        result["license_nc"] = None
        result["license_sa"] = None
        result["license_nd"] = None
        result["license_version"] = None

    musicinfo = result.get("musicinfo") or {}
    if not isinstance(musicinfo, dict):
        musicinfo = {}
    result["lang"] = musicinfo.get("lang")
    result["gender"] = musicinfo.get("gender")
    result["is_instrumental"] = True if musicinfo.get("vocalinstrumental") == "instrumental" else False
    result["is_electric"] = True if musicinfo.get("acousticelectric") == "electric" else False

    tags = musicinfo.get("tags") or {}
    if not isinstance(tags, dict):
        tags = {}
    result["genre"] = _normalize_list(tags.get("genres"))
    result["instruments"] = _normalize_list(tags.get("instruments"))
    result["vartags"] = _normalize_list(tags.get("vartags"))
    result["speed"] = jamendo_speed_to_int(musicinfo.get("speed"))

    # extract audio/download urls safely
    audio_url = result.get("audio")
    if audio_url is not None:
        result["audio_url"] = str(audio_url)
    else:
        result["audio_url"] = audio_url

    download_url = result.get("audiodownload")
    if download_url is not None:
        result["download_url"] = str(download_url)
    else:
        result["download_url"] = download_url
    result["waveform"] = _str_to_dict(result.get("waveform")).get("peaks")
    return Song.from_dict(result)


def _jamendo_id_exists(jamendo_id: str, client: Any) -> bool:
    return songs_repo.jamendo_id_exists(jamendo_id, client=client)


def import_jamendo_tracks(results: Iterable[Dict[str, Any]], force: bool = False) -> Dict[str, int]:
    stats = {"fetched": 0, "inserted": 0, "skipped": 0, "failed": 0}
    results = list(results)
    stats["fetched"] = len(results)
    admin_client = get_admin_supabase()

    for index, raw_track in enumerate(results, start=1):
        prefix = f"[{index}/{len(results)}]"
        try:
            song = jamendo_result_to_song(raw_track)
        except ValueError as exc:
            print(f"{prefix} SKIPPED malformed track: {exc}")
            stats["failed"] += 1
            continue

        display_title = song.title[:55].ljust(55)
        print(f"{prefix} {display_title}", end=" ")

        try:
            try:
                exists = _jamendo_id_exists(song.jamendo_id, client=admin_client)
            except Exception as e:
                print(f"ERROR checking existing jamendo_id {song.jamendo_id}: {e}")
                exists = False

            print(f" -> jamendo_id_exists={exists}")
            if exists and not force:
                print("SKIPPED (already exists)")
                stats["skipped"] += 1
                continue

            print(f" -> inserting song with jamendo_id={song.jamendo_id}")
            songs_repo.add_song(song, client=admin_client, force=force)
            print("INSERTED")
            stats["inserted"] += 1
        except ValueError as exc:
            print(f"SKIPPED ({exc})")
            stats["skipped"] += 1
        except Exception as exc:
            print(f"FAILED ({exc})")
            stats["failed"] += 1

    return stats

BOOST_OPTIONS = ["buzzrate", "downloads_week", "downloads_month", "downloads_total", "listens_week", "listens_month", "listens_total", "popularity_week", "popularity_month", "popularity_total"]

def run_importer(limit, force: bool = False, boost: str = "popularity_total") -> int:
    client_id = load_jamendo_client_id()
    tracks = []
    print("Fetching songs from Jamendo...")
    if boost == "all":
        for boost_option in BOOST_OPTIONS:
            tracks.extend(fetch_jamendo_tracks(client_id, limit, boost_option))
    else:
        if boost not in BOOST_OPTIONS:
            print(f"Invalid boost option '{boost}'. Defaulting to 'popularity_total'.")
            boost = "popularity_total"
        tracks = fetch_jamendo_tracks(client_id, limit, boost)
    print(f"Received {len(tracks)} tracks.\n")
    print("Importing songs...\n")

    stats = import_jamendo_tracks(tracks, force)

    print("\nImport complete.\n")
    print(f"Fetched: {stats['fetched']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")

    return stats["failed"]