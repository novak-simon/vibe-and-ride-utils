from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audius_import.audius_importer import (
    import_audius_tracks,
    write_songs_json,
)
from audius_import.audius_database import upload_songs

DEFAULT_QUERIES = [
    "workout",
    "fitness",
    "running",
    "high energy",
    "training",
    "gym",
    "cardio",
    "cycling",
    " HIIT",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import commercially usable Audius workout tracks."
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Additional Audius search query. Can be repeated.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/audius_songs.json"),
    )
    parser.add_argument(
        "--include-unlicensed",
        action="store_true",
        help="Include tracks without an explicitly commercial license.",
    )
    parser.add_argument(
        "--include-non-commercial",
        action="store_true",
        help="Include tracks with non-commercial or unknown licenses.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing Audius records instead of skipping them.",
    )
    parser.add_argument(
        "--no-create-artists",
        action="store_true",
        help="Do not create missing artist records.",
    )
    parser.add_argument(
        "--no-create-albums",
        action="store_true",
        help="Do not create missing album records.",
    )
    args = parser.parse_args()

    queries = DEFAULT_QUERIES + (args.queries or [])
    songs = import_audius_tracks(
        limit=args.limit,
        queries=queries,
        include_unlicensed=args.include_unlicensed,
        include_non_commercial=args.include_non_commercial,
    )
    write_songs_json(songs, args.output)

    inserted, skipped = upload_songs(
        songs,
        create_artists=not args.no_create_artists,
        create_albums=not args.no_create_albums,
        update_existing=args.update_existing,
    )
    print(
        f"Exported {len(songs)} songs; "
        f"inserted {inserted}, skipped {skipped}"
    )


if __name__ == "__main__":
    main()