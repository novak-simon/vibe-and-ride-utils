from __future__ import annotations

import numpy as np
import soundfile as sf
import tempfile
import os

from models.song_segment_model import SongSegment
from audio_analysis.segment_analyzer import SegmentAnalyzer
from audio_analysis.embedding_analyzer import OpenL3EmbeddingAnalyzer


def test_song_segment_model_serialization():
    embedding = [0.1 * i for i in range(512)]
    segment = SongSegment(
        song_id=101,
        segment_index=0,
        start_time=0.0,
        end_time=32.5,
        label="intro",
        energy=0.75,
        loudness_lufs=-12.5,
        embedding=embedding,
    )

    assert segment.duration == 32.5
    record = segment.to_record()
    assert record["song_id"] == 101
    assert record["segment_index"] == 0
    assert record["start_time"] == 0.0
    assert record["end_time"] == 32.5
    assert record["label"] == "intro"
    assert record["energy"] == 0.75
    assert record["loudness_lufs"] == -12.5
    assert len(record["embedding"]) == 512

    # Deserialization from dict
    restored = SongSegment.from_dict(record)
    assert restored.song_id == 101
    assert restored.segment_index == 0
    assert restored.start_time == 0.0
    assert restored.end_time == 32.5
    assert restored.label == "intro"
    assert len(restored.embedding) == 512


def test_segment_analyzer_synthetic_audio():
    # Create 30 seconds of synthetic audio with 2 distinct frequency parts (intro vs drop)
    sr = 22050
    t1 = np.linspace(0, 15, int(15 * sr), endpoint=False)
    t2 = np.linspace(0, 15, int(15 * sr), endpoint=False)
    # Part 1: Soft 220Hz tone
    part1 = 0.2 * np.sin(2 * np.pi * 220 * t1)
    # Part 2: Loud 880Hz tone
    part2 = 0.8 * np.sin(2 * np.pi * 880 * t2)
    audio = np.concatenate([part1, part2])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sr)

    try:
        analyzer = SegmentAnalyzer(min_segment_duration=4.0)
        segments = analyzer.analyze(temp_path, song_id=1, start_time=0.0, end_time=30.0)

        assert len(segments) >= 1
        assert segments[0].start_time == 0.0
        assert segments[-1].end_time == 30.0

        for seg in segments:
            assert seg.song_id == 1
            assert seg.start_time < seg.end_time
            assert seg.energy is not None
            assert 0.0 <= seg.energy <= 1.0

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_openl3_embedding_analyzer_synthetic_audio():
    sr = 48000
    duration = 3.0
    t = np.linspace(0, duration, int(duration * sr), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sr)

    try:
        segments = [
            SongSegment(song_id=42, segment_index=0, start_time=0.0, end_time=1.5, label="intro"),
            SongSegment(song_id=42, segment_index=1, start_time=1.5, end_time=3.0, label="section_1"),
        ]

        embedder = OpenL3EmbeddingAnalyzer(embedding_size=512, hop_size=0.5)
        enriched = embedder.embed_segments(temp_path, segments)

        assert len(enriched) == 2
        for seg in enriched:
            assert seg.embedding is not None
            assert len(seg.embedding) == 512
            # Verify unit L2 norm
            norm = np.linalg.norm(seg.embedding)
            assert abs(norm - 1.0) < 1e-3

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
