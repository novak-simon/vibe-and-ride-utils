from __future__ import annotations

import numpy as np
import librosa
from typing import List, Optional, Any
from BeatNet.BeatNet import BeatNet

from .model import AudioAnalysis
from helper_methods.analysis_methods import save_in_downloads_as


class BeatnetAnalyzer:
    """
    Analyze a local audio file using BeatNet (offline mode).

    This implementation attempts to be tolerant to different BeatNet return
    formats. It loads the audio (to get sr for conversions) then calls
    BeatNet.process(...) and extracts beat times (seconds) and optional tempo.
    """

    def analyze(self, audio_path: str) -> AudioAnalysis:
        # load audio to obtain sample rate for possible conversions
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        if y.size == 0:
            raise ValueError(f"Unable to decode audio from {audio_path}")

        try:
            from BeatNet.BeatNet import BeatNet # type: ignore
        except Exception as exc:
            raise ImportError(
                "BeatNet library is required for BeatnetAnalyzer. Install it (e.g. `pip install BeatNet`) "
                "or adapt this module."
            ) from exc

        estimator = BeatNet(1, mode="offline", inference_model="DBN", plot=[], thread=False)
        output = estimator.process(audio_path)
        save_in_downloads_as(output, "beatnet_output")

        beats = [(float(t), int(p)) for t, p in output]

        
        bpm_candidates: List[float] = []
        
        beat_times = [float(b[0]) for b in sorted(beats, key=lambda x: x[0])]
        if len(beat_times) == 0 and not bpm_candidates:
            raise RuntimeError("BeatNet produced no beats for the given audio")        
        
        beat_intervals = [
            float(beat_times[i + 1] - beat_times[i])
            for i in range(len(beat_times) - 1)
        ]
        
        filtered_intervals = []
        for interval in beat_intervals:
            if not interval == 0:
                filtered_intervals.append(interval)

        processed_intervals = self._remove_anomalies(filtered_intervals)
        if processed_intervals:
            calculated_bpm = 60.0 / float(np.mean(processed_intervals))
            bpm_candidates.append(calculated_bpm)
        if filtered_intervals:
            alternative_bpm = 60.0 / float(np.median(filtered_intervals))
            bpm_candidates.append(alternative_bpm)

        final_bpm_estimate = round(float(np.mean(bpm_candidates))) if bpm_candidates else None
        # print(f"Beatnet BPM: {final_bpm_estimate}")
        # print(f"Beatnet confidence: {self._confidence_for_intervals(filtered_intervals)}")

        return AudioAnalysis(
            bpm=final_bpm_estimate,
            bpm_confidence=self._confidence_for_intervals(filtered_intervals),
            beat_intervals=filtered_intervals,
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
            return []
        processed_intervals: List[float] = []
        for value in intervals:
            # keep value if within +/- 0.3 * std of mean
            if (mean_interval - 0.3 * std_interval) <= value <= (mean_interval + 0.3 * std_interval):
                processed_intervals.append(float(value))
        return processed_intervals