from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from helper_methods.model_methods import _optional_str, _optional_int_or_none, _optional_int, _optional_float_list, _str_to_list, current_timestampz

@dataclass(frozen=True)
class User:
    id: int = 0
    name: str = "User"
    genre_preferences: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=_optional_int_or_none(data.get("id")),
            name=_optional_str(data.get("name")),
            genre_preferences=_str_to_list(_optional_str(data.get("genre_preferences"))),
        )

    def to_record(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "genre_preferences": self.genre_preferences,
        }

@dataclass(frozen=True)
class UserSongStats:
    id: int = 0
    song_id: int = 0
    user_id: int = 0
    is_liked: bool = False
    play_count: int = 0
    skip_count: int = 0
    first_played_at: Optional[datetime] = None
    last_played_at: Optional[datetime] = None
    last_skipped_at: Optional[datetime] = None
    total_play_time: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSongStats":
        return cls(
            id=_optional_int_or_none(data.get("id")),
            song_id=_optional_int_or_none(data.get("song_id")),
            user_id=_optional_int_or_none(data.get("user_id")),
            is_liked=bool(data.get("is_liked")),
            play_count=_optional_int(data.get("play_count")),
            skip_count=_optional_int(data.get("skip_count")),
            first_played_at=datetime.fromisoformat(_optional_str(data.get("first_played_at"))) if data.get("first_played_at") else None,
            last_played_at=datetime.fromisoformat(_optional_str(data.get("last_played_at"))) if data.get("last_played_at") else None,
            last_skipped_at=datetime.fromisoformat(_optional_str(data.get("last_skipped_at"))) if data.get("last_skipped_at") else None,
            total_play_time=_optional_int(data.get("total_play_time")),
        )

    def to_record(self) -> Dict[str, Any]:
        return {
            "song_id": self.song_id,
            "user_id": self.user_id,
            "is_liked": self.is_liked,
            "play_count": self.play_count,
            "skip_count": self.skip_count,
            "first_played_at": (self.first_played_at if self.first_played_at else current_timestampz()).isoformat(),
            "last_played_at": current_timestampz().isoformat(),
            "last_skipped_at": self.last_skipped_at.isoformat() if self.last_skipped_at else None,
            "total_play_time": self.total_play_time,
        }