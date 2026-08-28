from __future__ import annotations

import logging
import os
import shutil
import tempfile
import urllib.request
from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator, Optional, List
import math

from database.songs import (
    fetch_unanalyzed_songs,
    fetch_unsegmented_songs,
    update_song_analysis,
    update_song_timing,
    save_song_segments,
    get_song_by_id,
    fetch_songs,
)
from .librosa_analyzer import LibrosaAnalyzer
from .beatnet_analyzer import BeatnetAnalyzer
from .start_time_analyzer import StartEndTimeAnalyzer
from .segment_analyzer import SegmentAnalyzer
from .embedding_analyzer import OpenL3EmbeddingAnalyzer
from models.song_model import Song
from models.audio_analysis_model import AudioAnalysis
from models.song_segment_model import SongSegment
from audius_import.audius_importer import resolve_audius_stream_url

logger = logging.getLogger(__name__)


class AudioAnalysisService:
    def __init__(self, db_client) -> None:
        self.db_client = db_client
        self.librosa_analyzer = LibrosaAnalyzer()
        self.beatnet_analyzer = BeatnetAnalyzer()
        self.start_end_time_analyzer = StartEndTimeAnalyzer()
        self.segment_analyzer = SegmentAnalyzer()
        self.embedding_analyzer = OpenL3EmbeddingAnalyzer()

    def analyze(
        self,
        limit: int = 50,
        force: bool = False,
        song_id: Optional[int] = None,
        with_embeddings: bool = False,
        only_embeddings: bool = False,
    ) -> None:
        if song_id is not None and song_id > 0:
            self.analyze_by_id(
                song_id,
                with_embeddings=with_embeddings,
                only_embeddings=only_embeddings,
            )
        else:
            self.analyze_batch(
                limit=limit,
                force=force,
                with_embeddings=with_embeddings,
                only_embeddings=only_embeddings,
            )

    def analyze_batch(
        self,
        limit: int = 50,
        force: bool = False,
        with_embeddings: bool = False,
        only_embeddings: bool = False,
    ) -> None:
        if only_embeddings:
            songs = fetch_unsegmented_songs(self.db_client, limit=limit)
        elif force:
            songs = fetch_songs(self.db_client, limit=limit)
        else:
            songs = fetch_unanalyzed_songs(self.db_client, limit=limit)

        if not songs:
            print("No songs found for analysis.")
            return

        for index, song in enumerate(songs, start=1):
            print(f"Analyzing {index}/{len(songs)}: {song.title or 'song with ID ' + str(song.id)}")
            self.analyze_song(
                song,
                with_embeddings=with_embeddings,
                only_embeddings=only_embeddings,
            )

    def analyze_by_id(
        self,
        id: int,
        with_embeddings: bool = False,
        only_embeddings: bool = False,
    ) -> None:
        song = get_song_by_id(id, self.db_client)
        if song is None:
            raise LookupError(f"Song with id={id} was not found")
        print(f"Analyzing {song.title or 'song with ID ' + str(song.id)}")
        self.analyze_song(
            song,
            with_embeddings=with_embeddings,
            only_embeddings=only_embeddings,
        )

    def analyze_song(
        self,
        song: Song,
        with_embeddings: bool = False,
        only_embeddings: bool = False,
    ) -> None:
        try:
            if song.audius_id:
                song = replace(
                    song,
                    download_url=resolve_audius_stream_url(song.audius_id),
                )
            with self._prepare_local_audio(song) as audio_path:
                start_time = song.start_time or 0.0
                end_time = song.end_time or 0.0

                if not only_embeddings:
                    if song.audius_id:
                        waveform = self.librosa_analyzer.generate_waveform(audio_path)
                        song_with_waveform = replace(song, waveform=waveform)
                        timing_analysis = self.start_end_time_analyzer.analyze(
                            song_with_waveform,
                            beatnet_analysis=AudioAnalysis(
                                bpm=song.bpm,
                                bpm_confidence=None,
                                beat_intervals=[],
                                beat_timestamps=[],
                            ),
                            librosa_analysis=AudioAnalysis(
                                bpm=song.bpm,
                                bpm_confidence=None,
                                beat_intervals=[],
                                beat_timestamps=[],
                            ),
                        )
                        update_song_timing(self.db_client, song.id, timing_analysis)
                        start_time = timing_analysis.start_time
                        end_time = timing_analysis.end_time
                        print(f"  Start time: {start_time}")
                        print(f"  End time: {end_time}")
                    else:
                        librosa_analysis = self.librosa_analyzer.analyze(audio_path)
                        try:
                            beatnet_analysis = self.beatnet_analyzer.analyze(audio_path)
                        except (ImportError, OSError) as err:
                            logger.warning("BeatNet unavailable; using librosa analysis only: %s", err)
                            beatnet_analysis = AudioAnalysis(
                                bpm=0,
                                bpm_confidence=None,
                                beat_intervals=[],
                                beat_timestamps=[],
                            )
                        start_end_time_analysis = self.start_end_time_analyzer.analyze(
                            song,
                            beatnet_analysis=beatnet_analysis,
                            librosa_analysis=librosa_analysis,
                        )
                        final_analysis: AudioAnalysis = self._merge_analysis(
                            librosa_analysis, beatnet_analysis, start_end_time_analysis
                        )

                        update_song_analysis(self.db_client, song.id, final_analysis)
                        start_time = final_analysis.start_time
                        end_time = final_analysis.end_time

                        print(f"  BPM: {final_analysis.bpm}")
                        print(
                            f"  Confidence: "
                            f"{final_analysis.bpm_confidence if final_analysis.bpm_confidence is not None else 'None'}"
                        )
                        print(f"  Start time: {start_time}")
                        print(f"  End time: {end_time}")

                # Structural segmentation & OpenL3 embeddings extraction
                if with_embeddings or only_embeddings:
                    print("  Extracting structural segments & OpenL3 embeddings...")
                    segments = self.segment_analyzer.analyze(
                        audio_path=audio_path,
                        song_id=song.id,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    enriched_segments = self.embedding_analyzer.embed_segments(
                        audio_path=audio_path,
                        segments=segments,
                    )
                    save_song_segments(self.db_client, song.id, enriched_segments)
                    print(f"  Saved {len(enriched_segments)} structural segments with 512-dim vectors.")

        except Exception as err:
            logger.exception("Failed to analyze song %s (%s)", song.title, song.id)
            print(f"  FAILED: {err}")

    @contextmanager
    def _prepare_local_audio(self, song: Song) -> Iterator[str]:
        if song.id is None:
            raise ValueError("Song has no database id")

        source_url = song.download_url or song.audio_url
        if not source_url:
            raise ValueError("Song has no audio_url or download_url")

        if source_url.startswith("file://"):
            local_path = source_url[7:]
            cleanup = False
        elif os.path.exists(source_url):
            local_path = source_url
            cleanup = False
        else:
            local_path = self._download_remote_audio(source_url)
            cleanup = True

        try:
            yield local_path
        finally:
            if cleanup and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except OSError:
                    logger.warning("Unable to remove temporary audio file %s", local_path)

    def _download_remote_audio(self, url: str) -> str:
        suffix = os.path.splitext(url.split("?", 1)[0])[1] or ".mp3"
        fd, local_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        request = urllib.request.Request(
            url, headers={"User-Agent": "zwift-music/librosa-analyzer"}
        )
        with urllib.request.urlopen(request, timeout=60) as remote_stream, open(
            local_path, "wb"
        ) as local_file:
            shutil.copyfileobj(remote_stream, local_file)

        return local_path

    def _calculate_relation_estimate(self, relation: float, tolerance: float) -> float:
        if 2 - tolerance < relation and relation < 2 + tolerance:
            relation_estimate = 2
        elif 3 - tolerance < relation and relation < 3 + tolerance:
            relation_estimate = 3
        elif 4 - tolerance < relation and relation < 4 + tolerance:
            relation_estimate = 4
        elif 1 / 2 - tolerance < relation and relation < 1 / 2 + tolerance:
            relation_estimate = 0.5
        elif 1 / 3 - tolerance < relation and relation < 1 / 3 + tolerance:
            relation_estimate = 1 / 3
        elif 1 / 4 - tolerance < relation and relation < 1 / 4 + tolerance:
            relation_estimate = 1 / 4
        else:
            relation_estimate = 1
        return relation_estimate

    def _normalize_by_relation_estimate(
        self,
        relation_estimate: float,
        librosa_analysis: AudioAnalysis,
        beatnet_analysis: AudioAnalysis,
    ):
        beatnet_analysis_bpm = beatnet_analysis.bpm / relation_estimate
        librosa_analysis_bpm = librosa_analysis.bpm
        if relation_estimate > 1:
            k = int(relation_estimate)
            beatnet_analysis_intervals = beatnet_analysis.beat_intervals[::k]
            librosa_analysis_intervals = librosa_analysis.beat_intervals
            beatnet_analysis_timestamps = [t[0] for t in beatnet_analysis.beat_timestamps[::k]]
            librosa_analysis_timestamps = librosa_analysis.beat_timestamps
        else:
            k = int(1 / relation_estimate)
            beatnet_analysis_intervals = beatnet_analysis.beat_intervals
            librosa_analysis_intervals = librosa_analysis.beat_intervals[::k]
            beatnet_analysis_timestamps = [t[0] for t in beatnet_analysis.beat_timestamps]
            librosa_analysis_timestamps = librosa_analysis.beat_timestamps[::k]
        return (
            librosa_analysis_bpm,
            beatnet_analysis_bpm,
            librosa_analysis_intervals,
            beatnet_analysis_intervals,
            librosa_analysis_timestamps,
            beatnet_analysis_timestamps,
        )

    def _calculate_final_bpm_and_confidence(
        self,
        librosa_bpm: float,
        beatnet_bpm: float,
        librosa_confidence: float,
        beatnet_confidence: float,
    ) -> int:
        if librosa_confidence is None or beatnet_confidence is None:
            if librosa_confidence is None:
                if beatnet_confidence is None:
                    final_confidence = 0
                    final_bpm = (librosa_bpm + beatnet_bpm) / 2
                else:
                    final_confidence = beatnet_confidence
                    final_bpm = beatnet_bpm
            else:
                final_confidence = librosa_confidence
                final_bpm = librosa_bpm
        elif abs(librosa_confidence - beatnet_confidence) > 100:
            if librosa_confidence > beatnet_confidence:
                final_bpm = librosa_bpm
                final_confidence = librosa_confidence - 100
            else:
                final_bpm = beatnet_bpm
                final_confidence = beatnet_confidence - 100
        elif abs(librosa_bpm - beatnet_bpm) > 15:
            final_bpm = beatnet_bpm
            final_confidence = beatnet_confidence - 100
        else:
            final_bpm = (
                librosa_bpm * librosa_confidence + beatnet_bpm * beatnet_confidence
            ) / (librosa_confidence + beatnet_confidence)
            bpm_diff = abs(librosa_bpm - beatnet_bpm)
            matchCoefficient = -1 * math.pow(bpm_diff - 5, 3)
            final_confidence = (
                librosa_confidence
                if beatnet_confidence == 0
                else ((librosa_confidence + beatnet_confidence) / 2)
            ) + matchCoefficient
        if final_confidence > 1000:
            final_confidence = 1000
        elif final_confidence < 0:
            final_confidence = 0
        if final_bpm > 160:
            final_bpm /= 2
        elif final_bpm < 40:
            final_bpm *= 2
        return int(round(final_bpm)), int(round(final_confidence))

    def _merge_intervals(
        self, librosa_intervals: List[float], beatnet_intervals: List[float]
    ) -> List[float]:
        final_intervals = []
        for i in range(max(len(librosa_intervals), len(beatnet_intervals))):
            if i < len(librosa_intervals):
                librosa_interval = librosa_intervals[i]
            else:
                librosa_interval = None
            if i < len(beatnet_intervals):
                beatnet_interval = beatnet_intervals[i]
            else:
                beatnet_interval = None
            if beatnet_interval is None:
                final_intervals.append(librosa_interval)
                continue
            elif librosa_interval is None:
                final_intervals.append(beatnet_interval)
                continue
            final_intervals.append(librosa_interval + beatnet_interval / 2)
        return final_intervals

    def _merge_analysis(
        self,
        librosa_analysis: AudioAnalysis,
        beatnet_analysis: AudioAnalysis,
        start_end_time_analysis: AudioAnalysis,
    ) -> AudioAnalysis:
        if librosa_analysis.bpm == 0 or beatnet_analysis.bpm == 0:
            relation = 1
        else:
            relation = beatnet_analysis.bpm / librosa_analysis.bpm
        tolerance = 0.15
        relation_estimate = self._calculate_relation_estimate(relation, tolerance)
        (
            librosa_analysis_bpm,
            beatnet_analysis_bpm,
            librosa_analysis_intervals,
            beatnet_analysis_intervals,
            librosa_analysis_timestamps,
            beatnet_analysis_timestamps,
        ) = self._normalize_by_relation_estimate(
            relation_estimate, librosa_analysis, beatnet_analysis
        )
        final_bpm, final_confidence = self._calculate_final_bpm_and_confidence(
            librosa_analysis_bpm,
            beatnet_analysis_bpm,
            librosa_analysis.bpm_confidence,
            beatnet_analysis.bpm_confidence,
        )
        final_intervals = self._merge_intervals(
            librosa_analysis_intervals, beatnet_analysis_intervals
        )
        final_timestamps = self._merge_intervals(
            librosa_analysis_timestamps, beatnet_analysis_timestamps
        )
        final_analysis: AudioAnalysis = AudioAnalysis(
            bpm=final_bpm,
            bpm_confidence=final_confidence,
            beat_intervals=final_intervals,
            beat_timestamps=final_timestamps,
            start_time=start_end_time_analysis.start_time,
            end_time=start_end_time_analysis.end_time,
        )
        return final_analysis