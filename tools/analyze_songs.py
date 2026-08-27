from __future__ import annotations

import argparse

from audio_analysis.service import AudioAnalysisService
from database.methods import _effective_client
from database.admin_client import get_admin_supabase

admin_client = get_admin_supabase()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze songs from Supabase using librosa."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of songs to analyze in this batch.",
    )
    parser.add_argument(
        "--id",
        type=int,
        default=0,
        help="Specify a song you want to analyze by ID in the database."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Analyze songs even if they already have a BPM value.",
    )
    args = parser.parse_args()

    client = _effective_client(client=admin_client)
    service = AudioAnalysisService(client)
    service.analyze(limit=args.limit, force=args.force, song_id=args.id)

if __name__ == "__main__":
    main()