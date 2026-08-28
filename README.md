Utilities for the Vibe and Ride project. This repository contains various scripts and tools that are used to support the development and maintenance of the Vibe and Ride application.\
\
Vibe and Ride is a project aimed at enhancing the user experience for riders by providing real-time data, analytics, and other features to improve their journey. The utilities in this repository are designed to facilitate the development process, automate tasks, and ensure the smooth operation of the application.\
\
Github Repository: https://github.com/novak-simon/vibe-and-ride

## Database layout and audio analysis

The current Supabase layout is normalized: `songs` contains shared metadata,
while `artists` and `albums` contain names. Provider-specific fields live in
`jamendo_song_data` and `audius_song_data`, linked by `song_id`. The analysis tool reads provider URLs through those relations and writes `bpm`,
`start_time`, and `end_time` back to `songs`. Jamendo tracks receive full BPM
analysis from librosa and BeatNet's offline DBN mode. Audius tracks keep the BPM supplied by the
API; librosa generates an in-memory waveform for start/end-time detection, and
resolves the current stream URL from the Audius API once per analysis before
downloading.

### Structural Segmentation & OpenL3 Embeddings

Tracks can also undergo structural audio segmentation (`librosa.segment`) and deep feature extraction using **OpenL3** (`512-dimensional embeddings`, `content_type="music"`). Structural segments (e.g. intro, verse, chorus/drop, outro) with their start/end timestamps, energy, loudness, and vector embeddings are persisted to the `song_segments` table in Supabase (indexed with `pgvector` HNSW cosine similarity).

### Running Analysis

Run analysis with:
- `python tools/analyze_songs.py --limit 50` (BPM & timing analysis)
- `python tools/analyze_songs.py --limit 50 --with-embeddings` (BPM, timing, structural segments, and OpenL3 embeddings)
- `python tools/analyze_songs.py --limit 50 --only-embeddings` (Extract embeddings for songs that lack them)
- `python tools/analyze_songs.py --id 123 --with-embeddings` (Analyze specific song by ID)

Configure `SUPABASE_URL` (or `NEXT_PUBLIC_SUPABASE_URL`) and `SUPABASE_SECRET_KEY` first. `Supabase.txt` is the schema reference.
