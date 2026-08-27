from models.song_model import Song
from unittest.mock import Mock, patch

from audius_import.audius_importer import resolve_audius_stream_url


def test_audius_song_keeps_api_bpm():
    song = Song(title="Ride", audius_id="audius-track", bpm=128)

    assert song.audius_id is not None
    assert song.jamendo_id is None
    assert song.bpm == 128


@patch("audius_import.audius_importer.load_audius_api_key", return_value="key")
@patch("audius_import.audius_importer.requests.get")
def test_resolve_audius_stream_url_uses_redirected_api_url(mock_get, _mock_key):
    response = Mock(url="https://audius-content.example/stream.mp3")
    mock_get.return_value = response

    assert resolve_audius_stream_url("track-1") == response.url
    mock_get.assert_called_once()
    response.raise_for_status.assert_called_once()
    response.close.assert_called_once()
