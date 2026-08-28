from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SongSegment:
    song_id: int
    segment_index: int
    start_time: float
    end_time: float
    duration: Optional[float] = None
    label: Optional[str] = None
    relative_energy: Optional[float] = None
    loudness_lufs: Optional[float] = None
    embedding: Optional[List[float]] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.duration is None:
            object.__setattr__(self, "duration", max(0.0, round(self.end_time - self.start_time, 3)))

    def to_record(self) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "song_id": self.song_id,
            "segment_index": self.segment_index,
            "start_time": round(float(self.start_time), 3),
            "end_time": round(float(self.end_time), 3),
            "label": self.label,
            "relative_energy": round(float(self.relative_energy), 4) if self.relative_energy is not None else None,
            "loudness_lufs": round(float(self.loudness_lufs), 2) if self.loudness_lufs is not None else None,
        }
        if self.embedding is not None:
            record["embedding"] = [float(x) for x in self.embedding]
        if self.id is not None:
            record["id"] = self.id
        return record

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SongSegment:
        embedding = data.get("embedding")
        if isinstance(embedding, str):
            cleaned = embedding.strip("[]")
            embedding = [float(x.strip()) for x in cleaned.split(",") if x.strip()] if cleaned else None
        elif isinstance(embedding, list):
            embedding = [float(x) for x in embedding]

        # Support both 'relative_energy' and legacy 'energy'
        rel_energy = data.get("relative_energy")
        if rel_energy is None:
            rel_energy = data.get("energy")

        return cls(
            id=data.get("id"),
            song_id=data["song_id"],
            segment_index=data["segment_index"],
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            duration=float(data["duration"]) if data.get("duration") is not None else None,
            label=data.get("label"),
            relative_energy=float(rel_energy) if rel_energy is not None else None,
            loudness_lufs=float(data["loudness_lufs"]) if data.get("loudness_lufs") is not None else None,
            embedding=embedding,
        )
