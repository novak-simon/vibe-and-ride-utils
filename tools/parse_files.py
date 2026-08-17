from __future__ import annotations

import argparse

from workout_parsing.workout_parser import WorkoutParser
from database.methods import _effective_client
from database.admin_client import get_admin_supabase

admin_client = get_admin_supabase()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse workout files."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of workouts to parse in this batch.",
    )
    parser.add_argument(
        "--stop_removal",
        type=bool,
        default=False,
        help="If set True, the parser will not remove parsed workout files from the assets folder after parsing."
    )
    args = parser.parse_args()

    client = _effective_client(client=admin_client)
    service = WorkoutParser(client)
    service.parse(limit=args.limit, stop_removal=args.stop_removal)

if __name__ == "__main__":
    main()