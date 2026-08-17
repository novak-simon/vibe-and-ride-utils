from __future__ import annotations

import numpy as np
import librosa
from typing import List, Optional

from .model import AudioAnalysis
from helper_methods.analysis_methods import save_in_downloads_as


class LibrosaAnalyzer:
    """
    Analyze a local audio file using librosa beat tracking.

    The BPM confidence is an application-level metric based on beat-interval
    regularity; this is not a librosa-provided confidence score.
    """

    def analyze(self, audio_path: str) -> AudioAnalysis:
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        if y.size == 0:
            raise ValueError(f"Unable to decode audio from {audio_path}")

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = []
        if isinstance(tempo, float):
            bpm.append(tempo)
        else:
            for temp in tempo:
                bpm.append(round(temp))

        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        save_in_downloads_as(beat_times, "librosa_beat_times")
        beats = [float(value) for value in beat_times]
        beat_intervals = [
            float(beats[i + 1] - beats[i]) for i in range(len(beats) - 1)
        ]
        processed_intervals = self._remove_anomalies(beat_intervals)
        if processed_intervals:
            calculated_bpm = 60 / np.mean(processed_intervals)
            alternative_bpm = 60 / np.median(beat_intervals)
        elif beat_intervals:
            calculated_bpm = 60 / np.mean(beat_intervals)
            alternative_bpm = 60 / np.median(beat_intervals)
        else:
            calculated_bpm = 0
            alternative_bpm = 0
        
        bpm.append(calculated_bpm)
        bpm.append(alternative_bpm)
        final_bpm_estimate = int(round(np.nan_to_num(np.nanmean(bpm))))
        #print(f"Librosa BPM: {final_bpm_estimate}")
        #print(f"Librosa confidence: {self._confidence_for_intervals(beat_intervals)}")
        

        return AudioAnalysis(
            bpm=final_bpm_estimate,
            bpm_confidence=self._confidence_for_intervals(beat_intervals),
            beat_intervals=beat_intervals,
            beat_timestamps=beats,
        )

    @staticmethod
    def _confidence_for_intervals(intervals: List[float]) -> Optional[int]:
        if len(intervals) < 2:
            return None

        mean_interval = float(np.mean(intervals))
        if mean_interval <= 0:
            return None

        std_interval = float(np.std(intervals, ddof=0))
        coefficient_of_variation = int(std_interval / mean_interval * 1000)
        confidence = 1000 - coefficient_of_variation
        return max(0, min(1000, confidence))

    @staticmethod
    def _remove_anomalies(intervals: List[float]) -> List[float]:
        if not intervals:
            return []
        std_interval = float(np.std(intervals, ddof=0))
        mean_interval = float(np.mean(intervals))
        if mean_interval <= 0:
            return None
        processed_intervals = []
        for i in range(len(intervals)):
            value = intervals[i]
            if not value > mean_interval + 0.3 * std_interval or value < mean_interval - 0.3 * std_interval:
                processed_intervals.append(value)
        return processed_intervals
        