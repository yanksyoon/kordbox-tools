"""Audio metadata extraction via ffprobe."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils import find_ffprobe


@dataclass(frozen=True)
class AudioMetadata:
    """Extracted audio file metadata."""
    filepath: str
    format: str                       # file extension
    codec: str                        # codec name (e.g. "pcm_s16le", "mp3")
    sample_rate: int
    bit_depth: int | None             # None for lossy formats
    bitrate: int                      # bits per second
    channels: int
    duration: float                   # seconds
    file_size: int                    # bytes


def extract_metadata(filepath: str) -> Optional[AudioMetadata]:
    """
    Run ffprobe on *filepath* and return structured metadata.

    Returns ``None`` if the file doesn't exist or ffprobe fails.
    """
    path = Path(filepath)
    if not path.is_file():
        return None

    ffprobe = str(find_ffprobe())
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError,
            FileNotFoundError, OSError):
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    # Find audio stream
    audio_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            audio_stream = stream
            break
    if audio_stream is None:
        return None

    fmt = data.get("format", {})

    sample_rate = int(audio_stream.get("sample_rate", 0))

    # Bit depth — may come from two different keys
    raw_depth = audio_stream.get("bits_per_raw_sample") or audio_stream.get("bits_per_sample")
    bit_depth: int | None = None
    if raw_depth is not None:
        try:
            bit_depth = int(raw_depth)
        except (ValueError, TypeError):
            pass

    bit_rate = int(fmt.get("bit_rate", 0))
    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))
    channels = int(audio_stream.get("channels", 0))
    codec = audio_stream.get("codec_name", "unknown")

    return AudioMetadata(
        filepath=str(path),
        format=path.suffix.lower().lstrip("."),
        codec=codec,
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        bitrate=bit_rate,
        channels=channels,
        duration=duration,
        file_size=file_size,
    )
