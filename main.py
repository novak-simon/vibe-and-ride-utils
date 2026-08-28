import argparse
import sys
from database.admin_client import get_admin_supabase
from audio_analysis.service import AudioAnalysisService

def main():
    parser = argparse.ArgumentParser(description="Vibe & Ride Utilities")
    subparsers = parser.add_subparsers(dest="command")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze songs for BPM and timing")
    analyze_parser.add_argument("--id", type=int, help="Specific song ID to analyze")
    analyze_parser.add_argument("--limit", type=int, default=10, help="Limit number of songs for batch analysis")

    args = parser.parse_args()

    if args.command == "analyze":
        client = get_admin_supabase()
        service = AudioAnalysisService(client)
        if args.id:
            service.analyze_by_id(args.id)
        else:
            service.analyze_batch(limit=args.limit)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
