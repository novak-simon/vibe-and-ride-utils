from __future__ import annotations

import os
import warnings

# Suppress TensorFlow C++ log noise early before libraries load
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
warnings.filterwarnings("ignore", category=UserWarning, module="resampy")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import argparse

from audio_analysis.service import AudioAnalysisService
from database.methods import _effective_client
from database.admin_client import get_admin_supabase

admin_client = get_admin_supabase()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze songs from Supabase using librosa, BeatNet, and OpenL3."
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
        help="Specify a song you want to analyze by ID in the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Analyze songs even if they already have a BPM value.",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Extract structural segments and 512-dim OpenL3 embeddings in addition to BPM/timing.",
    )
    parser.add_argument(
        "--only-embeddings",
        action="store_true",
        help="Only extract and save structural segments & embeddings for tracks that do not have them yet.",
    )
    args = parser.parse_args()

    client = _effective_client(client=admin_client)
    service = AudioAnalysisService(client)
    service.analyze(
        limit=args.limit,
        force=args.force,
        song_id=args.id,
        with_embeddings=args.with_embeddings,
        only_embeddings=args.only_embeddings,
    )


if __name__ == "__main__":
    main()