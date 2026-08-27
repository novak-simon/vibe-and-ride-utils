Utilities for the Vibe and Ride project. This repository contains various scripts and tools that are used to support the development and maintenance of the Vibe and Ride application.\
\
Vibe and Ride is a project aimed at enhancing the user experience for riders by providing real-time data, analytics, and other features to improve their journey. The utilities in this repository are designed to facilitate the development process, automate tasks, and ensure the smooth operation of the application.\
\
Github Repository: https://github.com/novak-simon/vibe-and-ride

## Database layout and audio analysis

The current Supabase layout is normalized: `songs` contains shared metadata,
while `artists` and `albums` contain names. Provider-specific fields live in
`jamendo_song_data` and `audius_song_data`, linked by `song_id`. The analysis
tool reads provider URLs through those relations and writes `bpm`, `start_time`,
and `end_time` back to `songs`. Beat intervals, beat timestamps, and BPM
confidence remain in-memory because the current `songs` schema has no columns
for them.

Run analysis with `python tools/analyze_songs.py --limit 50` or
`python tools/analyze_songs.py --id 123`. Configure `SUPABASE_URL` (or
`NEXT_PUBLIC_SUPABASE_URL`) and `SUPABASE_SECRET_KEY` first. `Supabase.txt` is
the schema reference.
