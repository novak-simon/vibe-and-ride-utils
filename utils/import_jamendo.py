from __future__ import annotations
import argparse

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.jamendo_importer import run_importer
MAX_TRACKS = 200

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze songs from Supabase using librosa."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_TRACKS,
        help="Maximum number of songs to analyze in this batch.",
    )
    parser.add_argument(
        "--force",
        type=bool,
        default=False,
        help="If set True, analyzer will analyze songs even if they were previously analyzed and will update the values in database."
    )
    args = parser.parse_args()
    run_importer(limit=args.limit, force=args.force)

if __name__ == "__main__":
    main()