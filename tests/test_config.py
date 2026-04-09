"""Tests for src.config."""

from src.config import CDJ_MODELS, CONVERSION_PRESETS, AUDIO_EXTENSIONS, CDJModelSpecs


class TestCDJModels:
    def test_all_models_have_required_fields(self):
        for name, specs in CDJ_MODELS.items():
            assert isinstance(specs, CDJModelSpecs), f"{name} is not a CDJModelSpecs"
            assert len(specs.formats) > 0, f"{name} has no formats"
            assert len(specs.sample_rates) > 0, f"{name} has no sample_rates"
            assert len(specs.bit_depths) > 0, f"{name} has no bit_depths"
            assert specs.max_bitrate > 0, f"{name} has invalid max_bitrate"

    def test_cdj3000_supports_flac(self):
        assert "flac" in CDJ_MODELS["cdj-3000"].formats

    def test_cdj3000_high_sample_rates(self):
        assert 96000 in CDJ_MODELS["cdj-3000"].sample_rates

    def test_cdj400_no_rekordbox(self):
        assert CDJ_MODELS["cdj-400"].rekordbox is False

    def test_cdj3000_has_sd_card(self):
        assert CDJ_MODELS["cdj-3000"].sd_card is True

    def test_cdj400_16bit_only(self):
        assert CDJ_MODELS["cdj-400"].bit_depths == {16}


class TestConversionPresets:
    def test_club_preset_is_wav(self):
        preset = CONVERSION_PRESETS["club"]
        assert preset.format == "wav"
        assert preset.sample_rate == 44100
        assert preset.bit_depth == 16

    def test_high_quality_preset_is_mp3(self):
        preset = CONVERSION_PRESETS["high_quality"]
        assert preset.format == "mp3"
        assert preset.bitrate == "320k"

    def test_hires_preset(self):
        preset = CONVERSION_PRESETS["hires"]
        assert preset.format == "flac"
        assert preset.sample_rate == 96000
        assert preset.bit_depth == 24


class TestConstants:
    def test_common_formats_present(self):
        for fmt in ("mp3", "wav", "flac", "aac"):
            assert fmt in AUDIO_EXTENSIONS

    def test_playlist_formats(self):
        from src.config import PLAYLIST_EXTENSIONS
        assert "m3u8" in PLAYLIST_EXTENSIONS
        assert "m3u" in PLAYLIST_EXTENSIONS
        assert "txt" in PLAYLIST_EXTENSIONS
