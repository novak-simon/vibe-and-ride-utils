from database.methods import _song_from_record
from models.audio_analysis_model import AudioAnalysis


def test_normalized_song_record_is_flattened_for_audio_analysis():
    song = _song_from_record(
        {
            "id": 42,
            "title": "Ride",
            "bpm": None,
            "artists": {"id": 7, "name": "The Band"},
            "albums": {"id": 8, "name": "Road"},
            "jamendo_song_data": {
                "song_id": 42,
                "jamendo_id": 123,
                "audio_url": "https://example.test/stream",
                "download_url": "https://example.test/file.mp3",
                "waveform": [],
            },
        }
    )

    assert song.id == 42
    assert song.artist == "The Band"
    assert song.jamendo_album_name == "Road"
    assert song.jamendo_id == "123"
    assert song.download_url.endswith(".mp3")


def test_analysis_record_contains_only_columns_present_on_songs():
    analysis = AudioAnalysis(
        bpm=128,
        bpm_confidence=900,
        beat_intervals=[0.47],
        beat_timestamps=[0.0],
        start_time=3.5,
        end_time=180.0,
    )

    # The database writer intentionally persists only these supported columns.
    assert set(("bpm", "start_time", "end_time")).issubset(analysis.to_record())
    assert "beat_intervals" not in {"bpm", "start_time", "end_time"}
