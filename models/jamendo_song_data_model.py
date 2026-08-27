

from realtime import dataclass


@dataclass(frozen=True)
class JamendoSongData:
    song_id: int
    jamendo_id: int
    audio_url: str
    download_url: str
    waveform: list[int] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "JamendoSongData":
        return cls(
            song_id=data["song_id"],
            jamendo_id=data["jamendo_id"],
            audio_url=data["audio_url"],
            download_url=data["download_url"],
            waveform=data.get("waveform"),
        )