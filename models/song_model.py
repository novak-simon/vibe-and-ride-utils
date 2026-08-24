from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from models.model_methods import _optional_float_list, _optional_int, _optional_int_or_none, _optional_str, _str_to_list, _str_to_dict, _optional_float


@dataclass(frozen=True)
class Song:
    title: str
    jamendo_id: Optional[str] = None
    jamendo_artist_id: Optional[int] = None
    jamendo_album_name: Optional[str] = None
    audius_id: Optional[str] = None
    audius_track_cid: Optional[str] = None
    audius_user_id: Optional[str] = None
    audius_permalink: Optional[str] = None
    audius_license: Optional[str] = None
    audius_license_url: Optional[str] = None
    audius_mood: Optional[str] = None
    audius_tags: List[str] = None
    audius_play_count: Optional[int] = None
    audius_repost_count: Optional[int] = None
    audius_favorite_count: Optional[int] = None
    audius_comment_count: Optional[int] = None
    audius_is_downloadable: Optional[bool] = None
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
    end_time: float = 0
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
            jamendo_id=_optional_str(data.get("jamendo_id")),
            jamendo_artist_id=_optional_int_or_none(
                data.get("jamendo_artist_id")
            ),
            jamendo_album_name=_optional_str(data.get("jamendo_album_name")),
            audius_id=_optional_str(data.get("audius_id")),
            audius_track_cid=_optional_str(data.get("audius_track_cid")),
            audius_user_id=_optional_str(data.get("audius_user_id")),
            audius_permalink=_optional_str(data.get("audius_permalink")),
            audius_license=_optional_str(data.get("audius_license")),
            audius_license_url=_optional_str(data.get("audius_license_url")),
            audius_mood=_optional_str(data.get("audius_mood")),
            audius_tags=_str_to_list(data.get("audius_tags")),
            audius_play_count=_optional_int(data.get("audius_play_count")),
            audius_repost_count=_optional_int(data.get("audius_repost_count")),
            audius_favorite_count=_optional_int(data.get("audius_favorite_count")),
            audius_comment_count=_optional_int(data.get("audius_comment_count")),
            audius_is_downloadable=data.get("audius_is_downloadable"),
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
            end_time=_optional_float(data.get("end_time")),
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
            "jamendo_artist_id": self.jamendo_artist_id,
            "jamendo_album_name": self.jamendo_album_name,
            "audius_id": self.audius_id,
            "audius_track_cid": self.audius_track_cid,
            "audius_user_id": self.audius_user_id,
            "audius_permalink": self.audius_permalink,
            "audius_license": self.audius_license,
            "audius_license_url": self.audius_license_url,
            "audius_mood": self.audius_mood,
            "audius_tags": self.audius_tags,
            "audius_play_count": self.audius_play_count,
            "audius_repost_count": self.audius_repost_count,
            "audius_favorite_count": self.audius_favorite_count,
            "audius_comment_count": self.audius_comment_count,
            "audius_is_downloadable": self.audius_is_downloadable,
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
            "end_time": self.end_time,
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


