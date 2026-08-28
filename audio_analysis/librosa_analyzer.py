from __future__ import annotations

import numpy as np
import subprocess
from typing import List, Optional

from models.audio_analysis_model import AudioAnalysis
from audio_analysis.analysis_methods import save_in_downloads_as


class LibrosaAnalyzer:
    """
    Analyze a local audio file using librosa beat tracking.

    The BPM confidence is an application-level metric based on beat-interval
    regularity; this is not a librosa-provided confidence score.
    """

    def analyze(self, audio_path: str) -> AudioAnalysis:
        librosa = self._load_librosa()
        try:
            if librosa is not None:
                y, sr = librosa.load(audio_path, sr=None, mono=True)
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            else:
                raise OSError("librosa is unavailable")
        except (ImportError, OSError):
            y, sr = self._load_with_ffmpeg(audio_path)
            beat_times = self._fallback_beat_times(y, sr)
        if y.size == 0:
            raise ValueError(f"Unable to decode audio from {audio_path}")

        bpm = []
        if len(beat_times) > 1:
            bpm.append(60 / float(np.mean(np.diff(beat_times))))
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

    def generate_waveform(self, audio_path: str, points: int = 1000) -> List[int]:
        """Create the amplitude envelope used by the start/end-time analyzer."""
        if points < 1:
            raise ValueError("Waveform points must be positive")

        librosa = self._load_librosa()
        try:
            if librosa is None:
                raise OSError("librosa is unavailable")
            y, _ = librosa.load(audio_path, sr=None, mono=True)
        except (ImportError, OSError):
            y, _ = self._load_with_ffmpeg(audio_path)
        if y.size == 0:
            raise ValueError(f"Unable to decode audio from {audio_path}")

        magnitudes = np.abs(y)
        boundaries = np.linspace(0, len(magnitudes), points + 1, dtype=int)
        waveform: List[int] = []
        for start, end in zip(boundaries[:-1], boundaries[1:]):
            segment = magnitudes[start:end]
            value = float(np.max(segment)) if segment.size else 0.0
            waveform.append(int(round(np.clip(value, 0.0, 1.0) * 100)))
        return waveform

    @staticmethod
    def _load_librosa():
        try:
            import librosa
        except (ImportError, OSError):
            return None
        return librosa

    @staticmethod
    def _load_with_ffmpeg(audio_path: str) -> tuple[np.ndarray, int]:
        sample_rate = 22050
        result = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", audio_path,
                "-f", "f32le", "-ac", "1", "-ar", str(sample_rate), "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            details = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"Unable to decode audio with ffmpeg: {details}")
        return np.frombuffer(result.stdout, dtype=np.float32), sample_rate

    @staticmethod
    def _fallback_beat_times(y: np.ndarray, sr: int) -> np.ndarray:
        if y.size == 0:
            return np.array([], dtype=float)
        hop = max(1, sr // 50)
        energy = np.array(
            [np.sqrt(np.mean(np.square(y[i:i + hop]))) for i in range(0, len(y), hop)]
        )
        if energy.size < 3:
            return np.array([], dtype=float)
        threshold = float(np.mean(energy) + 0.5 * np.std(energy))
        candidates = [
            i for i in range(1, len(energy) - 1)
            if energy[i] >= threshold and energy[i] >= energy[i - 1] and energy[i] > energy[i + 1]
        ]
        minimum_gap = max(1, int(0.4 * sr / hop))
        peaks = []
        for peak in candidates:
            if not peaks or peak - peaks[-1] >= minimum_gap:
                peaks.append(peak)
        return np.asarray(peaks, dtype=float) * hop / sr

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
        