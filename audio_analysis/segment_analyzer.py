from __future__ import annotations

import logging
from typing import List, Optional, Tuple
import numpy as np
import librosa

from models.song_segment_model import SongSegment

logger = logging.getLogger(__name__)


class SegmentAnalyzer:
    """Analyzes the structural audio sections of a musical track using librosa."""

    def __init__(
        self,
        target_sr: int = 22050,
        min_segment_duration: float = 6.0,
    ) -> None:
        self.target_sr = target_sr
        self.min_segment_duration = min_segment_duration

    def analyze(
        self,
        audio_path: str,
        song_id: int,
        start_time: float = 0.0,
        end_time: float = 0.0,
    ) -> List[SongSegment]:
        """Detects structural boundaries and calculates per-segment relative energy and loudness."""
        y, sr = librosa.load(audio_path, sr=self.target_sr, mono=True)
        total_duration = float(librosa.get_duration(y=y, sr=sr))

        actual_start = max(0.0, float(start_time)) if start_time > 0 else 0.0

        # In Vibe & Ride schema, end_time is the lead-out offset from the end of the song
        # (e.g. end_time = 4.14s means playback stops at total_duration - 4.14 = 185.86s).
        if end_time > 0:
            if end_time < total_duration / 2.0:
                actual_end = max(actual_start + self.min_segment_duration, total_duration - float(end_time))
            else:
                actual_end = min(total_duration, float(end_time))
        else:
            actual_end = total_duration

        if actual_end <= actual_start or (actual_end - actual_start) < self.min_segment_duration:
            # Fallback to single segment if track is too short or invalid range
            return [
                SongSegment(
                    song_id=song_id,
                    segment_index=0,
                    start_time=actual_start,
                    end_time=actual_end,
                    label="full_track",
                    relative_energy=1.0,
                    loudness_lufs=-14.0,
                )
            ]

        # Extract audio slice for structural analysis
        start_sample = int(actual_start * sr)
        end_sample = int(actual_end * sr)
        y_slice = y[start_sample:end_sample]
        slice_duration = actual_end - actual_start

        # Detect raw segment boundaries
        raw_boundaries = self._detect_boundaries(y_slice, sr, slice_duration)

        # Shift boundaries relative to track start
        shifted_boundaries = [actual_start + b for b in raw_boundaries]

        # Merge boundaries that produce segments shorter than min_segment_duration
        clean_boundaries = self._merge_short_segments(shifted_boundaries, actual_start, actual_end)

        # Build segment objects with energy and loudness measurements
        segments: List[SongSegment] = []
        global_max_rms = 1e-6
        raw_segment_metrics = []

        for i in range(len(clean_boundaries) - 1):
            s_time = clean_boundaries[i]
            e_time = clean_boundaries[i + 1]

            s_idx = int(s_time * sr)
            e_idx = int(e_time * sr)
            seg_audio = y[s_idx:e_idx]

            if len(seg_audio) > 0:
                rms = float(np.sqrt(np.mean(seg_audio**2)))
            else:
                rms = 0.0

            global_max_rms = max(global_max_rms, rms)
            raw_segment_metrics.append((s_time, e_time, rms))

        num_segments = len(raw_segment_metrics)
        for idx, (s_time, e_time, rms) in enumerate(raw_segment_metrics):
            # Intra-track relative energy in [0.0, 1.0] (fraction of the song's loudest section)
            relative_energy = min(1.0, rms / global_max_rms) if global_max_rms > 0 else 0.0

            # Objective loudness in dBFS
            loudness_db = 20.0 * np.log10(rms + 1e-9)

            # Assign intuitive labels
            if idx == 0 and s_time <= 1.0:
                label = "intro"
            elif idx == num_segments - 1 and e_time >= (total_duration - 5.0):
                label = "outro"
            else:
                label = f"section_{idx}"

            segments.append(
                SongSegment(
                    song_id=song_id,
                    segment_index=idx,
                    start_time=round(s_time, 3),
                    end_time=round(e_time, 3),
                    label=label,
                    relative_energy=round(relative_energy, 4),
                    loudness_lufs=round(loudness_db, 2),
                )
            )

        return segments

    def _detect_boundaries(self, y: np.ndarray, sr: int, duration: float) -> List[float]:
        """Uses MFCC and Chroma recurrence features to detect musical section boundaries."""
        try:
            hop_length = 512

            # 1. Timbral features (MFCC)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)

            # 2. Harmonic features (Chroma CENS)
            chroma = librosa.feature.chroma_cens(y=y, sr=sr, hop_length=hop_length)

            # 3. Stack features & normalize
            features = np.vstack([mfcc, chroma])

            # Determine number of clusters/segments based on track duration (~1 segment per 25-35s)
            k_segments = max(2, min(14, int(round(duration / 30.0))))

            # Agglomerative clustering with temporal connectivity constraint
            bounds = librosa.segment.agglomerative(features, k_segments)
            bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=hop_length)

            # Ensure start (0.0) and end (duration) are included
            all_bounds = sorted(list(set([0.0] + [float(t) for t in bound_times] + [float(duration)])))
            return all_bounds
        except Exception as e:
            logger.warning("Boundary detection failed (%s), falling back to uniform chunks", e)
            num_chunks = max(1, int(round(duration / 30.0)))
            return [float(i * (duration / num_chunks)) for i in range(num_chunks + 1)]

    def _merge_short_segments(
        self, boundaries: List[float], start_time: float, end_time: float
    ) -> List[float]:
        """Merges boundaries that produce sections shorter than min_segment_duration."""
        if len(boundaries) <= 2:
            return [start_time, end_time]

        clean = [boundaries[0]]
        for b in boundaries[1:-1]:
            if (b - clean[-1]) >= self.min_segment_duration:
                clean.append(b)

        # Check the last boundary
        if (end_time - clean[-1]) < self.min_segment_duration and len(clean) > 1:
            clean[-1] = end_time
        else:
            clean.append(end_time)

        return clean
