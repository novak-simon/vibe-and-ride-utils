from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AudioAnalysis:
    bpm: int
    bpm_confidence: Optional[int]
    beat_intervals: List[float]
    beat_timestamps: List[float]|List[tuple[float, int]]
    start_time: float = 0

    def to_record(self) -> Dict[str, Any]:
        return {
            "bpm": self.bpm,
            "bpm_confidence": self.bpm_confidence,
            "beat_intervals": self.beat_intervals,
            "beat_timestamps": self.beat_timestamps,
            "start_time": self.start_time,
        }