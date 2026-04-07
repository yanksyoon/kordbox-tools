"""Tests for src.metadata."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.metadata import AudioMetadata, extract_metadata


FAKE_PROBE_OUTPUT = json.dumps({
    "streams": [
        {
            "codec_type": "audio",
            "codec_name": "pcm_s16le",
            "sample_rate": "44100",
            "bits_per_raw_sample": "16",
            "channels": 2,
        }
    ],
    "format": {
        "bit_rate": "1411200",
        "duration": "180.5",
        "size": "31867200",
    },
})


def _tmp_file(name: str, content: bytes = b"") -> str:
    """Create a temp file without relying on pytest tmp_path fixture."""
    d = tempfile.mkdtemp()
    p = Path(d) / name
    p.write_bytes(content)
    return str(p)


class TestExtractMetadata:
    @patch("src.metadata.find_ffprobe")
    @patch("subprocess.run")
    def test_valid_file(self, mock_run, mock_find_ffprobe):
        mock_find_ffprobe.return_value = Path("/usr/bin/ffprobe")

        fake_file = _tmp_file("test.wav", b"fake audio data")

        mock_result = MagicMock()
        mock_result.stdout = FAKE_PROBE_OUTPUT
        mock_run.return_value = mock_result

        meta = extract_metadata(fake_file)

        assert meta is not None
        assert meta.format == "wav"
        assert meta.codec == "pcm_s16le"
        assert meta.sample_rate == 44100
        assert meta.bit_depth == 16
        assert meta.channels == 2
        assert meta.duration == 180.5
        assert meta.file_size == 31867200

    @patch("src.metadata.find_ffprobe")
    @patch("subprocess.run")
    def test_missing_file_returns_none(self, mock_run, mock_find_ffprobe):
        mock_find_ffprobe.return_value = Path("/usr/bin/ffprobe")
        meta = extract_metadata("/nonexistent/path/file.wav")
        assert meta is None

    @patch("src.metadata.find_ffprobe")
    @patch("subprocess.run")
    def test_ffprobe_failure_returns_none(self, mock_run, mock_find_ffprobe):
        mock_find_ffprobe.return_value = Path("/usr/bin/ffprobe")

        fake_file = _tmp_file("test.wav", b"fake audio data")

        mock_run.side_effect = FileNotFoundError()

        meta = extract_metadata(fake_file)
        assert meta is None

    @patch("src.metadata.find_ffprobe")
    @patch("subprocess.run")
    def test_no_audio_stream_returns_none(self, mock_run, mock_find_ffprobe):
        mock_find_ffprobe.return_value = Path("/usr/bin/ffprobe")

        fake_file = _tmp_file("test.txt", b"not audio")

        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"streams": [], "format": {}})
        mock_run.return_value = mock_result

        meta = extract_metadata(fake_file)
        assert meta is None

    @patch("src.metadata.find_ffprobe")
    @patch("subprocess.run")
    def test_lossy_format_no_bit_depth(self, mock_run, mock_find_ffprobe):
        mock_find_ffprobe.return_value = Path("/usr/bin/ffprobe")

        fake_file = _tmp_file("test.mp3", b"fake mp3")

        probe_data = {
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "44100",
                    "channels": 2,
                }
            ],
            "format": {
                "bit_rate": "320000",
                "duration": "200.0",
                "size": "8000000",
            },
        }
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(probe_data)
        mock_run.return_value = mock_result

        meta = extract_metadata(fake_file)
        assert meta is not None
        assert meta.bit_depth is None
        assert meta.bitrate == 320000


class TestAudioMetadata:
    def test_frozen_dataclass(self):
        meta = AudioMetadata(
            filepath="/tmp/test.wav",
            format="wav",
            codec="pcm_s16le",
            sample_rate=44100,
            bit_depth=16,
            bitrate=1411200,
            channels=2,
            duration=180.0,
            file_size=31867200,
        )
        # Frozen dataclass — should raise on mutation
        with pytest.raises((TypeError, AttributeError)):
            meta.sample_rate = 48000
