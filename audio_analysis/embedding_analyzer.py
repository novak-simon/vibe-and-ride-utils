from __future__ import annotations

import logging
import os
import warnings
from typing import List, Optional
import numpy as np
import librosa

# Suppress TensorFlow C++ log messages before import
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Suppress known harmless upstream deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="resampy")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from models.song_segment_model import SongSegment

logger = logging.getLogger(__name__)


class OpenL3EmbeddingAnalyzer:
    """Computes OpenL3 deep audio embeddings (512-dim) for structural song segments."""

    def __init__(
        self,
        content_type: str = "music",
        input_repr: str = "mel256",
        embedding_size: int = 512,
        hop_size: float = 0.5,
        batch_size: int = 32,
    ) -> None:
        self.content_type = content_type
        self.input_repr = input_repr
        self.embedding_size = embedding_size
        self.hop_size = hop_size
        self.batch_size = batch_size

    def embed_segments(
        self,
        audio_path: str,
        segments: List[SongSegment],
    ) -> List[SongSegment]:
        """Calculates 512-dim embeddings for the audio and assigns pooled vectors to segments."""
        if not segments:
            return []

        try:
            # Suppress TF/Keras python-level logging noise
            logging.getLogger("tensorflow").setLevel(logging.ERROR)
            import openl3
        except ImportError as e:
            logger.error("openl3 library is not installed: %s", e)
            raise RuntimeError(
                "openl3 is required for embedding analysis. Please install openl3."
            ) from e

        logger.info(
            "Extracting OpenL3 embeddings (content_type=%s, embedding_size=%d, hop_size=%.1fs)...",
            self.content_type,
            self.embedding_size,
            self.hop_size,
        )

        # Load audio using librosa (mono)
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # Extract frame-level embeddings
        embeddings, timestamps = openl3.get_audio_embedding(
            audio=y,
            sr=sr,
            content_type=self.content_type,
            input_repr=self.input_repr,
            embedding_size=self.embedding_size,
            hop_size=self.hop_size,
            batch_size=self.batch_size,
            verbose=False,
        )

        # Pool embeddings per segment
        enriched_segments: List[SongSegment] = []
        for segment in segments:
            # Find frames that fall within [start_time, end_time]
            mask = (timestamps >= segment.start_time) & (timestamps <= segment.end_time)
            matching_embeddings = embeddings[mask]

            if len(matching_embeddings) > 0:
                # Mean pooling across frames in the segment
                pooled = np.mean(matching_embeddings, axis=0)
            else:
                # Fallback to the closest single frame timestamp
                mid_time = (segment.start_time + segment.end_time) / 2.0
                closest_idx = int(np.argmin(np.abs(timestamps - mid_time)))
                pooled = embeddings[closest_idx]

            # L2 normalization
            norm = np.linalg.norm(pooled)
            if norm > 1e-7:
                pooled = pooled / norm

            vector_list = [round(float(val), 6) for val in pooled]

            # Reconstruct SongSegment with embedding
            enriched_segments.append(
                SongSegment(
                    id=segment.id,
                    song_id=segment.song_id,
                    segment_index=segment.segment_index,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.duration,
                    label=segment.label,
                    relative_energy=segment.relative_energy,
                    loudness_lufs=segment.loudness_lufs,
                    embedding=vector_list,
                )
            )

        return enriched_segments
