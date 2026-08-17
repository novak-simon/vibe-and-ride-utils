from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from models.model_methods import _optional_float_list, _optional_int, _optional_int_or_none, _optional_str, _str_to_list, _str_to_dict, _optional_float


@dataclass(frozen=True)
class Song:
    title: str
    jamendo_id: Optional[str] = None
    id: Optional[int] = None
    artist: Optional[str] = None
    release_date: Optional[str] = None
    genre: List[str] = None
    instruments: List[str] = None
    vartags: List[str] = None
    duration: int = None
    speed: int = 0
    bpm: int = 0
    bpm_confidence: int = 0
    beat_intervals: Optional[List[float]] = None
    audio_url: Optional[str] = None
    download_url: Optional[str] = None
    start_time: float = 0
    algorithm_cadence: int = 0
    algorithm_power: int = 60
    waveform: List[int] = None
    image: Optional[str] = None
    shareurl: Optional[str] = None
    license_ccurl: Optional[str] = None
    content_id_free: Optional[bool] = None
    lang: Optional[str] = None
    gender: Optional[str] = None
    is_instrumental: Optional[bool] = None
    is_electric: Optional[bool] = None
    license_nd: Optional[bool] = None
    license_sa: Optional[bool] = None
    license_nc: Optional[bool] = None
    license_version: Optional[float] = None


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Song":
        return cls(
            id=_optional_int_or_none(data.get("id")),
            title=str(data["title"]),
            jamendo_id=_optional_str(data["jamendo_id"]),
            artist=_optional_str(data.get("artist")),
            genre=_str_to_list(data.get("genre")),
            instruments=_str_to_list(data.get("instruments")),
            vartags=_str_to_list(data.get("vartags")),
            release_date=_optional_str(data.get("release_date")),
            duration=_optional_int(data.get("duration")),
            speed=_optional_int(data.get("speed"), default=0),
            bpm=_optional_int(data.get("bpm"), default=0),
            bpm_confidence=_optional_int(data.get("bpm_confidence"), default=0),
            audio_url=_optional_str(data.get("audio_url")),
            download_url=_optional_str(data.get("download_url")),
            beat_intervals=_optional_float_list(data.get("beat_intervals")),
            start_time=_optional_float(data.get("start_time")),
            algorithm_cadence=_optional_int(data.get("algorithm_cadence")),
            algorithm_power=_optional_int(data.get("algorithm_power"), default=60),
            waveform=_str_to_list(data.get("waveform")),
            image=_optional_str(data.get("image")),
            shareurl=_optional_str(data.get("shareurl")),
            license_ccurl=_optional_str(data.get("license_ccurl")),
            lang=_optional_str(data.get("lang")),
            gender=_optional_str(data.get("gender")),
            is_instrumental=bool(data.get("is_instrumental")),
            is_electric=bool(data.get("is_electric")),
            content_id_free=bool(data.get("content_id_free")),
            license_nd=bool(data.get("license_nd")),
            license_sa=bool(data.get("license_sa")),
            license_nc=bool(data.get("license_nc")),
            license_version=_optional_float(data.get("license_version")),

        )

    def to_record(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "jamendo_id": self.jamendo_id,
            "artist": self.artist,
            "release_date": self.release_date,
            "genre": self.genre,
            "duration": self.duration,
            "speed": self.speed,
            "bpm": self.bpm,
            "bpm_confidence": self.bpm_confidence,
            "audio_url": self.audio_url,
            "download_url": self.download_url,
            "beat_intervals": self.beat_intervals,
            "start_time": self.start_time,
            "algorithm_cadence": self.algorithm_cadence,
            "algorithm_power": self.algorithm_power,
            "waveform": self.waveform,
            "image": self.image,
            "shareurl": self.shareurl,
            "license_ccurl": self.license_ccurl,
            "vartags": self.vartags,
            "instruments": self.instruments,
            "lang": self.lang,
            "gender": self.gender,
            "is_instrumental": self.is_instrumental,
            "is_electric": self.is_electric,
            "content_id_free": self.content_id_free,
            "license_nd": self.license_nd,
            "license_sa": self.license_sa,
            "license_nc": self.license_nc,
            "license_version": self.license_version,
        }


