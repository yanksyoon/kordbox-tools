"""Tests for src.compatibility."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.compatibility import (
    CompatibilityResult,
    check_all_models,
    check_compatibility,
    find_compatible_models,
)
from src.metadata import AudioMetadata


def _tmp_file(name: str, content: bytes = b"") -> str:
    """Create a temp file for testing."""
    import tempfile as _t
    d = _t.mkdtemp()
    p = Path(d) / name
    p.write_bytes(content)
    return str(p)


# Fake metadata for a standard WAV file
FAKE_WAV_META = AudioMetadata(
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

FAKE_FLAC_HIRES_META = AudioMetadata(
    filepath="/tmp/test_hires.flac",
    format="flac",
    codec="flac",
    sample_rate=96000,
    bit_depth=24,
    bitrate=2800000,
    channels=2,
    duration=200.0,
    file_size=70000000,
)

FAKE_MP3_META = AudioMetadata(
    filepath="/tmp/test.mp3",
    format="mp3",
    codec="mp3",
    sample_rate=44100,
    bit_depth=None,
    bitrate=320000,
    channels=2,
    duration=180.0,
    file_size=7200000,
)


class TestCheckCompatibility:
    def test_unknown_model(self):
        result = check_compatibility("/tmp/test.wav", "cdj-9999")
        assert result.compatible is False
        assert "Unknown CDJ model" in result.errors[0]

    def test_missing_file(self):
        result = check_compatibility("/nonexistent/file.wav", "cdj-3000")
        assert result.compatible is False
        assert "File not found" in result.errors[0]

    @patch("src.compatibility.extract_metadata")
    def test_wav_compatible_with_cdj3000(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META
        filepath = _tmp_file("test.wav", b"fake wav")
        result = check_compatibility(filepath, "cdj-3000", FAKE_WAV_META)
        assert result.compatible is True
        assert result.model == "CDJ-3000"

    @patch("src.compatibility.extract_metadata")
    def test_hires_flac_not_compatible_with_cdj400(self, mock_meta):
        mock_meta.return_value = FAKE_FLAC_HIRES_META
        filepath = _tmp_file("test_hires.flac", b"fake flac")
        result = check_compatibility(filepath, "cdj-400", FAKE_FLAC_HIRES_META)
        assert result.compatible is False
        # CDJ-400 doesn't support FLAC at all
        assert any("FLAC" in e or "flac" in e for e in result.errors)

    @patch("src.compatibility.extract_metadata")
    def test_mp3_bitrate_note(self, mock_meta):
        mock_meta.return_value = FAKE_MP3_META
        filepath = _tmp_file("test.mp3", b"fake mp3")
        result = check_compatibility(filepath, "cdj-3000", FAKE_MP3_META)
        assert any("320" in n for n in result.notes)

    def test_unsupported_format(self):
        filepath = _tmp_file("test.ogg", b"fake")
        result = check_compatibility(filepath, "cdj-400")
        assert result.compatible is False
        assert "OGG" in result.errors[0]


class TestCheckAllModels:
    @patch("src.compatibility.extract_metadata")
    def test_returns_all_models(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META
        filepath = _tmp_file("test.wav", b"fake wav")
        results = check_all_models(filepath, FAKE_WAV_META)
        assert len(results) == 9  # 9 CDJ models

    @patch("src.compatibility.extract_metadata")
    def test_cdj3000_compatible_wav(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META
        filepath = _tmp_file("test.wav", b"fake wav")
        results = check_all_models(filepath, FAKE_WAV_META)
        assert results["CDJ-3000"].compatible is True


class TestFindCompatibleModels:
    @patch("src.compatibility.extract_metadata")
    def test_wav_supported_by_most(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META
        filepath = _tmp_file("test.wav", b"fake wav")
        models = find_compatible_models(filepath, FAKE_WAV_META)
        assert "CDJ-3000" in models
        assert "CDJ-2000NXS2" in models


class TestCompatibilityResult:
    def test_frozen_dataclass(self):
        result = CompatibilityResult(
            filepath="/tmp/test.wav",
            model="CDJ-3000",
            model_key="cdj-3000",
            compatible=True,
        )
        with pytest.raises((TypeError, AttributeError)):
            result.compatible = False
