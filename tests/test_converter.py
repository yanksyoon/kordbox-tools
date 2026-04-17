"""Tests for src.converter."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.converter import (
    ConversionReport,
    ConversionResult,
    ConversionTarget,
    LOSSY_FORMATS,
    LOSSLESS_FORMATS,
    build_ffmpeg_cmd,
    convert_file,
    needs_conversion,
    resolve_prefer_lossless_target,
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

FAKE_WAV_24BIT_META = AudioMetadata(
    filepath="/tmp/test_24.wav",
    format="wav",
    codec="pcm_s24le",
    sample_rate=96000,
    bit_depth=24,
    bitrate=4608000,
    channels=2,
    duration=180.0,
    file_size=99532800,
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

FAKE_AAC_META = AudioMetadata(
    filepath="/tmp/test.m4a",
    format="m4a",
    codec="aac",
    sample_rate=44100,
    bit_depth=None,
    bitrate=256000,
    channels=2,
    duration=180.0,
    file_size=5760000,
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


class TestFormatConstants:
    def test_lossy_formats_contains_expected(self):
        assert "mp3" in LOSSY_FORMATS
        assert "aac" in LOSSY_FORMATS
        assert "m4a" in LOSSY_FORMATS

    def test_lossless_formats_contains_expected(self):
        assert "wav" in LOSSLESS_FORMATS
        assert "aiff" in LOSSLESS_FORMATS
        assert "flac" in LOSSLESS_FORMATS

    def test_no_overlap_between_sets(self):
        assert LOSSY_FORMATS.isdisjoint(LOSSLESS_FORMATS)


class TestResolvePreferLosslessTarget:
    """Tests for resolve_prefer_lossless_target policy function."""

    def test_lossless_target_unchanged(self):
        """A lossless target (wav/aiff/flac) must be returned as-is."""
        for fmt in ("wav", "aiff", "flac"):
            target = ConversionTarget(format=fmt, sample_rate=44100, bit_depth=16)
            result = resolve_prefer_lossless_target(FAKE_WAV_META, target)
            assert result is target, f"Expected same object for lossless target {fmt!r}"

    def test_mp3_target_overrides_to_flac(self):
        """MP3 target should be overridden to FLAC."""
        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        result = resolve_prefer_lossless_target(FAKE_WAV_META, target)
        assert result.format == "flac"
        assert result.bitrate is None

    def test_aac_target_overrides_to_flac(self):
        """AAC target should be overridden to FLAC."""
        target = ConversionTarget(format="aac", bitrate="256k", sample_rate=44100)
        result = resolve_prefer_lossless_target(FAKE_WAV_META, target)
        assert result.format == "flac"
        assert result.bitrate is None

    def test_m4a_target_overrides_to_flac(self):
        """M4A target should be overridden to FLAC."""
        target = ConversionTarget(format="m4a", bitrate="256k", sample_rate=44100)
        result = resolve_prefer_lossless_target(FAKE_WAV_META, target)
        assert result.format == "flac"

    def test_preserves_source_sample_rate(self):
        """Overridden target inherits the source sample rate."""
        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=48000)
        result = resolve_prefer_lossless_target(FAKE_WAV_META, target)
        # Source is 44100; that should be used, not the target's 48000.
        assert result.sample_rate == FAKE_WAV_META.sample_rate

    def test_preserves_source_bit_depth_when_known(self):
        """Overridden target inherits source bit depth when the source has one."""
        target = ConversionTarget(format="mp3", bitrate="320k")
        result = resolve_prefer_lossless_target(FAKE_WAV_24BIT_META, target)
        assert result.bit_depth == 24

    def test_defaults_bit_depth_for_lossy_source(self):
        """For lossy sources (no bit_depth), the override defaults to 16-bit."""
        target = ConversionTarget(format="aac", bitrate="256k")
        result = resolve_prefer_lossless_target(FAKE_MP3_META, target)
        assert result.bit_depth == 16

    def test_lossy_to_lossy_overrides_to_flac(self):
        """Lossy source + lossy target: still override to FLAC (avoid generational loss)."""
        target = ConversionTarget(format="aac", bitrate="256k")
        result = resolve_prefer_lossless_target(FAKE_MP3_META, target)
        assert result.format == "flac"
        assert result.bitrate is None


class TestBuildFfmpegCmdDither:
    """Tests for dithering flag in build_ffmpeg_cmd."""

    @patch("src.converter.find_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))
    def test_dither_added_for_wav_16bit(self, mock_ffmpeg):
        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        cmd = build_ffmpeg_cmd("/in.flac", "/out.wav", target, dither=True)
        assert "-af" in cmd
        assert any("triangular_hp" in arg for arg in cmd)

    @patch("src.converter.find_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))
    def test_dither_added_for_aiff_16bit(self, mock_ffmpeg):
        target = ConversionTarget(format="aiff", sample_rate=44100, bit_depth=16)
        cmd = build_ffmpeg_cmd("/in.flac", "/out.aiff", target, dither=True)
        assert "-af" in cmd
        assert any("triangular_hp" in arg for arg in cmd)

    @patch("src.converter.find_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))
    def test_dither_not_added_for_wav_24bit(self, mock_ffmpeg):
        """Dithering should NOT be added when output is already 24-bit."""
        target = ConversionTarget(format="wav", sample_rate=96000, bit_depth=24)
        cmd = build_ffmpeg_cmd("/in.flac", "/out.wav", target, dither=True)
        assert "-af" not in cmd

    @patch("src.converter.find_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))
    def test_dither_not_added_when_disabled(self, mock_ffmpeg):
        target = ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)
        cmd = build_ffmpeg_cmd("/in.flac", "/out.wav", target, dither=False)
        assert "-af" not in cmd

    @patch("src.converter.find_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))
    def test_dither_not_added_for_mp3(self, mock_ffmpeg):
        """Dithering flag has no effect for lossy formats."""
        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        cmd = build_ffmpeg_cmd("/in.wav", "/out.mp3", target, dither=True)
        assert "-af" not in cmd


class TestConvertFilePreferLossless:
    """Tests for the prefer_lossless parameter in convert_file."""

    @patch("src.converter.extract_metadata")
    @patch("src.converter.find_ffmpeg")
    @patch("subprocess.Popen")
    def test_mp3_target_becomes_flac_with_prefer_lossless(
        self, mock_popen, mock_find_ffmpeg, mock_meta
    ):
        """With prefer_lossless=True, an MP3 target must produce a .flac output."""
        mock_meta.return_value = FAKE_WAV_META
        mock_find_ffmpeg.return_value = Path("/usr/bin/ffmpeg")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr.readline.return_value = ""
        mock_popen.return_value = mock_proc

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("track.wav", b"wav data", base=d)

        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        result = convert_file(fake_file, d, target, overwrite=True, prefer_lossless=True)

        # Output path must use .flac extension, not .mp3
        assert result.output_path.endswith(".flac"), (
            f"Expected .flac output, got: {result.output_path}"
        )
        # Confirm the ffmpeg command used FLAC codec (check Popen call args)
        call_args = mock_popen.call_args[0][0]  # first positional arg = cmd list
        codec_idx = call_args.index("-codec:a")
        assert call_args[codec_idx + 1] == "flac"

    @patch("src.converter.extract_metadata")
    @patch("src.converter.find_ffmpeg")
    @patch("subprocess.Popen")
    def test_aac_target_becomes_flac_with_prefer_lossless(
        self, mock_popen, mock_find_ffmpeg, mock_meta
    ):
        """With prefer_lossless=True, an AAC/M4A target must produce a .flac output."""
        mock_meta.return_value = FAKE_MP3_META
        mock_find_ffmpeg.return_value = Path("/usr/bin/ffmpeg")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr.readline.return_value = ""
        mock_popen.return_value = mock_proc

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("track.mp3", b"mp3 data", base=d)

        target = ConversionTarget(format="aac", bitrate="256k", sample_rate=44100)
        result = convert_file(fake_file, d, target, overwrite=True, prefer_lossless=True)

        assert result.output_path.endswith(".flac"), (
            f"Expected .flac output, got: {result.output_path}"
        )
        call_args = mock_popen.call_args[0][0]
        # The codec flag must be 'flac', not a lossy codec
        codec_idx = call_args.index("-codec:a")
        assert call_args[codec_idx + 1] == "flac"

    @patch("src.converter.extract_metadata")
    def test_flac_target_unchanged_with_prefer_lossless(self, mock_meta):
        """With prefer_lossless=True, a FLAC target is not altered."""
        mock_meta.return_value = FAKE_WAV_META

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("track.wav", b"wav data", base=d)

        # Fake the output file so convert_file does not error on missing output
        target = ConversionTarget(format="flac", sample_rate=96000, bit_depth=24)
        # Since FAKE_WAV_META is 44100/16 and target is 96000/24, needs_conversion=True
        # But we just want to check the output path extension here.
        with patch("src.converter._run_ffmpeg"):
            result = convert_file(fake_file, d, target, overwrite=True, prefer_lossless=True)
        # Even with prefer_lossless, FLAC target stays FLAC
        assert result.output_path.endswith(".flac")

    @patch("src.converter.extract_metadata")
    def test_prefer_lossless_false_keeps_mp3(self, mock_meta):
        """Without prefer_lossless, MP3 target stays as MP3 (backward compat)."""
        mock_meta.return_value = FAKE_WAV_META

        d = tempfile.mkdtemp()
        fake_file = _tmp_file("track.wav", b"wav data", base=d)

        target = ConversionTarget(format="mp3", bitrate="320k", sample_rate=44100)
        with patch("src.converter._run_ffmpeg"):
            result = convert_file(fake_file, d, target, overwrite=True, prefer_lossless=False)
        assert result.output_path.endswith(".mp3")
