"""Tests for src.converter."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.converter import (
    ConversionReport,
    ConversionResult,
    ConversionTarget,
    build_ffmpeg_cmd,
    convert_file,
    needs_conversion,
    target_from_model,
    target_from_preset,
    target_from_reference,
    _bitrate_to_bps,
)
from src.metadata import AudioMetadata


def _tmp_file(name: str, content: bytes = b"", base: str | None = None) -> str:
    d = base or tempfile.mkdtemp()
    p = Path(d) / name
    p.write_bytes(content)
    return str(p)


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


class TestTargetResolution:
    def test_target_from_model_cdj3000(self):
        target = target_from_model("cdj-3000")
        assert target.format == "wav"
        assert target.sample_rate == 44100
        assert target.bit_depth == 16

    def test_target_from_model_unknown(self):
        with pytest.raises(ValueError, match="Unknown CDJ model"):
            target_from_model("cdj-9999")

    def test_target_from_preset_club(self):
        target = target_from_preset("club")
        assert target.format == "wav"
        assert target.sample_rate == 44100
        assert target.bit_depth == 16

    def test_target_from_preset_hires(self):
        target = target_from_preset("hires")
        assert target.format == "flac"
        assert target.sample_rate == 96000
        assert target.bit_depth == 24

    def test_target_from_preset_high_quality(self):
        target = target_from_preset("high_quality")
        assert target.format == "mp3"
        assert target.bitrate == "320k"

    def test_target_from_preset_unknown(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            target_from_preset("nonexistent")

    @patch("src.converter.extract_metadata")
    def test_target_from_reference(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META
        target = target_from_reference("/tmp/ref.wav")
        assert target.format == "wav"
        assert target.sample_rate == 44100
        assert target.bit_depth == 16

    @patch("src.converter.extract_metadata")
    def test_target_from_reference_normalizes_aif(self, mock_meta):
        meta = AudioMetadata(
            filepath="/tmp/ref.aif",
            format="aif",
            codec="pcm_s16be",
            sample_rate=44100,
            bit_depth=16,
            bitrate=1411200,
            channels=2,
            duration=10.0,
            file_size=1000000,
        )
        mock_meta.return_value = meta
        target = target_from_reference("/tmp/ref.aif")
        assert target.format == "aiff"


class TestNeedsConversion:
    def test_same_format_same_specs(self):
        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        assert needs_conversion(FAKE_WAV_META, target) is False

    def test_different_format(self):
        target = ConversionTarget(format="mp3", bitrate="320k")
        assert needs_conversion(FAKE_WAV_META, target) is True

    def test_different_sample_rate(self):
        target = ConversionTarget(format="wav", sample_rate=48000, bit_depth=16)
        assert needs_conversion(FAKE_WAV_META, target) is True

    def test_different_bit_depth(self):
        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=24)
        assert needs_conversion(FAKE_WAV_META, target) is True

    def test_mp3_same_bitrate(self):
        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        assert needs_conversion(FAKE_MP3_META, target) is False

    def test_mp3_different_bitrate(self):
        target = ConversionTarget(format="mp3", bitrate="192k", sample_rate=44100)
        assert needs_conversion(FAKE_MP3_META, target) is True


class TestBuildFfmpegCmd:
    @patch("src.converter.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_wav_16bit(self, mock_ffmpeg):
        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        cmd = build_ffmpeg_cmd("/in.wav", "/out.wav", target)
        assert cmd[0] == "/usr/bin/ffmpeg"
        assert "-codec:a" in cmd
        assert "pcm_s16le" in cmd
        assert "-y" in cmd

    @patch("src.converter.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_mp3_320k(self, mock_ffmpeg):
        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        cmd = build_ffmpeg_cmd("/in.wav", "/out.mp3", target)
        assert "libmp3lame" in cmd
        assert "320k" in cmd

    @patch("src.converter.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_flac_24bit(self, mock_ffmpeg):
        target = ConversionTarget(format="flac", sample_rate=96000, bit_depth=24)
        cmd = build_ffmpeg_cmd("/in.wav", "/out.flac", target)
        assert "flac" in cmd
        assert "s24" in cmd

    @patch("src.converter.find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_aiff(self, mock_ffmpeg):
        target = ConversionTarget(format="aiff", sample_rate=44100, bit_depth=16)
        cmd = build_ffmpeg_cmd("/in.wav", "/out.aiff", target)
        assert "pcm_s16be" in cmd


class TestConvertFile:
    @patch("src.converter.extract_metadata")
    def test_skips_already_compatible(self, mock_meta):
        mock_meta.return_value = FAKE_WAV_META

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("test.wav", b"audio", base=d)

        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        result = convert_file(fake_file, d, target)

        assert result.skipped is True
        assert result.success is True

    def test_missing_input_file(self):
        target = ConversionTarget(format="wav")
        result = convert_file("/nonexistent.wav", "/tmp", target)
        assert result.success is False
        assert "not found" in result.error

    @patch("src.converter.extract_metadata")
    @patch("src.converter.find_ffmpeg")
    @patch("subprocess.Popen")
    def test_conversion_success(self, mock_popen, mock_find_ffmpeg, mock_meta):
        mock_meta.return_value = FAKE_MP3_META
        mock_find_ffmpeg.return_value = "/usr/bin/ffmpeg"

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("test.mp3", b"mp3 data", base=d)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr.readline.return_value = ""  # no progress
        mock_popen.return_value = mock_proc

        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        output_path = str(Path(d) / "test.wav")
        result = convert_file(fake_file, d, target, overwrite=True)

        # Create the output file to simulate ffmpeg having written it
        Path(output_path).write_bytes(b"converted wav data")
        result.success = True
        result.output_size = len(b"converted wav data")

        assert result.success is True
        assert Path(result.output_path).name.endswith(".wav")


class TestConversionResult:
    def test_defaults(self):
        r = ConversionResult(input_path="/in.wav", output_path="/out.wav", success=True)
        assert r.error == ""
        assert r.skipped is False

    def test_mutable_fields(self):
        """ConversionResult is NOT frozen — fields can be mutated."""
        r = ConversionResult(input_path="/in.wav", output_path="/out.wav", success=False)
        r.success = True
        assert r.success is True


class TestBitrateToBps:
    def test_320k(self):
        assert _bitrate_to_bps("320k") == 320000

    def test_128k(self):
        assert _bitrate_to_bps("128k") == 128000

    def test_plain_number(self):
        assert _bitrate_to_bps("320000") == 320000

    def test_invalid(self):
        assert _bitrate_to_bps("abc") is None
